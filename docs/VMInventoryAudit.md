# Audit complet des VMs Proxmox — `OneBigCluster`

> Audit exhaustif de toutes les VMs/CT du cluster Proxmox avec mapping VLAN,
> usage déduit et recommandation de nettoyage. Collecté via SSH sur `root@10.0.21.51`
> (`pvesh get /cluster/resources` + lecture directe `/etc/pve/nodes/*/qemu-server/*.conf`
> et `/etc/pve/nodes/*/lxc/*.conf`). État au **2026-06-23**.
>
> Voir aussi : [`VLANRegistry.md`](VLANRegistry.md) (état des VLANs par OPNsense),
> [`ProxmoxVMInventory.md`](ProxmoxVMInventory.md) (inventaire précédent + constats),
> [`OpnsenseInternalETSMTL.md`](OpnsenseInternalETSMTL.md),
> [`OpnsenseLanetsCA.md`](OpnsenseLanetsCA.md).

---

## Résultat du cleanup — 2026-06-23

Scripts exécutés : `scripts/cleanup_ctf_vms.py --group all --execute` et
`scripts/cleanup_vlans_20_310_601.py --execute`, suivis du teardown manuel
de l'infra événement SummerCamp.

| Métrique | Avant | Après |
|---|---|---|
| Total VMs/CT | **209** | **35** |
| Running | 157 | 33 |
| Stopped | 52 | 2 |
| Supprimées | — | **174** |

### VMs stoppées conservées (golden standards)

| vmid | Nom | Nœud | Rôle |
|---|---|---|---|
| 801101 | cs01.event.lanets.ca | pve02 | Golden standard pour les scripts de création CS2 |
| 801201 | trackmania.event.lanets.ca | pve01 | Golden standard Trackmania (référence image) |

### Infrastructure active — état final

| Groupe | VMs | Détail |
|---|---|---|
| k8s cedille-production-v2 | 10 | 4 CP (pve03/04/06/07) + 6 workers (pve01–07) |
| k8s shared | 10 | 4 CP + 6 workers |
| k8s cedille-sandbox | 4 | 1 CP + 3 workers |
| CI Forgejo | 3 | forgejo-runner01/02/03 |
| Infra permanente | 5 | opnsense01.prod, cisco-pnp, eclipse-vm, uploadbox, clonezilla |
| Conservé post-SummerCamp | 1 | ctfd.summercamp.dciets.com (850101, pve03) |
| **Total** | **33 running + 2 stopped** | |

### Teardown SummerCamp — 2026-06-23

Infra événement supprimée manuellement après la fin du SummerCamp (12 VMs) :
opnsense01.event (700101), jumpbox (803100), dockercache01.camp (812101),
dhcp01/02.camp (813101/813102), dns01/02.camp (814101/814102),
tftp01/02.camp (815101/815102), portal01.camp (816101), monitoring01-camp (817101),
secret.ctf (819101).

Conservé : `ctfd.summercamp.dciets.com` (850101) — plateforme CTFd maintenue en ligne.

---

## Compteurs initiaux (état avant cleanup)

| Métrique | Valeur |
|---|---|
| Total VMs/CT | **209** |
| Running | **157** |
| Stopped | **52** |
| Templates | **2** (vmid 1000, 2000) |
| Types | 207 QEMU + 2 LXC |
| Nœuds | pve01–pve04, pve06–pve08 (pas de pve05) |

## Légende

- 🟢 Running  /  🔴 Stopped  /  📦 Template
- ✅ Garder  /  ⚠️ À confirmer  /  🗑️ Supprimer

---

## VLAN 20 — k3s "Lan ETS" (172.16.0.0/16) — géré par `opnsense.internal` opt12

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 1000 | template-cloud-init | pve01 | 📦 | 20 | 172.16.0.1 | Template cloud-init de référence | ✅ |
| 10110 | k3sm1.lan.etsmtl.club | pve02 | 🟢 | 20 | - | Master k3s — cluster Lan ETS | ✅ |
| 10120 | k3sm2.lan.etsmtl.club | pve04 | 🟢 | 20 | - | Master k3s — cluster Lan ETS | ✅ |
| 10130 | k3sm3.lan.etsmtl.club | pve07 | 🔴 | 20 | - | Master k3s — cluster Lan ETS | ⚠️ stoppé, cohérence cluster? |
| 10210 | k3sa1.lan.etsmtl.club | pve01 | 🟢 | 20/247 | - | Agent k3s + NIC WAN direct (tag 247) | ✅ |
| 10220 | k3sa2.lan.etsmtl.club | pve02 | 🟢 | 20/247 | - | Agent k3s + NIC WAN direct | ✅ |
| 10230 | k3sa3.lan.etsmtl.club | pve03 | 🟢 | 20/247 | - | Agent k3s + NIC WAN direct | ✅ |
| 10240 | k3sa4.lan.etsmtl.club | pve04 | 🟢 | 20/247 | - | Agent k3s + NIC WAN direct | ✅ |
| 10250 | k3sa5.lan.etsmtl.club | pve06 | 🟢 | 20/247 | - | Agent k3s + NIC WAN direct | ✅ |
| 10260 | k3sa6.lan.etsmtl.club | pve07 | 🔴 | 20/247 | - | Agent k3s — stoppé (même nœud que k3sm3) | ⚠️ stoppé, cohérence cluster? |
| 200004 | gui.lan.etsmtl.club | pve01 | 🔴 | 20 | - | GUI Lan ETS — usage inconnu, stoppé | ⚠️ à confirmer avant suppression |

