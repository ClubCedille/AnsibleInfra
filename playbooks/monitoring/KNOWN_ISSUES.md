# Monitoring infra — état et issues connues

Date: 2026-08-23 (mise à jour ; état initial au 2026-06-24 conservé en historique ci-dessous)

## État Prometheus targets

| Job | État | Notes |
|-----|------|-------|
| alertmanager | ✅ 1/1 | |
| blackbox_icmp_infra | ✅ 6/6 | Inclut OPNsense, switches, NAS |
| blackbox_icmp_pve | ✅ 8/8 | |
| ceph | ✅ 8/8 | pve05 revenu réseau |
| garagehq | ✅ 1/1 | metrics_token en clair dans monitoring_core.yaml (lecture seule, intentionnel) |
| ipmi_ilo | ⚠️ 3/5 | 10.0.21.43 (pve03), 10.0.21.44 (pve04) — injoignables réseau, pas juste un mdp |
| ipmi_idrac | ⚠️ 1/3 | 10.0.21.45 (pve05), 10.0.21.46 (pve06) — injoignables réseau |
| ipmi_nas | ✅ 1/1 | |
| loki | ✅ 1/1 | |
| nas_node_exporter | ✅ 1/1 | |
| prometheus | ✅ 1/1 | |
| pve_cluster | ✅ 8/8 | pve05 revenu réseau |
| pve_node_exporter | ✅ 8/8 | pve05/pve08 corrigés — voir ci-dessous |
| snmp_ios_switches | ❌ 0/2 | axs01/mgmt01 — timeout (pas HTTP 500 comme avant), community/CLI à vérifier |
| snmp_nxos_switches | ✅ 1/1 | data01 (10.0.21.11) |

## Résolu depuis le 24 juin

### pve_node_exporter pve05/pve08 — corrigé (2026-08-23)
node_exporter n'avait jamais été installé sur ces deux hôtes (probablement
reconstruits après le déploiement initial de juin, `systemctl` retournait
"Unit not found"). Fix : `make monitoring/infra-node-exporters LIMIT=pve05.mgmt.etsmtl.club,pve08.mgmt.etsmtl.club`.
Les deux exposent maintenant `:9100/metrics` normalement.

### Alloy log shipping — root cause trouvée et corrigée (2026-08-23)
`config.alloy.j2` (rôle `cedille.monitoring.alloy`, repo `AnsibleRoles`) générait
des littéraux d'objet River sans virgule entre les champs (`__path__ = "..."`
suivi directement de `job = "..."` sans `,`) — le parseur River rejette ça au
démarrage (`missing ',' in field list`), d'où le crash loop systemd.
Fix mergé : [AnsibleRoles#67](https://github.com/ClubCedille/AnsibleRoles/pull/67).
Après `make galaxy-install` pour rafraîchir le cache de collection, redéployé sur
tout le groupe `monitoring_alloy` (pve01-08 + nas01) — les 9 hôtes sont `active`.

pve08 n'avait en fait jamais Alloy installé (même cause que node_exporter — hôte
reconstruit). nas01 avait un problème séparé : le `bond0` NetworkManager
(issu de la migration LACP, voir contexte NAS) était en `ipv4.method: manual`
sans serveur DNS configuré, donc `/etc/resolv.conf` vide → tout `apt-get update`
échouait. DNS ajouté (`1.1.1.1`, search `prod.lanets.ca`, cohérent avec les
autres hôtes infra) directement sur la machine.

## Issues à régler

### SNMP IOS (axs01 10.0.21.31, mgmt01 10.0.21.32) — priorité moyenne
L'erreur a changé depuis juin : c'est maintenant un timeout pur (`request
timeout (after 3 retries)`) côté snmp_exporter, plus une HTTP 500. Pas encore
root-causé plus loin — nécessite soit la community string vaultée
(`monitoring_snmp_community` dans `monitoring_exporters.yaml`) pour tester un
`snmpwalk` direct, soit un accès CLI aux switches (`show snmp community`).

Pistes toujours valables :
- Vérifier la community string sur les switches.
- Le module `cisco_ios` dans `snmp.yml` walk des OIDs Cisco spécifiques
  (CISCO-PROCESS-MIB, CISCO-MEMORY-POOL-MIB) qui peuvent ne pas être supportés
  sur certains modèles IOS. Fallback : module `if_mib` pour ces switches.

### IPMI iLO/iDRAC — injoignables au niveau réseau
- pve03 iLO (10.0.21.43), pve04 iLO (10.0.21.44)
- pve05 iDRAC (10.0.21.45), pve06 iDRAC (10.0.21.46)

Confirmé le 2026-08-23 : ces IP ne répondent même pas au ping — ce n'est donc
pas (seulement) un mot de passe expiré, il faut une intervention physique
(vérifier le câblage du port mgmt dédié, éventuellement reset factory du BMC).
Rien de plus à faire côté Ansible tant que le matériel n'est pas accessible
réseau.

Credentials dans `inventories/infra/group_vars/monitoring_core.yaml` :
`monitoring_ipmi_username` / `monitoring_ipmi_password` (vaultés).

### OPNsense Telegraf → Prometheus remote_write
Playbook `playbooks/infra/opnsense-telegraf.yaml` écrit mais jamais run.
Cible : opnsense01/02 → remote_write vers http://10.0.21.95:9090/api/v1/write.
Prérequis : plugin `os-telegraf` installé sur les OPNsense.

### Mimir remote_write — cible à corriger vers k8s-shared
Commenté dans monitoring_core.yaml, ciblait encore k8s-cedille-production-v2
(en décommission). À réécrire pour pointer vers Mimir dans k8s-shared une fois
déployé (voir plan monitoring global). Variables à remplir :
- `monitoring_mimir_url`
- `monitoring_mimir_username`
- `monitoring_mimir_password` (vault)
