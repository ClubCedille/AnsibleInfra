# Monitoring infra — état et issues connues

Date: 2026-06-24

## État Prometheus targets

| Job | État | Notes |
|-----|------|-------|
| alertmanager | ✅ 1/1 | |
| blackbox_icmp_infra | ✅ 6/6 | Inclut OPNsense, switches, NAS |
| blackbox_icmp_pve | ✅ 8/8 | |
| ceph | ⚠️ 6/8 | pve05 down réseau ; pve07 MGR inactif (normal) |
| garagehq | ✅ 1/1 | metrics_token en clair dans monitoring_core.yaml (lecture seule, intentionnel) |
| ipmi_ilo | ⚠️ 3/5 | 10.0.21.43 (pve03), 10.0.21.44 (pve04) — reset mdp iLO requis |
| ipmi_idrac | ⚠️ 1/3 | 10.0.21.45 (pve05 down), 10.0.21.46 (pve06) — reset mdp iDRAC requis |
| ipmi_nas | ✅ 1/1 | |
| loki | ✅ 1/1 | |
| nas_node_exporter | ✅ 1/1 | |
| prometheus | ✅ 1/1 | |
| pve_cluster | ⚠️ 7/8 | pve05 down réseau |
| pve_node_exporter | ⚠️ 7/8 | pve05 down réseau |
| snmp_ios_switches | ❌ 0/2 | HTTP 500 du snmp_exporter sur axs01/mgmt01 — community string à vérifier ou OIDs non supportés sur ces modèles IOS |
| snmp_nxos_switches | ✅ 1/1 | data01 (10.0.21.11) |

## Issues à régler

### SNMP IOS (axs01 10.0.21.31, mgmt01 10.0.21.32) — priorité moyenne
snmp_exporter retourne HTTP 500 au lieu de timeout. SNMP est joignable (le timeout
a disparu après l'ajout de scrape_timeout: 30s) mais le walk échoue.

Pistes :
- Vérifier la community string (`monitoring_snmp_community`) sur les switches : `show snmp community`
- Le module `cisco_ios` dans snmp.yml walk des OIDs Cisco spécifiques (CISCO-PROCESS-MIB,
  CISCO-MEMORY-POOL-MIB) qui peuvent ne pas être supportés sur certains modèles IOS.
  Fallback : utiliser le module `if_mib` pour ces switches et ne garder `cisco_ios`
  que pour les switches qui supportent ces MIBs.

### IPMI iLO/iDRAC — reset mot de passe requis
- pve03 iLO (10.0.21.43) — reset mdp
- pve04 iLO (10.0.21.44) — reset mdp
- pve06 iDRAC (10.0.21.46) — reset mdp
- pve05 iDRAC (10.0.21.45) — pve05 est down réseau, à traiter en même temps

Credentials dans `inventories/infra/group_vars/monitoring_core.yaml` :
`monitoring_ipmi_username` / `monitoring_ipmi_password` (vaultés).

### pve05 (10.0.21.55) — down réseau
Toutes les métriques failing : node_exporter, pve_cluster, ceph. Node à investiguer
directement (hors scope monitoring).

### Alloy log shipping sur PVE
`make monitoring/infra-alloy` a crashé sur pve01-07 (crash loop systemd).
pve08 et nas01 fonctionnent. Root cause non encore investiguée — vérifier
`journalctl -xeu alloy.service` sur un node PVE en erreur via jumpbox.

### OPNsense Telegraf → Prometheus remote_write
Playbook `playbooks/infra/opnsense-telegraf.yaml` écrit mais jamais run.
Cible : opnsense01/02 → remote_write vers http://10.0.21.95:9090/api/v1/write.
Prérequis : plugin `os-telegraf` installé sur les OPNsense.

### Mimir remote_write (k8s prod-v2)
Commenté dans monitoring_core.yaml. À activer une fois Mimir déployé dans
k8s-cedille-production-v2. Variables à remplir :
- `monitoring_mimir_url`
- `monitoring_mimir_username`
- `monitoring_mimir_password` (vault)