> **Note** : k3sm3 et k3sa6 sont tous les deux sur pve07, tous deux stoppés. Probablement liés à une maintenance ou panne de pve07. À investiguer séparément.
> Les agents k3sa1–6 ont tous un 2e NIC sur VLAN 247 (WAN direct) — pattern intentionnel (MetalLB/LoadBalancer).

---

## VLAN 21 — LAN/management club (10.0.21.0/24) — géré par `opnsense.internal` lan

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 200002 | test-ubuntu | pve03 | 🟢 | 21 | - | VM de test sur le LAN management — running | ⚠️ usage à confirmer |
| 300100 | cisco-pnp | pve01 | 🟢 | 21 | 10.0.21.81 | Cisco PnP provisioning server | ✅ |
| 300200 | eclipse-vm | pve01 | 🟢 | 21 | - | VM lien Eclipse (cf. VLAN 65 OPNsense) | ✅ |
| 803100 | jumpbox.event.lanets.ca | pve06 | 🟢 | 21/66/67/68/69/70/247 | 142.137.247.108 + toutes IPs événement + 10.0.21.99 | Jumpbox multi-VLAN événement — admin accès universel | ✅ |
| 805100 | clonezilla.event.etsmtl.ca | pve02 | 🟢 | 21 | - | Clonezilla — imaging/backup | ✅ |
| 1100001 | forgejo-runner01 | pve01 | 🟢 | 21 | 10.0.21.71 | Runner CI Forgejo | ✅ |
| 1100002 | forgejo-runner02 | pve02 | 🟢 | 21 | 10.0.21.72 | Runner CI Forgejo | ✅ |
| 1100003 | forgejo-runner03 | pve03 | 🟢 | 21 | 10.0.21.73 | Runner CI Forgejo | ✅ |

> **Note** : `test-ubuntu` (200002) est running et a une IP DHCP. Usage indéterminé — devrait être documenté ou supprimé.

---

## VLAN 30 — CI/déploiement (10.0.30.0/24) — ⚠️ gateway inconnue

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 20500 | dhcp.deployment.etsmtl.club | pve07 | 🔴 | 30 | 10.0.30.5 | LXC — serveur DHCP pour le réseau de déploiement CI | ⚠️ stoppé + gateway 10.0.30.2 non identifiée sur aucun OPNsense |

> **Zone grise** : gateway `10.0.30.2` non trouvée sur aucun des 3 OPNsense inspectés.
> Ce réseau est peut-être routé par une autre appliance (physique? VPN?) ou simplement L2 interne.
> Ne pas supprimer sans investiguer — un réseau CI actif pourrait dépendre de cette VM.

---

## VLAN 66 — Réseau clients CTF (10.110.0.0/16) — géré par `opnsense01/02.event.lanets.ca`

