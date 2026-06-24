# Registre des VLANs — état général de l'infra

> Vue d'ensemble de tous les tags 802.1Q observés sur le trunk Proxmox (`vmbr1`,
> cluster `OneBigCluster`, 10.0.21.51) et sur les trois OPNsense inspectés :
> `opnsense.internal.etsmtl.club`, `opnsense01-02.event.lanets.ca` (CARP) et
> `OPNsense.lanets.ca` (172.16.10.2). Construit en croisant
> [`OpnsenseInternalETSMTL.md`](OpnsenseInternalETSMTL.md),
> [`OpnsenseLanetsCA.md`](OpnsenseLanetsCA.md),
> [`ProxmoxVMInventory.md`](ProxmoxVMInventory.md) et `CLAUDE.md` (topologie événement
> CTF). État au 2026-06-23.
>
> Ce document est le point d'entrée pour savoir "qui gère quoi" avant toute
> intervention sur le trunk/switch ou sur un OPNsense.
>
> **Note** : `OPNsense.lanets.ca` (3e routeur, 172.16.10.2) n'utilise **pas** de
> VLAN 802.1Q — il opère sur des NICs physiques séparées et n'apparaît donc pas
> dans la table des tags ci-dessous. Voir [`OpnsenseLanetsCA.md`](OpnsenseLanetsCA.md)
> pour son audit complet.

---

## Légende statut

- 🟢 **Actif** — trafic réel et/ou VMs confirmées dessus.
- 🟠 **Conservé (décision explicite)** — pas de trafic mesuré, mais maintenu sur
  demande de l'utilisateur.
- ⚪ **À orpheliner** — confirmé mort (0 trafic 30j + 0 VM Proxmox), retrait planifié.
- ✅ **Orphelinée (exécutée, complet)** — sur `opnsense.internal` : interface
  désassignée, règle pare-feu retirée, tag VLAN supprimé et interface OS détruite.
  Ne reste que le pruning éventuel côté switch/Proxmox (hors périmètre OPNsense).
- 🔵 **Hors périmètre OPNsense connu** — VMs présentes, mais aucune des deux instances
  OPNsense inspectées ne gère ce VLAN ; gateway/rôle à clarifier.
- ⚫ **Géré par le cluster événement** — appartient à `opnsense01/02.event.lanets.ca`,
  documenté séparément dans `CLAUDE.md`.

## Table maîtresse

