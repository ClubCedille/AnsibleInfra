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
| 20              | 172.16.0.0/16                    | Lan ETS (cluster k3s)                   | 🟢     | `opnsense.internal` (opt12)                                                        | 11 VMs Proxmox (k3sm1-3, k3sa1-6)                                                                                                                     |
| 21              | 10.0.21.0/24                     | LAN / management                        | 🟢     | `opnsense.internal` (lan)                                                          | 8 VMs (forgejo-runners, clonezilla, cisco-pnp, eclipse-vm, test-ubuntu)                                                                               |
| 30              | 10.0.30.0/24                     | Déploiement/CI (?)                      | 🔵     | Inconnu — gw déclaré `10.0.30.2`, pas une IP d'un OPNsense inspecté                | 2 VMs (LXC `dhcp.deployment.etsmtl.club`)                                                                                                             |
| 65              | 10.255.255.252/30                | Lien "Eclipse"                          | 🟠     | `opnsense.internal` (opt14)                                                        | 0 trafic/0 VM mesurés, mais conservé — commentaire config "pls don't delete" + décision explicite utilisateur 2026-06-23                              |
| 66              | 10.110.0.0/16                    | CLIENT (réseau joueurs CTF)             | ⚫     | `opnsense01/02.event.lanets.ca`                                                    | 44 VMs Proxmox — réseau DHCP/Kea du challenge, voir `CLAUDE.md`                                                                                       |
| 67              | 10.120.0.0/16                    | AP-MGMT (WiFi + mgmt event)             | ⚫     | `opnsense01/02.event.lanets.ca`                                                    | 10 VMs — inclut `monitoring01-camp`                                                                                                                   |
| 68              | 10.130.0.0/16                    | DNS (BIND9 redondant)                   | ⚫     | `opnsense01/02.event.lanets.ca`                                                    | **100 VMs** — la quasi-totalité des challenges `*.ctf`                                                                                                |
| 69              | 10.140.0.0/16                    | Non documenté                           | 🔵     | `opnsense01/02.event.lanets.ca` (interface existe) mais rôle absent de `CLAUDE.md` | Trafic quasi nul (juste les deux CARP entre eux) — usage à clarifier ou VLAN de réserve                                                               |
| 70              | 10.150.0.0/16                    | Non documenté — probable cache/registre | 🔵     | `opnsense01/02.event.lanets.ca` (interface existe) mais rôle absent de `CLAUDE.md` | **Trafic très élevé** (151M paquets entrants observés) — corrélé à `dockercache01.camp`, cohérent avec un usage de cache d'images Docker à fort débit |
| 247             | (segment WAN partagé)            | Livraison WAN/Internet                  | 🟢     | NIC WAN des deux OPNsense + ~20 services avec IP publique directe                  | 33 VMs — voir `ProxmoxVMInventory.md` §1-2. Plusieurs workers k8s y ont aussi un accès direct (bypass pare-feu)                                       |
| 310             | —                                | Doublon legacy `cs01`                   | ⚪     | Aucun — VM stoppée, probablement obsolète                                          | 1 VM (`cs01.event.lanets.ca`, vmid 801100, stoppée) — doublon de la vraie `cs01` (vmid 801101, tag 66)                                                |
| 500             | 10.5.0.0/24                      | "services" — réseau interne k8s         | 🟢     | `opnsense.internal` (opt5)                                                         | **25 VMs** — NIC `net0` partagé par tous les clusters k8s                                                                                             |
| 601             | (réseau k3s `k3s-m0x`/`k3s-w0x`) | Cluster k3s "classique"                 | 🔵     | Inconnu — pas dans la liste VLAN d'aucun OPNsense inspecté                         | 8 VMs — gateway à identifier avant toute action sur ce tag                                                                                            |
| 1001            | 10.10.0.128/25                   | k8s01                                   | ✅     | `opnsense.internal` (opt1)                                                         | 0 VM, 0 trafic — entièrement orphelinée le 2026-06-23 (interface+règle+tag retirés)                                                                                                  |
| 1002            | 10.10.1.0/25                     | k8s02                                   | ✅     | `opnsense.internal` (opt2)                                                         | 0 VM, 0 trafic — entièrement orphelinée le 2026-06-23 (interface+règle+tag retirés)                                                                                                  |
| 1003            | 10.10.1.128/25                   | k8s03 (cluster "cedille-sandbox")       | 🟢     | `opnsense.internal` (opt3)                                                         | 4 VMs, 4 baux DHCP actifs                                                                                                                             |
| 1004            | 10.5.4.0/24                      | k8s04                                   | ✅     | `opnsense.internal` (opt4)                                                         | 0 VM, 0 trafic — entièrement orphelinée le 2026-06-23 (interface+règle+tag retirés)                                                                                                  |
| 1005            | 10.10.2.128/25                   | k8s05                                   | ✅     | `opnsense.internal` (opt6)                                                         | 0 VM ; léger trafic résiduel = bruit de trunk — entièrement orphelinée le 2026-06-23 (interface+règle+tag retirés)                                                                   |
| 1006            | 10.10.3.0/25                     | k8s06                                   | ✅     | `opnsense.internal` (opt7)                                                         | 0 VM, 0 trafic — entièrement orphelinée le 2026-06-23 (interface+règle+tag retirés)                                                                                                  |
| 1007            | 10.10.3.128/25                   | k8s07                                   | ✅     | `opnsense.internal` (opt8)                                                         | 0 VM, 0 trafic — entièrement orphelinée le 2026-06-23 (interface+règle+tag retirés)                                                                                                  |
| 1008            | 10.5.8.0/24                      | k8s08                                   | ✅     | `opnsense.internal` (opt9)                                                         | 0 VM ; léger trafic résiduel = bruit de trunk — entièrement orphelinée le 2026-06-23 (interface+règle+tag retirés)                                                                   |
| 1009            | 10.5.9.0/24                      | k8s09 (cluster "shared")                | 🟢     | `opnsense.internal` (opt10)                                                        | 10 VMs, le plus chargé du cluster                                                                                                                     |
| 1010            | 10.5.10.0/24                     | k8s10 (cluster "cedille-production-v2") | 🟢     | `opnsense.internal` (opt13)                                                        | 10 VMs, 8 baux actifs                                                                                                                                 |
| 1011            | —                                | Tag orphelin                            | ✅     | `opnsense.internal` (tag retiré le 2026-06-23)                                     | 0 VM, 0 interface — tag VLAN supprimé, interface OS détruite                                                                                          |
| 2206            | —                                | Second NIC `dockercache01.camp`         | 🔵     | Probablement événement (`.camp`), non confirmé                                     | 1 VM                                                                                                                                                  |
| _(natif/untag)_ | —                                | VLAN natif `vmbr1`                      | 🔵     | Inconnu — à clarifier (management Proxmox lui-même ?)                              | 3 VMs : `controlplane-01.etsmtl.club`, `controlplane-01.management.etsmtl.ca`, `worker-01.management.etsmtl.club`                                     |

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