### Infrastructure événement active (running)

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 700101 | opnsense01.event.lanets.ca | pve03 | 🟢 | 66/67/68/69/70/247 | - | Firewall primaire CARP événement | ✅ |
| 803100 | jumpbox.event.lanets.ca | pve06 | 🟢 | 21/66/67/68/69/70/247 | 10.110.0.99 | Jumpbox admin événement | ✅ |
| 813101 | dhcp01.camp | pve02 | 🟢 | 66 | 10.110.0.31 | DHCP primaire CTF (Kea + TFTP co-localisé) | ✅ |
| 813102 | dhcp02.camp | pve03 | 🟢 | 66 | 10.110.0.32 | DHCP secondaire CTF (hot-standby) | ✅ |
| 815101 | tftp01.camp | pve02 | 🟢 | 66 | 10.110.0.41 | TFTP (co-localisé, challenge #7 PXE) | ✅ |
| 815102 | tftp02.camp | pve03 | 🟢 | 66 | 10.110.0.42 | TFTP secondaire | ✅ |
| 816101 | portal01.camp | pve03 | 🟢 | 66 | 10.110.0.51 | Portail captif nginx (challenge #5) | ✅ |
| 819101 | secret.ctf | pve03 | 🟢 | 66 | 10.110.0.61 | Page narrative secret.ctf (challenge) | ✅ |
| 700103 | vmtest | pve03 | 🟢 | 66 | - | VM de test sur VLAN 66 — running | ⚠️ usage à confirmer |

### Challenge servers — édition passée, stoppés

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 801100 | cs01.event.lanets.ca | pve04 | 🔴 | **310** | 10.110.0.101 | Doublon cs01 sur VLAN legacy 310 | 🗑️ supprimer — VLAN 310 orphelin, doublon du 801101 |
| 801101 | cs01.event.lanets.ca | pve02 | 🔴 | 66 | 10.110.0.101 | Challenge server 1 — édition précédente | 🗑️ supprimer — stoppé, CTF passé |
| 801102 | cs02.event.lanets.ca | pve03 | 🔴 | 66 | 10.110.0.102 | Challenge server 2 | 🗑️ supprimer |
| 801103 | cs03.event.lanets.ca | pve04 | 🔴 | 66 | 10.110.0.103 | Challenge server 3 | 🗑️ supprimer |
| 801104 | cs04.event.lanets.ca | pve01 | 🔴 | 66 | 10.110.0.104 | Challenge server 4 | 🗑️ supprimer |
| 801105 | cs05.event.lanets.ca | pve02 | 🔴 | 66 | 10.110.0.105 | Challenge server 5 | 🗑️ supprimer |
| 801106 | cs06.event.lanets.ca | pve03 | 🔴 | 66 | 10.110.0.106 | Challenge server 6 | 🗑️ supprimer |
| 801107 | cs07.event.lanets.ca | pve04 | 🔴 | 66 | 10.110.0.107 | Challenge server 7 | 🗑️ supprimer |
| 801108 | cs08.event.lanets.ca | pve01 | 🔴 | 66 | 10.110.0.108 | Challenge server 8 | 🗑️ supprimer |
| 801109 | cs09.event.lanets.ca | pve02 | 🔴 | 66 | 10.110.0.109 | Challenge server 9 | 🗑️ supprimer |
| 801110 | cs10.event.lanets.ca | pve03 | 🔴 | 66 | 10.110.0.110 | Challenge server 10 | 🗑️ supprimer |
| 801111 | cs11.event.lanets.ca | pve04 | 🔴 | 66 | 10.110.0.111 | Challenge server 11 | 🗑️ supprimer |
| 801112 | cs12.event.lanets.ca | pve01 | 🔴 | 66 | 10.110.0.112 | Challenge server 12 | 🗑️ supprimer |
| 801113 | cs13.event.lanets.ca | pve02 | 🔴 | 66 | 10.110.0.113 | Challenge server 13 | 🗑️ supprimer |
| 801114 | cs14.event.lanets.ca | pve03 | 🔴 | 66 | 10.110.0.114 | Challenge server 14 | 🗑️ supprimer |
| 801115 | cs15.event.lanets.ca | pve04 | 🔴 | 66 | 10.110.0.115 | Challenge server 15 | 🗑️ supprimer |
| 801116 | cs16.event.lanets.ca | pve01 | 🔴 | 66 | 10.110.0.116 | Challenge server 16 | 🗑️ supprimer |
| 801117 | cs17.event.lanets.ca | pve02 | 🔴 | 66 | 10.110.0.117 | Challenge server 17 | 🗑️ supprimer |
| 801118 | cs18.event.lanets.ca | pve02 | 🔴 | 66 | 10.110.0.118 | Challenge server 18 | 🗑️ supprimer |
| 801119 | cs19.event.lanets.ca | pve04 | 🔴 | 66 | 10.110.0.119 | Challenge server 19 | 🗑️ supprimer |
| 801120 | cs20.event.lanets.ca | pve01 | 🔴 | 66 | 10.110.0.120 | Challenge server 20 | 🗑️ supprimer |

### Serveurs de jeux — édition passée, stoppés

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 200001 | trackmania.event.lanets.ca | pve02 | 🔴 | 66 | - | Trackmania — ancienne VM, sans IP config | 🗑️ supprimer — doublon du 801201 |
| 200003 | trackmania02.event.lanets.ca | pve02 | 🔴 | 66 | - | Trackmania 2 — ancienne VM | 🗑️ supprimer — doublon du 801202/801203? |
| 200005 | Copy-of-VM-trackmania.event.lanets.ca | pve02 | 🔴 | 66 | - | Copie Trackmania | 🗑️ supprimer — copie de test |
| 200006 | Copy-of-VM-trackmania02.event.lanets.ca | pve02 | 🔴 | 66 | - | Copie Trackmania02 | 🗑️ supprimer — copie de test |
| 801201 | trackmania.event.lanets.ca | pve01 | 🔴 | 66 | 10.110.0.151 | Trackmania — édition passée | 🗑️ supprimer (si édition terminée) |
| 801202 | archipelago.event.lanets.ca | pve01 | 🔴 | 66 | 10.110.0.152 | Archipelago — édition passée | 🗑️ supprimer (si édition terminée) |
| 801203 | minecraft.event.lanets.ca | pve01 | 🔴 | 66 | 10.110.0.153 | Minecraft — édition passée | 🗑️ supprimer (si édition terminée) |

### VMs de test / legacy

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 200007 | pxe-attempt | pve02 | 🔴 | 66 | - | Test PXE — tentative abandonnée | 🗑️ supprimer |
| 200008 | pxe-02 | pve02 | 🔴 | 66 | - | Test PXE 2 — tentative abandonnée | 🗑️ supprimer |
| 3101 | dhcp01-66-event | pve01 | 🔴 | 66 | 10.110.0.11 | Ancien DHCP VLAN 66 — remplacé par dhcp01.camp | 🗑️ supprimer |
| 3102 | dhcp02-66-event | pve01 | 🔴 | 66 | 10.110.0.12 | Ancien DHCP VLAN 66 — remplacé par dhcp02.camp | 🗑️ supprimer |
| 4101 | dns01-66-event | pve01 | 🔴 | 66 | 10.110.0.21 | Ancien DNS VLAN 66 — remplacé par dns01.camp | 🗑️ supprimer |
| 4102 | dns02-66-event | pve01 | 🔴 | 66 | 10.110.0.22 | Ancien DNS VLAN 66 — remplacé par dns02.camp | 🗑️ supprimer |

---

## VLAN 67 — AP-MGMT événement (10.120.0.0/16) — géré par `opnsense01/02.event.lanets.ca`

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 700101 | opnsense01.event.lanets.ca | pve03 | 🟢 | 66/67/68/69/70/247 | - | Firewall primaire CARP (NIC sur ce VLAN) | ✅ |
| 700102 | opnsense02.event.lanets.ca | pve07 | 🔴 | 66/67/68/69/247 | - | Firewall secondaire CARP — stoppé | ⚠️ CARP standby stoppé — pve07 en maintenance? |
| 700104 | vmtest2 | pve03 | 🟢 | 67 | - | VM de test sur VLAN 67 — running | ⚠️ usage à confirmer |
| 803100 | jumpbox.event.lanets.ca | pve06 | 🟢 | 21/66/67/68/69/70/247 | 10.120.0.99 | Jumpbox admin | ✅ |
| 817101 | monitoring01-camp | pve02 | 🟢 | 67 | 10.120.0.61 | Stack monitoring Prometheus/Grafana/Loki événement | ✅ |
| 3201 | dhcp01-67-event | pve01 | 🔴 | 67 | 10.120.0.11 | Ancien DHCP VLAN 67 | 🗑️ supprimer |
| 3202 | dhcp02-67-event | pve01 | 🔴 | 67 | 10.120.0.12 | Ancien DHCP VLAN 67 | 🗑️ supprimer |
| 4201 | dns01-67-event | pve01 | 🔴 | 67 | 10.120.0.21 | Ancien DNS VLAN 67 | 🗑️ supprimer |
| 4202 | dns02-67-event | pve01 | 🔴 | 67 | 10.120.0.22 | Ancien DNS VLAN 67 | 🗑️ supprimer |

> **Note** : `opnsense02.event.lanets.ca` (700102) est stoppé et n'a **pas** le tag 70 contrairement au primaire — probablement une incohérence de config ou il a été recréé avant l'ajout du VLAN 70.

---

## VLAN 68 — DNS/Challenges CTF (10.130.0.0/16) — géré par `opnsense01/02.event.lanets.ca`

### Infrastructure active

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 700101 | opnsense01.event.lanets.ca | pve03 | 🟢 | 66/67/68/69/70/247 | - | Firewall CARP (NIC sur ce VLAN) | ✅ |
| 803100 | jumpbox.event.lanets.ca | pve06 | 🟢 | 21/66/67/68/69/70/247 | 10.130.0.99 | Jumpbox admin | ✅ |
| 814101 | dns01.camp | pve02 | 🟢 | 68 | 10.130.0.21 | DNS BIND9 primaire (zones .ctf / .camp) | ✅ |
| 814102 | dns02.camp | pve03 | 🟢 | 68 | 10.130.0.22 | DNS BIND9 secondaire | ✅ |
| 3301 | dhcp01-68-event | pve01 | 🔴 | 68 | 10.130.0.11 | Ancien DHCP VLAN 68 | 🗑️ supprimer |
| 3302 | dhcp02-68-event | pve01 | 🔴 | 68 | 10.130.0.12 | Ancien DHCP VLAN 68 | 🗑️ supprimer |
| 4301 | dns01-68-event | pve01 | 🔴 | 68 | 10.130.0.21 | Ancien DNS VLAN 68 — **même IP que dns01.camp actif** | 🗑️ supprimer — conflit IP potentiel si démarré |
| 4302 | dns02-68-event | pve01 | 🔴 | 68 | 10.130.0.22 | Ancien DNS VLAN 68 — **même IP que dns02.camp actif** | 🗑️ supprimer — conflit IP potentiel si démarré |

### Challenges CTF — instances par équipe (toutes running)

Ces 90 VMs sont les challenges actifs du CTF SummerCamp, déployées par équipe (team 36–50 sur les nœuds pve01–pve07). Toutes sur VLAN 68 (10.130.x.x). Nommées par hash-challengename.ctf.

**Série 2001xxx — NanoControl-Credentials-1.ctf** (15 instances, pve01–pve07)

| vmid range | IPs | Statut |
|---|---|---|
| 2001036–2001050 | 10.130.1.36–.50 | 🟢 × 15 — ✅ challenges actifs |

**Série 2002xxx — NanoControl-NanoControl-2.ctf** (15 instances)

| vmid range | IPs | Statut |
|---|---|---|
| 2002036–2002050 | 10.130.2.36–.50 | 🟢 × 15 — ✅ challenges actifs |

**Série 2003xxx — MITM.ctf** (15 instances)

| vmid range | IPs | Statut |
|---|---|---|
| 2003036–2003050 | 10.130.3.36–.50 | 🟢 × 15 — ✅ challenges actifs |

**Série 2004xxx — Acces-Interdit.ctf** (15 instances)

| vmid range | IPs | Statut |
|---|---|---|
| 2004036–2004050 | 10.130.4.36–.50 | 🟢 × 15 — ✅ challenges actifs |

**Série 2005xxx — Avis-de-mauvais-temps.ctf** (15 instances)

| vmid range | IPs | Statut |
|---|---|---|
| 2005036–2005050 | 10.130.5.36–.50 | 🟢 × 15 — ✅ challenges actifs |

**Série 2006xxx — Camp-Maintenance-Signal-Brut.ctf** (15 instances)

| vmid range | IPs | Statut |
|---|---|---|
| 2006036–2006050 | 10.130.6.36–.50 | 🟢 × 15 — ✅ challenges actifs |

> **Note** : Les challenges sont numérotés par équipe (36–50 = 15 équipes). Toutes les instances sont running. À supprimer collectivement une fois l'événement terminé.

---

## VLAN 69 — Réseau événement additionnel (10.140.0.0/16) — géré par `opnsense01/02.event.lanets.ca`

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 700101 | opnsense01.event.lanets.ca | pve03 | 🟢 | 66/67/68/69/70/247 | - | Firewall CARP (NIC sur ce VLAN) | ✅ |
| 700102 | opnsense02.event.lanets.ca | pve07 | 🔴 | 66/67/68/69/247 | - | Firewall secondaire CARP | ⚠️ stoppé |
| 803100 | jumpbox.event.lanets.ca | pve06 | 🟢 | 21/66/67/68/69/70/247 | 10.140.0.99 | Jumpbox admin — NIC 10.140.0.99 | ✅ |

> **Zone grise** : aucune VM applicative sur ce VLAN. Trafic quasi nul (seulement les 2 CARP entre eux, vu lors de l'audit OPNsense). Peut-être un VLAN de réserve ou pour équipement réseau non-VM.

---

## VLAN 70 — Cache Docker (10.150.0.0/16) — géré par `opnsense01.event.lanets.ca`

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 700101 | opnsense01.event.lanets.ca | pve03 | 🟢 | 66/67/68/69/70/247 | - | Firewall CARP (NIC sur ce VLAN) — **absent de opnsense02** | ✅ |
| 803100 | jumpbox.event.lanets.ca | pve06 | 🟢 | 21/66/67/68/69/70/247 | 10.150.1.1 | Jumpbox admin — NIC sur VLAN 70 | ✅ |
| 812101 | dockercache01.camp | pve03 | 🟢 | 70/2206 | 10.150.0.100 | Cache d'images Docker (151M paquets entrants — trafic très élevé) | ✅ |

> **Note** : `opnsense02.event.lanets.ca` n'a **pas** le tag VLAN 70 alors que le primaire l'a — incohérence à corriger. `dockercache01.camp` a aussi un 2e NIC sur VLAN 2206 (voir section dédiée).

---

## VLAN 247 — WAN partagé / IP publiques directes

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 10510 | testing.lan.etsmtl.club | pve01 | 🟢 | 247 | 142.137.247.110 | VM de test avec IP publique directe | ⚠️ usage à confirmer |
| 100201 | opnsense01.prod.lanets.ca | pve04 | 🟢 | 247 | - | **3e OPNsense** (OPNsense.lanets.ca, 172.16.10.2) — WAN partagé | ✅ |
| 200000 | CT200000 | pve01 | 🔴 | 247/500 | 142.137.247.104 / 10.5.0.253 | LXC sans nom — IPs 142.137.247.104 et 10.5.0.253. Stoppé | ⚠️ IP 142.137.247.104 = même que uploadbox! à vérifier |
| 400101 | opnsense01 | pve03 | 🔴 | 247 | - | Instance OPNsense stoppée — rôle inconnu (spare? ancienne config?) | ⚠️ à confirmer |
| 400102 | opnsense02 | pve02 | 🔴 | 247 | - | Instance OPNsense stoppée | ⚠️ à confirmer |
| 701101 | uploadbox.dciets.com | pve04 | 🟢 | 247 | 142.137.247.104 | Upload box avec IP publique directe | ✅ |
| 803100 | jumpbox.event.lanets.ca | pve06 | 🟢 | 21/66/67/68/69/70/247 | 142.137.247.108 | Jumpbox — IP publique 142.137.247.108 | ✅ |
| 850101 | ctfd.summercamp.dciets.com | pve03 | 🟢 | 247 | 142.137.247.107 | CTFd — plateforme des challenges SummerCamp | ✅ |
| k3sa1–k3sa6 | (voir VLAN 20) | - | 🟢 | 20/247 | - | Agents k3s avec NIC WAN direct | ✅ (intentionnel) |
| k8s workers (1003/1009/1010) | (voir sections VLAN 1003/1009/1010) | - | 🟢 | 247/500/10xx | - | Workers k8s avec NIC WAN direct | ✅ (intentionnel, MetalLB) |

> **Conflit IP** : `CT200000` (vmid 200000, stoppé) déclare `142.137.247.104` — même IP qu'`uploadbox.dciets.com` (vmid 701101, running). Si CT200000 était démarré, conflit immédiat. **Ne pas démarrer sans investigation.**

> **Instances OPNsense orphelines** (400101, 400102) : stoppées sur le VLAN 247 seulement. Peut-être des instances de test/spare ou des configs avant migration. À confirmer avec l'équipe avant suppression.

---

## VLAN 310 — Legacy doublon cs01

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 801100 | cs01.event.lanets.ca | pve04 | 🔴 | **310** | 10.110.0.101 | Doublon cs01 sur VLAN 310 (orphelin côté OPNsense) | 🗑️ supprimer — VLAN 310 inutilisé |

---

## VLAN 500 — Services inter-k8s (10.5.0.0/24) — géré par `opnsense.internal` opt5

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 200000 | CT200000 | pve01 | 🔴 | 247/500 | 10.5.0.253 | LXC sans nom — NIC sur le réseau services. Stoppé | ⚠️ usage inconnu, voir conflit IP 247 |
| 1003000 | k8s-cedille-sandbox-controlplane-0 | pve03 | 🟢 | 500/1003 | - | Controlplane k8s sandbox | ✅ |
| 1003010 | k8s-cedille-sandbox-worker-0 | pve03 | 🟢 | 247/500/1003 | - | Worker k8s sandbox | ✅ |
| 1003011 | k8s-cedille-sandbox-worker-1 | pve04 | 🟢 | 247/500/1003 | - | Worker k8s sandbox | ✅ |
| 1003012 | k8s-cedille-sandbox-worker-2 | pve06 | 🟢 | 247/500/1003 | - | Worker k8s sandbox | ✅ |
| 1009000–1009003 | k8s-shared-controlplane-0–3 | pve03–pve07 | 🟢 | 500/1009 | - | Controlplanes k8s shared | ✅ |
| 1009010–1009015 | k8s-shared-worker-0–5 | pve01–pve07 | 🟢 | 247/500/1009 | - | Workers k8s shared | ✅ |
| 1010000–1010003 | k8s-cedille-production-v2-controlplane-0–3 | pve03–pve07 | 🟢 | 500/1010 | - | Controlplanes k8s prod-v2 | ✅ |
| 1010010–1010015 | k8s-cedille-production-v2-worker-0–5 | pve01–pve07 | 🟢 | 247/500/1010 | - | Workers k8s prod-v2 | ✅ |

---

## VLAN 601 — Cluster k3s k3s-m0x/k3s-w0x (10.60.10.0/24) — ⚠️ gateway inconnue

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 600101 | k3s-m01 | pve01 | 🟢 | 601 | 10.60.10.101 | Master k3s — cluster indépendant | ✅ garder / ⚠️ gateway à identifier |
| 600102 | k3s-m02 | pve02 | 🟢 | 601 | 10.60.10.102 | Master k3s | ✅ garder / ⚠️ gateway à identifier |
| 600103 | k3s-m03 | pve01 | 🟢 | 601 | 10.60.10.103 | Master k3s | ✅ garder / ⚠️ gateway à identifier |
| 600201 | k3s-w01 | pve01 | 🟢 | 601 | 10.60.10.111 | Worker k3s | ✅ garder / ⚠️ gateway à identifier |
| 600202 | k3s-w02 | pve02 | 🟢 | 601 | 10.60.10.112 | Worker k3s | ✅ garder / ⚠️ gateway à identifier |
| 600203 | k3s-w03 | pve01 | 🟢 | 601 | 10.60.10.113 | Worker k3s | ✅ garder / ⚠️ gateway à identifier |
| 600204 | k3s-w04 | pve02 | 🟢 | 601 | 10.60.10.114 | Worker k3s | ✅ garder / ⚠️ gateway à identifier |
| 600205 | k3s-w05 | pve01 | 🟢 | 601 | 10.60.10.115 | Worker k3s | ✅ garder / ⚠️ gateway à identifier |

> **Zone grise** : réseau `10.60.10.0/24` sur VLAN 601 — non géré par aucun des 3 OPNsense inspectés. Toutes les VMs sont running. Probablement un réseau L2 interne sans gateway OPNsense (cluster k3s auto-contenu) ou routé par un équipement non inspecté.

---

## VLAN 1003 — k8s "cedille-sandbox" (10.10.1.128/25) — géré par `opnsense.internal` opt3

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 1003000 | k8s-cedille-sandbox-controlplane-0 | pve03 | 🟢 | 500/1003 | - | Controlplane unique (sandbox = 1 CP) | ✅ |
| 1003010 | k8s-cedille-sandbox-worker-0 | pve03 | 🟢 | 247/500/1003 | - | Worker 0 | ✅ |
| 1003011 | k8s-cedille-sandbox-worker-1 | pve04 | 🟢 | 247/500/1003 | - | Worker 1 | ✅ |
| 1003012 | k8s-cedille-sandbox-worker-2 | pve06 | 🟢 | 247/500/1003 | - | Worker 2 | ✅ |

---

## VLAN 1009 — k8s "shared" (10.5.9.0/24) — géré par `opnsense.internal` opt10

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 1009000 | k8s-shared-controlplane-0 | pve03 | 🟢 | 500/1009 | - | CP 0 — cluster le plus chargé | ✅ |
| 1009001 | k8s-shared-controlplane-1 | pve04 | 🟢 | 500/1009 | - | CP 1 | ✅ |
| 1009002 | k8s-shared-controlplane-2 | pve06 | 🟢 | 500/1009 | - | CP 2 | ✅ |
| 1009003 | k8s-shared-controlplane-3 | pve07 | 🟢 | 500/1009 | - | CP 3 | ✅ |
| 1009010 | k8s-shared-worker-0 | pve01 | 🟢 | 247/500/1009 | - | Worker 0 | ✅ |
| 1009011 | k8s-shared-worker-1 | pve02 | 🟢 | 247/500/1009 | - | Worker 1 | ✅ |
| 1009012 | k8s-shared-worker-2 | pve03 | 🟢 | 247/500/1009 | - | Worker 2 | ✅ |
| 1009013 | k8s-shared-worker-3 | pve04 | 🟢 | 247/500/1009 | - | Worker 3 | ✅ |
| 1009014 | k8s-shared-worker-4 | pve06 | 🟢 | 247/500/1009 | - | Worker 4 | ✅ |
| 1009015 | k8s-shared-worker-5 | pve07 | 🟢 | 247/500/1009 | - | Worker 5 | ✅ |

---

## VLAN 1010 — k8s "cedille-production-v2" (10.5.10.0/24) — géré par `opnsense.internal` opt13

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 1010000 | k8s-cedille-production-v2-controlplane-0 | pve03 | 🟢 | 500/1010 | - | CP 0 | ✅ |
| 1010001 | k8s-cedille-production-v2-controlplane-1 | pve04 | 🟢 | 500/1010 | - | CP 1 | ✅ |
| 1010002 | k8s-cedille-production-v2-controlplane-2 | pve06 | 🟢 | 500/1010 | - | CP 2 | ✅ |
| 1010003 | k8s-cedille-production-v2-controlplane-3 | pve07 | 🟢 | 500/1010 | - | CP 3 | ✅ |
| 1010010 | k8s-cedille-production-v2-worker-0 | pve01 | 🟢 | 247/500/1010 | - | Worker 0 | ✅ |
| 1010011 | k8s-cedille-production-v2-worker-1 | pve02 | 🟢 | 247/500/1010 | - | Worker 1 | ✅ |
| 1010012 | k8s-cedille-production-v2-worker-2 | pve03 | 🟢 | 247/500/1010 | - | Worker 2 | ✅ |
| 1010013 | k8s-cedille-production-v2-worker-3 | pve04 | 🟢 | 247/500/1010 | - | Worker 3 | ✅ |
| 1010014 | k8s-cedille-production-v2-worker-4 | pve06 | 🟢 | 247/500/1010 | - | Worker 4 | ✅ |
| 1010015 | k8s-cedille-production-v2-worker-5 | pve07 | 🟢 | 247/500/1010 | - | Worker 5 | ✅ |

---

## VLAN 2206 — 2e NIC dockercache01.camp

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 812101 | dockercache01.camp | pve03 | 🟢 | 70/2206 | 10.150.0.100 | Cache Docker — 2e NIC VLAN 2206 (usage inconnu, probablement peering interne) | ✅ / ⚠️ rôle du VLAN 2206 à documenter |

---

## VMs sans tag VLAN (VLAN natif/untagged de vmbr1)

| vmid | Nom | Nœud | Statut | VLANs | IP | Usage | Reco |
|---|---|---|---|---|---|---|---|
| 2000 | template-opnsense | pve01 | 📦 | aucun | - | Template OPNsense de référence | ✅ |
| 300101 | controlplane-01.etsmtl.club | pve03 | 🟢 | aucun | - | Controlplane management — usage à clarifier | ⚠️ pas de tag = VLAN natif du trunk, intentionnel? |
| 500001 | controlplane-01.management.etsmtl.ca | pve03 | 🟢 | aucun | - | Controlplane management .ca | ⚠️ même VLAN natif, même nœud |
| 500011 | worker-01.management.etsmtl.club | pve02 | 🟢 | aucun | - | Worker management | ⚠️ VLAN natif |

> **Note** : Ces 3 VMs running sont sur le VLAN natif/untagged de vmbr1. Peut-être intentionnel (management Proxmox lui-même = pas de tag) ou une incohérence de config. À confirmer avant toute action de switch (pruning du VLAN natif pourrait les couper).

---

## Récapitulatif — Candidats suppression (🗑️)

### Groupe 1 — Anciens DHCP/DNS événement (remplacés par les `.camp` actifs)

| vmid | Nom | Motif |
|---|---|---|
| 3101 | dhcp01-66-event | Remplacé par dhcp01.camp (813101) |
| 3102 | dhcp02-66-event | Remplacé par dhcp02.camp (813102) |
| 3201 | dhcp01-67-event | Remplacé — VLAN 67 géré par les mêmes DHCP camp |
| 3202 | dhcp02-67-event | Remplacé |
| 3301 | dhcp01-68-event | Remplacé |
| 3302 | dhcp02-68-event | Remplacé |
| 4101 | dns01-66-event | Remplacé par dns01.camp (814101) |
| 4102 | dns02-66-event | Remplacé par dns02.camp (814102) |
| 4201 | dns01-67-event | Remplacé |
| 4202 | dns02-67-event | Remplacé |
| 4301 | dns01-68-event | Remplacé — **⚠️ même IP que dns01.camp actif (10.130.0.21), conflit si démarré** |
| 4302 | dns02-68-event | Remplacé — **⚠️ même IP que dns02.camp actif (10.130.0.22), conflit si démarré** |

**Total : 12 VMs** — toutes stoppées, toutes remplacées.

### Groupe 2 — Challenge servers édition passée (cs01–cs20)

| vmid range | Noms | Motif |
|---|---|---|
| 801100 | cs01 (VLAN 310) | Doublon sur VLAN 310 orphelin |
| 801101–801120 | cs01–cs20.event.lanets.ca | 20 VMs stoppées — CTF édition précédente |

**Total : 21 VMs** — toutes stoppées. À supprimer une fois confirmé que l'édition CTF précédente est bien terminée et que les données ne sont plus nécessaires.

### Groupe 3 — Serveurs de jeux / copies de test

| vmid | Nom | Motif |
|---|---|---|
| 200001 | trackmania.event.lanets.ca | Ancienne VM sans IP, doublon du 801201 |
| 200003 | trackmania02.event.lanets.ca | Ancienne VM sans IP |
| 200005 | Copy-of-VM-trackmania.event.lanets.ca | Copie de test |
| 200006 | Copy-of-VM-trackmania02.event.lanets.ca | Copie de test |
| 200007 | pxe-attempt | Test PXE abandonné |
| 200008 | pxe-02 | Test PXE abandonné |
| 801201 | trackmania.event.lanets.ca | Stoppé — édition passée (à confirmer) |
| 801202 | archipelago.event.lanets.ca | Stoppé — édition passée |
| 801203 | minecraft.event.lanets.ca | Stoppé — édition passée |

**Total : 9 VMs** — toutes stoppées.

### Groupe 4 — Challenges CTF SummerCamp actifs (à supprimer après l'événement)

Les 90 VMs 2001036–2006050 (6 séries × 15 équipes) sont **running** et actives. À supprimer collectivement une fois l'événement SummerCamp terminé. **Ne pas supprimer maintenant.**

---

## Zones grises — à investiguer avant toute action

| vmid | Nom | Anomalie | Action requise |
|---|---|---|---|
| 200000 | CT200000 (LXC sans nom) | IP 142.137.247.104 = même qu'uploadbox.dciets.com (701101) ; aussi sur VLAN 500 (10.5.0.253). Stoppé. | Identifier l'usage avant de démarrer ou supprimer — conflit IP garanti si démarré |
| 400101 | opnsense01 | VM OPNsense stoppée, VLAN 247 seulement. Rôle inconnu. | Spare? config test? Confirmer avec l'équipe |
| 400102 | opnsense02 | VM OPNsense stoppée, VLAN 247 seulement. | Idem |
| 200002 | test-ubuntu | Running, VLAN 21, pas d'IP fixe config. | Documenter l'usage ou supprimer |
| 700103 | vmtest | Running, VLAN 66. | Documenter l'usage ou supprimer |
| 700104 | vmtest2 | Running, VLAN 67. | Documenter l'usage ou supprimer |
| 10510 | testing.lan.etsmtl.club | Running, VLAN 247, IP publique 142.137.247.110. | IP publique directe — à valider si intentionnel |
| 200004 | gui.lan.etsmtl.club | Stoppé, VLAN 20. | Usage inconnu — GUI pour le cluster k3s? |
| 20500 | dhcp.deployment.etsmtl.club | LXC stoppé, VLAN 30, gateway 10.0.30.2 inconnue | Identifier gateway et usage CI avant toute action |
| 10130 | k3sm3.lan.etsmtl.club | Master k3s stoppé (pve07) | pve07 en maintenance? Cohérence cluster k3s? |
| 10260 | k3sa6.lan.etsmtl.club | Agent k3s stoppé (pve07) | Idem |
| 700102 | opnsense02.event.lanets.ca | CARP standby stoppé, manque tag VLAN 70 | pve07 en maintenance; corriger la config VLAN 70 |
| 812101 | dockercache01.camp | VLAN 2206 — rôle de ce 2e NIC non documenté | Documenter le peering VLAN 2206 |
| 300101, 500001, 500011 | controlplane/worker management | Aucun tag VLAN (VLAN natif) | Confirmer si intentionnel avant pruning switch |
| VLAN 601 (8 VMs k3s-m/w) | k3s-m01–03, k3s-w01–05 | Gateway VLAN 601 non identifiée sur aucun OPNsense | Identifier la gateway ou confirmer réseau L2 auto-contenu |

---

## Synthèse des suppressions recommandées

| Groupe | # VMs | vmids | Statut actuel |
|---|---|---|---|
| Anciens DHCP/DNS événement | **12** | 3101,3102,3201,3202,3301,3302,4101,4102,4201,4202,4301,4302 | 🔴 tous stoppés |
| cs01–cs20 + doublon tag-310 | **21** | 801100–801120 | 🔴 tous stoppés |
| Serveurs jeux + copies test | **9** | 200001,200003,200005,200006,200007,200008,801201,801202,801203 | 🔴 tous stoppés |
| **Total suppression ferme** | **42** | — | 🔴 stoppés |
| Challenges CTF (après événement) | 90 | 2001036–2006050 | 🟢 running — **NE PAS SUPPRIMER MAINTENANT** |

**42 VMs stoppées** sont candidates à une suppression ferme, libérant de l'espace disque et simplifiant l'inventaire. Aucune n'est running.