| Tag             | Réseau                           | Nom/rôle                                | Statut | Géré par                                                                           | Détail                                                                                                                                                |
| --------------- | -------------------------------- | --------------------------------------- | ------ | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 15              | —                                | CEPH (stockage)                         | 🟢     | Proxmox Ceph cluster                                                               | MTU 9216 — réseau dédié réplication Ceph entre nœuds PVE                                                                                              |
| 20              | 172.16.0.0/16                    | Lan ETS (cluster k3s)                   | ✅     | `opnsense.internal` (opt12 supprimé 2026-06-23)                                    | 0 VM — cluster k3s Lan ETS supprimé ; interface+tag+règle+OS interface entièrement retirés                                                            |
| 21              | 10.0.21.0/24                     | LAN / management                        | 🟢     | `opnsense.internal` (lan)                                                          | 5 VMs (forgejo-runners, clonezilla, cisco-pnp, eclipse-vm)                                                                                            |
| 30              | 10.0.30.0/24                     | Bootstrap switches Cisco PNP            | 🟢     | Serveur PNP (`cisco-pnp.mgmt`) — gw 10.0.30.2                                     | Utilisé pour bootstrapper les switches Cisco via PNP ; à conserver                                                                                    |
| 65              | 10.255.255.252/30                | Lien "Eclipse"                          | 🟠     | `opnsense.internal` (opt14)                                                        | 0 trafic/0 VM, conservé par décision explicite ("pls don't delete")                                                                                   |
| 66              | 10.110.0.0/16                    | CLIENT (réseau joueurs CTF)             | 🟠     | *(event OPNsense supprimé)* — **réservé événements futurs**                        | 0 VM active — teardown SummerCamp 2026-06-23 ; **à conserver sur le trunk switch**                                                                   |
| 67              | 10.120.0.0/16                    | AP-MGMT (WiFi + mgmt event)             | 🟠     | *(event OPNsense supprimé)* — **réservé événements futurs**                        | 0 VM active — **à conserver sur le trunk switch**                                                                                                    |
| 68              | 10.130.0.0/16                    | DNS/Challenges CTF                      | 🟠     | *(event OPNsense supprimé)* — **réservé événements futurs**                        | 0 VM active — **à conserver sur le trunk switch**                                                                                                    |
| 69              | 10.140.0.0/16                    | Réseau événement additionnel            | 🟠     | *(event OPNsense supprimé)* — **réservé événements futurs**                        | 0 VM active — **à conserver sur le trunk switch**                                                                                                    |
| 70              | 10.150.0.0/16                    | Cache Docker événement                  | ✅     | *(event OPNsense supprimé)*                                                        | 0 VM active (dockercache01 supprimé 2026-06-23) — **à retirer PVE et switch**                                                                        |
| 247             | (segment WAN partagé)            | Livraison WAN/Internet                  | 🟢     | NIC WAN des OPNsense + services IP publique directe                                | opnsense01.prod, uploadbox, ctfd, workers k8s avec NIC WAN direct                                                                                    |
| 255             | —                                | PFSYNC OPNsense                         | 🟠     | OPNsense (pfsync — sync état firewall)                                             | Sub-interface `vmbr1.255` présente sur pve04 (OPNsense existant), à propager sur tous les nœuds PVE 2026-06-24                                        |
| 310             | —                                | Doublon legacy `cs01`                   | ✅     | Aucun                                                                              | VM 801100 supprimée — VLAN orphelin, aucune VM restante                                                                                               |
| 500             | 10.5.0.0/24                      | "services" — réseau interne k8s         | 🟢     | `opnsense.internal` (opt5)                                                         | 24 VMs — NIC inter-nœuds des clusters k8s                                                                                                             |
| 601             | (réseau k3s `k3s-m0x`/`k3s-w0x`) | Cluster k3s "classique"                 | ✅     | Inconnu — pas dans aucun OPNsense                                                  | 0 VM — cluster k3s-m/w supprimé lors du cleanup 2026-06-23 ; VLAN trunk à pruner                                                                     |
| 1001            | 10.10.0.128/25                   | k8s01                                   | ✅     | `opnsense.internal` (supprimé)                                                     | 0 VM — interface+règle+tag+OS retirés 2026-06-23                                                                                                      |
| 1002            | 10.10.1.0/25                     | k8s02                                   | ✅     | `opnsense.internal` (supprimé)                                                     | 0 VM — interface+règle+tag+OS retirés 2026-06-23                                                                                                      |
| 1003            | 10.10.1.128/25                   | k8s03 (cluster "cedille-sandbox")       | 🟢     | `opnsense.internal` (opt3)                                                         | 4 VMs, 4 baux DHCP actifs                                                                                                                             |
| 1004            | 10.5.4.0/24                      | k8s04                                   | ✅     | `opnsense.internal` (supprimé)                                                     | 0 VM — interface+règle+tag+OS retirés 2026-06-23                                                                                                      |
| 1005            | 10.10.2.128/25                   | k8s05                                   | ✅     | `opnsense.internal` (supprimé)                                                     | 0 VM — interface+règle+tag+OS retirés 2026-06-23                                                                                                      |
| 1006            | 10.10.3.0/25                     | k8s06                                   | ✅     | `opnsense.internal` (supprimé)                                                     | 0 VM — interface+règle+tag+OS retirés 2026-06-23                                                                                                      |
| 1007            | 10.10.3.128/25                   | k8s07                                   | ✅     | `opnsense.internal` (supprimé)                                                     | 0 VM — interface+règle+tag+OS retirés 2026-06-23                                                                                                      |
| 1008            | 10.5.8.0/24                      | k8s08                                   | ✅     | `opnsense.internal` (supprimé)                                                     | 0 VM — interface+règle+tag+OS retirés 2026-06-23                                                                                                      |
| 1009            | 10.5.9.0/24                      | k8s09 (cluster "shared")                | 🟢     | `opnsense.internal` (opt10)                                                        | 10 VMs, le plus chargé du cluster                                                                                                                     |
| 1010            | 10.5.10.0/24                     | k8s10 (cluster "cedille-production-v2") | 🟢     | `opnsense.internal` (opt13)                                                        | 10 VMs, 8 baux actifs                                                                                                                                 |
| 1011            | —                                | Tag orphelin                            | ✅     | `opnsense.internal` (supprimé)                                                     | 0 VM — tag+OS retirés 2026-06-23                                                                                                                      |
| 2206            | —                                | Lien ETS — infrastructure réseau ETS    | 🟢     | Côté ETS (routeurs/infra ETS)                                                      | **À conserver** — lien vers l'infrastructure et les routeurs de l'ETS ; le NIC `dockercache01` n'était qu'un usage secondaire                         |
| _(natif/untag)_ | —                                | VLAN natif `vmbr1`                      | ✅     | Aucun                                                                              | 3 VMs management supprimées lors du cleanup 2026-06-23                                                                                                |

