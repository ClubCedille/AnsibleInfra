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
| ipmi_ilo | ⚠️ 4/5 | pve04 corrigé (voir ci-dessous) ; pve03 (10.0.21.43) répond au ping/HTTPS mais pas RMCP/IPMI-LAN |
| ipmi_idrac | ⚠️ 1/3 | pve05 (10.0.21.45), pve06 (10.0.21.46) — pas de lien physique sur le port dédié (voir ci-dessous) |
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

### pve04 iLO — corrigé (2026-08-23)
En vérifiant la config in-band (`ipmitool lan print` via `/dev/ipmi0`, accessible
même quand le port réseau dédié ne répond pas), l'iLO de pve04 était en
**DHCP** et avait reçu `10.0.21.154` au lieu de `10.0.21.44` — Prometheus
scrutait donc la mauvaise IP depuis le début, ce n'était pas un problème réseau.
Fix : `ipmitool lan set 2 ipsrc static` + `ipaddr 10.0.21.44` + `netmask
255.255.255.0` + `defgw ipaddr 10.0.21.1`, puis `ipmitool mc reset cold` pour
faire réinitialiser l'interface. Confirmé `up` côté Prometheus après reset.

Méthode utile pour auditer les 8 BMC d'un coup (nécessite `ipmitool` installé
sur chaque hôte PVE, `apt-get install ipmitool`) :
```
ipmitool lan print   # auto-détecte le bon channel (2 pour iLO HP, 1 pour iDRAC Dell)
```
Comparer le champ `IP Address` avec le mapping attendu (`pveNN` ↔ `.4N`/`.4N+…`
dans hosts.ini) — ça a permis de trouver le mismatch DHCP sur pve04 en plus des
IP à 0.0.0.0 sur pve06 (voir ci-dessous).

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

### pve05 / pve06 iDRAC — pas de lien physique sur le port dédié
Diagnostic approfondi le 2026-08-23 avec `racadm` (voir installation ci-dessous) :

```
NIC Selection   = Dedicated
Link Detected   = No
Speed           = 10Mb/s
Active NIC      = None

Static IPv4 settings:
Static IP Address    = 10.0.21.45   # (ou .46 pour pve06)
Static Subnet Mask   = 255.255.255.0
Static Gateway       = 10.0.21.1
```

La config IP stockée est **correcte** sur les deux — ce n'est ni un mot de
passe, ni un mauvais paramétrage. Le port réseau dédié de l'iDRAC ne détecte
tout simplement aucun lien physique. Aucune commande logicielle (`ipmitool`,
`racadm`, `mc reset cold`) ne peut réparer ça — il faut vérifier/reconnecter
le câble sur le port mgmt dédié de ces deux serveurs, ou le port switch en
face (potentiellement désactivé ou down côté switch).

SEL (`ipmitool sel list`) ne montre aucun évènement matériel récent sur ces
deux hôtes (dernier évènement pve05 : perte AC PSU le 2026-06-24 ; pve06 :
pic de température en mars) — rien qui explique une panne du lien réseau
aujourd'hui, donc pas de piste "défaillance matérielle active" à creuser.