### Nettoyage OPNsense terminé — prochaine étape : validation switch

Le nettoyage côté `opnsense.internal` est maintenant complet (interfaces + règles +
tags VLAN). Les 3 routeurs de l'infra ont maintenant été inspectés (2026-06-23) :

1. `opnsense.internal.etsmtl.club` (10.0.21.1) — routeur interne club, audit + nettoyage complets
2. `opnsense01/02.event.lanets.ca` (CARP 10.120.0.2/3) — cluster événement CTF
3. `OPNsense.lanets.ca` (172.16.10.2) — routeur infra LAN Events, **audité le 2026-06-23**
   (voir [`OpnsenseLanetsCA.md`](OpnsenseLanetsCA.md)) — n'utilise pas de VLAN 802.1Q,
   ne gère aucun tag du registre ci-dessus

Conclusion : les tags 30 et 601 **ne sont gérés par aucun des 3 OPNsense** — leur
gateway reste non identifiée (voir "Zones grises" ci-dessous).

Il reste à faire, selon le contexte donné par l'utilisateur (2026-06-23) :

> Valider les configurations sur le switch pour s'assurer que tous les VLANs
> nécessaires à l'infra sont disponibles, et pruner tous les VLANs qui ne servent
> plus à rien.

Cette étape nécessite un accès au(x) switch(s) — non disponible dans cette session.

## Zones grises à clarifier avant toute action future

Ces VLANs ont des VMs actives mais ne sont gérés par aucun des **trois** OPNsense
inspectés — **ne pas les inclure dans un nettoyage** sans avoir d'abord identifié leur
gateway/rôle réel :

- **Tag 30** (10.0.30.0/24, déploiement/CI) — gateway déclarée `10.0.30.2`, non
  identifiée.
- **Tag 601** (cluster k3s `k3s-m0x`/`k3s-w0x`, 8 VMs) — aucune gateway identifiée.
- **Tag 69** (10.140.0.0/16) et **tag 70** (10.150.0.0/16) — gérés par le cluster CARP
  événement mais absents de `CLAUDE.md` ; tag 70 a un trafic très élevé (cache Docker
  probable) et ne devrait surtout pas être touché sans investigation.
- **Tag 2206** — rôle non confirmé.
- **VLAN natif/untag de `vmbr1`** — 3 VMs de management dessus, à clarifier si c'est
  voulu.
- **Tag 310** — doublon legacy stoppé (`cs01.event.lanets.ca`), candidat à la
  suppression de VM (pas un VLAN à gérer en tant que tel) mais pas couvert par cette
  décision d'orphelinage VLAN.

## Limites

- Construit par croisement de documents déjà existants + relevés ponctuels (`netstat`,
  ARP) sur le cluster CARP événement pour les tags 69/70 — pas un audit aussi
  approfondi que celui fait pour `opnsense.internal` (pas de RRD 30 jours consultées
  côté event cluster).
- Les rôles déduits par nom de VM/tag ne sont pas tous confirmés par l'utilisateur.
- Aucune action corrective n'a été effectuée sur l'infra — ce document est un état des
  lieux + un plan, pas un changelog d'opérations réalisées.