---

## Orphelinage exécuté — complet, étapes 1 à 3/3 (2026-06-23)

VLANs concernés : **1001, 1002, 1004, 1005, 1006, 1007, 1008** (le VLAN 65 est
explicitement **exclu** — conservé par décision utilisateur). Le tag **1011** n'a
jamais eu d'interface assignée, donc rien à désassigner pour ce tag (reste tel quel).

### Fait

1. **Sauvegarde** : `/conf/backup/config-pre-vlan-cleanup-1782187437.xml` créée sur
   `opnsense.internal.etsmtl.club` avant toute modification.
2. **Désassignation des 7 interfaces** : retrait de la balise `<enable>` dans
   `/conf/config.xml` pour `opt1, opt2, opt4, opt6, opt7, opt8, opt9`
   (k8s01,02,04,05,06,07,08) — méthode officielle OPNsense pour désactiver une
   interface tout en conservant sa config (IP, VLAN) pour une ré-activation facile.
   Le reste de la configuration de ces interfaces (IP, sous-réseau, description) a été
   conservé intact, comme décidé.
3. **Application en live** : les 7 interfaces VLAN (`vtnet0_vlan1001/1002/1004/1005/
1006/1007/1008`) ont été descendues (`ifconfig down`) sans reboot du routeur.
4. **`dhcpd` redémarré** (`configctl dhcpd restart`) pour qu'il ne tente plus de se
   lier sur ces interfaces — aucune erreur, service toujours actif.
5. **Vérifié** : XML toujours valide après édition, les interfaces actives
   (1003/k8s03, 1009/k8s09, 21/LAN, etc.) sont restées `UP` et non affectées, uptime
   du routeur continu (pas de reboot/crash).
6. **Règles pare-feu orphelines retirées** : les 7 règles `pass any any` associées à
   ces interfaces (`opt1, opt2, opt4, opt6, opt7, opt8, opt9`) ont été supprimées de
   `config.xml` par UUID (sauvegarde séparée :
   `/conf/backup/config-pre-pfrule-cleanup-1782244859.xml`), puis appliquées en live
   via `configctl filter reload` (mécanisme officiel "Apply changes"). Vérifié :
   `pfctl -sr` (108 règles, contre 131 avant tout le nettoyage) ne référence plus
   aucune des 7 interfaces, et le ruleset des VLANs actifs (k8s03, services, k8s09,
   Lan ETS, k8s10) est resté intact.