Avant de trouver ce diagnostic, plusieurs `ipmitool lan set` sur pve06 ont
timeout/laissé le BMC en `Set in Progress` — ce n'était pas un bug logiciel
récupérable par reset, juste le symptôme du lien absent (rien ne confirme
l'écriture côté réseau). Ne pas re-tenter `ipmitool lan set` sur ces deux hôtes
tant que le lien physique n'est pas rétabli.

**Installation de racadm (Dell) pour diagnostic approfondi**, utile pour tout
futur iDRAC à dépanner :
```bash
curl -fsSL https://linux.dell.com/repo/pgp_pubkeys/0x1285491434D8786F.asc \
  | gpg --dearmor -o /etc/apt/trusted.gpg.d/dell-apt-key.gpg
echo 'deb [signed-by=/etc/apt/trusted.gpg.d/dell-apt-key.gpg] https://linux.dell.com/repo/community/openmanage/11000/jammy jammy main' \
  > /etc/apt/sources.list.d/dell-openmanage.list
apt-get update
apt-get install -y srvadmin-idracadm7 libargtable2-0   # libargtable2-0 dispo direct dans Debian trixie
/opt/dell/srvadmin/bin/idracadm7 getniccfg
```
Notes : utiliser `https://` (pas `http://`, filtré en sortie sur ce réseau) ;
le paquet Dell est buildé pour Ubuntu jammy mais tourne sans souci sur Debian
13/trixie (glibc plus récente, compatible ascendante) ; `idracadm7` couvre
iDRAC7/8/9 malgré le nom.

### pve03 iLO — lien réseau OK mais IPMI-over-LAN ne répond pas
Contrairement à pve05/06, pve03 répond au ping et sur le port HTTPS (443)
après `ipmitool mc reset cold`. La config du channel LAN est correcte
(`ipmitool channel info 2` → `Access Mode: always available`). Mais le port
RMCP/UDP 623 utilisé par `ipmi_exporter` ne répond toujours pas, testé
directement depuis un autre hôte PVE (`ipmitool -I lanplus -H 10.0.21.43 ...`
→ timeout). Semble être un service IPMI-LAN bloqué indépendamment du reste du
firmware (iLO 2.82, assez ancien — HP ProLiant Gen8). `ilorest` (RESTful HP
tool) est installé sur pve03 mais échoue en local
(`chif library not found`) — le module noyau `hpilo` est bien chargé et
`/dev/hpilo/*` existe, il manque juste la lib userspace `ilorest_chif`,
pas creusé plus loin.

### pve04 (résolu, voir plus haut) et récapitulatif des 4 BMC problématiques

| Hôte | Type | Cause réelle | Statut |
|---|---|---|---|
| pve03 | iLO | Service IPMI-LAN bloqué, firmware ancien | Ping/HTTPS OK, RMCP toujours down |
| pve04 | iLO | DHCP au lieu de static, mauvaise IP | ✅ Corrigé |
| pve05 | iDRAC | Pas de lien physique sur le port dédié | Bloqué — intervention physique requise |
| pve06 | iDRAC | Pas de lien physique sur le port dédié | Bloqué — intervention physique requise |

Credentials dans `inventories/infra/group_vars/monitoring_core.yaml` :
`monitoring_ipmi_username` / `monitoring_ipmi_password` (vaultés).

### OPNsense Telegraf → Prometheus remote_write
Playbook `playbooks/infra/opnsense-telegraf.yaml` écrit mais jamais run.
Cible : opnsense01/02 → remote_write vers http://10.0.21.95:9090/api/v1/write.
Prérequis : plugin `os-telegraf` installé sur les OPNsense.

### Syslog forwarding NX-OS → Loki — résolu (2026-09-02)
Deux causes distinctes empêchaient tout syslog de sortir de data01 (Core01)
vers monitoring01, découvertes et corrigées en deux temps.

**1. VRF incorrecte** (trouvé côté AnsibleInfra) : `logging server 10.0.21.95
5 use-vrf management` pointait vers une VRF vide — l'IP 10.0.21.11 est en
réalité sur `Vlan21` en VRF `default` (`show ip interface brief vrf all` le
révèle). Corrigé en `use-vrf default`.

**2. Socket syslogd jamais ouvert** (trouvé en direct sur le switch) : même
avec la bonne VRF, `show logging server` restait bloqué sur "This server is
temporarily unreachable" malgré routage/ARP/ping/ACL/CoPP tous corrects (CoPP
ne filtre que le trafic *entrant* vers le control-plane, jamais le trafic que
le switch génère lui-même). La vraie cause : le syslogd de ce NX-OS ancien
(7.0.3.I6(2), ~2017) **n'ouvre jamais le socket UDP d'émission** tant qu'aucun
`logging source-interface` n'est configuré. La commande elle-même le révèle :
```
core01(config)# logging source-interface Vlan21
Configuring logging source-interface will open UDP/syslog socket(514).
```
**Sur tout futur switch NX-OS à configurer pour du syslog forwarding, penser à
`logging source-interface <interface>` en plus de `logging server` — sans
ça, aucun paquet ne sort jamais, peu importe le reste de la config.**

Config finale sur data01 :
```
logging level spanning-tree 5
logging server 10.0.21.95 5 use-vrf default
logging source-interface Vlan21
```

**3. Format non-RFC3164** (trouvé côté Alloy, après le fix switch) : une fois
les paquets réellement délivrés (confirmé par `tcpdump`), Alloy ne produisait
toujours aucune donnée dans Loki, sans la moindre erreur — `loki.source.syslog`
avec `syslog_format = "rfc3164"` rejette silencieusement chaque message NX-OS
car son format n'est pas conforme : `<189>: 2026 Sep 2 18:24:04 UTC:
%VSHD-...` (un `:` et une année sur 4 chiffres juste après le PRI, que RFC3164
n'autorise pas). Fix : `syslog_format = "raw"` (évite le parsing d'en-tête
entièrement) — nécessite `--stability.level=experimental` sur le binaire Alloy
(géré via `alloy_custom_args` dans le rôle, écrit dans `/etc/default/alloy`).
Vérification utile en cas de doute sur le pipeline : les métriques internes
d'Alloy sur `:12345/metrics` (`loki_source_syslog_entries_total`,
`loki_source_syslog_parsing_errors_total`,
`loki_process_dropped_lines_total{reason="..."}`)  distinguent clairement
"jamais reçu" / "reçu mais rejeté au parsing" / "reçu, parsé, filtré par
l'allowlist" — bien plus rapide qu'un tcpdump pour diagnostiquer où ça bloque.

### Mimir remote_write — cible à corriger vers k8s-shared
Commenté dans monitoring_core.yaml, ciblait encore k8s-cedille-production-v2
(en décommission). À réécrire pour pointer vers Mimir dans k8s-shared une fois
déployé (voir plan monitoring global). Variables à remplir :
- `monitoring_mimir_url`
- `monitoring_mimir_username`
- `monitoring_mimir_password` (vault)