7. **Tags VLAN retirés** (confirmation explicite utilisateur requise et obtenue avant
   cette étape) : les 8 entrées `<vlan>` pour les tags **1001, 1002, 1004, 1005, 1006,
   1007, 1008 et 1011** ont été supprimées de `config.xml` par UUID (sauvegarde
   séparée : `/conf/backup/config-pre-vlantag-cleanup-1782245317.xml`). Il ne reste que
   8 VLANs définis sur `opnsense.internal` : `20, 21, 65, 247, 500, 1003, 1009, 1010`
   (les actifs + le 65 conservé).
8. **Interfaces VLAN OS détruites** : `vtnet0_vlan1001, 1002, 1004, 1005, 1006, 1007,
1008, 1011` ont été détruites (`ifconfig destroy`) — y compris `vtnet0_vlan1011`
   qui existait au niveau OS malgré l'absence d'assignation à une interface OPNsense
   (créée au boot pour tout tag défini dans `<vlans>`, indépendamment de son usage).
   Vérifié après coup : les 8 interfaces n'existent plus, les VLANs actifs et le VLAN
   65 conservé sont restés `UP` et intacts, `pfctl -sr` toujours à 108 règles, uptime
   continu, `config.xml` valide.

### Pas fait (volontairement, hors périmètre de ce nettoyage)

- **Switch/Proxmox** : ces 8 tags sont probablement toujours transportés sur le trunk
  physique vers `opnsense.internal` (pas d'accès switch dans cette session) — à
  vérifier/pruner lors de la validation switch mentionnée ci-dessous.

### État du nettoyage OPNsense — 2026-06-23

**`opnsense.internal` (10.0.21.1)** — nettoyage complet :

- Toutes les interfaces mortes supprimées de `config.xml` (k8s01-08, LanETS/20)
- 11 interfaces actives : lan, wan, k8s03, services, k8s09, k8s10, breakingglass WG, OpenVPN, Eclipse, lo0
- 106 règles pf

**`opnsense01/02.event.lanets.ca`** — **supprimés** (teardown SummerCamp 2026-06-23).
VLANs 66-70 conservés sur le trunk switch, sans gateway active — réservés pour le
prochain événement. Un nouvel event OPNsense sera déployé depuis le template
(`template-opnsense`, vmid 2000 — supprimé aussi, à recréer si nécessaire).

**`OPNsense.lanets.ca` (172.16.10.2, vmid 100201)** — **non accessible en session SSH**
(172.16.10.x non routable depuis pve01 ni depuis la machine locale). Nettoyage à faire :
8 interfaces mortes (GameServers, InfraJennifer, EventStaging, LABO, WireguardVPN,
OpenVPN_Players, StagingPeeringVlan501, Wireguard opt1) — voir [`OpnsenseLanetsCA.md`](OpnsenseLanetsCA.md).
Nécessite accès console Proxmox (VM 100201 pve04) ou VPN 172.16.10.x.

### Prochaine étape : switch

VLANs à pruner du trunk switch (plus aucune VM ni gateway) : **20, 70, 310, 601,
1001, 1002, 1004, 1005, 1006, 1007, 1008, 1011, natif/untag**.

VLANs à conserver : **21, 30, 65, 66, 67, 68, 69, 247, 255, 500, 1003, 1009, 1010, 2206**.

(cache Docker événement — non confirmé comme VLAN événement permanent).

## Limites

- Construit par croisement de documents déjà existants + relevés ponctuels (`netstat`,
  ARP) sur le cluster CARP événement pour les tags 69/70 — pas un audit aussi
  approfondi que celui fait pour `opnsense.internal` (pas de RRD 30 jours consultées
  côté event cluster).
- Les rôles déduits par nom de VM/tag ne sont pas tous confirmés par l'utilisateur.
- Aucune action corrective n'a été effectuée sur l'infra — ce document est un état des
  lieux + un plan, pas un changelog d'opérations réalisées.
