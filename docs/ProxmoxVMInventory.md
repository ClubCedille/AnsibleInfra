# Inventaire Proxmox — VMs/CT et mapping VLAN

> ⚠️ **Document remplacé** : voir [`VMInventoryAudit.md`](VMInventoryAudit.md) pour
> l'audit complet et exhaustif (209 VMs, recommandations suppression, zones grises) —
> produit le 2026-06-23 à partir des données fraîches de l'API Proxmox.
> Ce document reste utile pour les constats macro et l'historique de l'analyse initiale.

> Inventaire complet du cluster Proxmox `OneBigCluster` (10.0.21.51), collecté en
> lecture seule (lecture directe de `/etc/pve/nodes/*/{qemu-server,lxc}/*.conf` +
> `pvesh get /cluster/resources` pour les statuts) en juin 2026.
>
> Objectif : valider quelles VMs existent réellement, sur quels VLANs (tags 802.1Q)
> elles peuvent communiquer, et croiser ça avec l'audit de
> [`OpnsenseInternalETSMTL.md`](OpnsenseInternalETSMTL.md) pour distinguer les VLANs
> réellement morts des faux signaux de trafic.

---

## Cluster

- Nom : `OneBigCluster`, 7 nœuds quorum (`pve01, pve02, pve03, pve04, pve06, pve07,
pve08` — **pas de `pve05`**, numérotation non contiguë, normal).
- **207 VMs QEMU + 2 conteneurs LXC** au total.
- Statuts : **157 `running`**, 52 `stopped` (aucun en `paused`/`suspended`).
- Bridge principal : `vmbr1` (266 NICs dessus) — trunk 802.1Q portant tous les VLANs.
  `vmbr2` (16 NICs) et `vmbr3` (3 NICs) sont utilisés spécifiquement par le cluster
  CARP événementiel (`opnsense01/02.event.lanets.ca`). `vmbr0` n'a qu'une seule NIC
  (probablement le management Proxmox lui-même).

## Mapping VLAN → usage réel (tous les tags vus sur `vmbr1`)

| Tag       | # VMs | Usage identifié                                                                                                                                                     | Géré par OPNsense ?                                             |
| --------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 20        | 11    | Cluster k3s "Lan ETS" (k3sm1-3, k3sa1-6)                                                                                                                            | `opnsense.internal` (opt12)                                     |
| 21        | 8     | LAN/management (cisco-pnp, eclipse-vm, clonezilla, forgejo-runner01-03, test-ubuntu)                                                                                | `opnsense.internal` (lan)                                       |
| 30        | 2     | `dhcp.deployment.etsmtl.club` (LXC, gw déclaré `10.0.30.2`)                                                                                                         | **Non** — gateway externe à confirmer                           |
| 66        | 44    | Réseau "client" événement CTF (10.110.0.0/16, cf. `CLAUDE.md`)                                                                                                      | `opnsense01/02.event.lanets.ca`                                 |
| 67        | 10    | Réseau "AP-MGMT" événement (10.120.0.0/16)                                                                                                                          | `opnsense01/02.event.lanets.ca`                                 |
| 68        | 100   | Réseau DNS/challenges CTF (la grande majorité des VMs `*.ctf`)                                                                                                      | `opnsense01/02.event.lanets.ca`                                 |
| 69        | 4     | Réseau événement additionnel (non documenté dans `CLAUDE.md`)                                                                                                       | `opnsense01/02.event.lanets.ca`                                 |
| 70        | 4     | Réseau événement additionnel (non documenté dans `CLAUDE.md`)                                                                                                       | `opnsense01/02.event.lanets.ca`                                 |
| 247       | 33    | **VLAN de livraison WAN/Internet partagé** (NIC WAN des deux OPNsense + IP publiques directes pour plusieurs services)                                              | Bypass OPNsense pour les VMs autres que les firewalls eux-mêmes |
| 310       | 1     | `cs01.event.lanets.ca` (vmid 801100, stoppé) — doublon apparent de `cs01` (vmid 801101, tag 66)                                                                     | Inconnu — probablement obsolète                                 |
| 500       | 25    | NIC "services" interne k8s (control plane / inter-nœuds), partagé par tous les clusters k8s                                                                         | `opnsense.internal` (opt5)                                      |
| 601       | 8     | Cluster `k3s-m01-03`/`k3s-w01-05` — **pas dans la liste des VLANs de `opnsense.internal`**                                                                          | **Non identifié** — gateway externe à confirmer                 |
| 1003      | 4     | k8s "cedille-sandbox" (controlplane-0, worker-0/1/2)                                                                                                                | `opnsense.internal` (opt3)                                      |
| 1009      | 10    | k8s "shared" (controlplane-0..3, worker-0..5)                                                                                                                       | `opnsense.internal` (opt10)                                     |
| 1010      | 10    | k8s "cedille-production-v2" (controlplane-0..3, worker-0..5)                                                                                                        | `opnsense.internal` (opt13)                                     |
| 2206      | 1     | second NIC de `dockercache01.camp`                                                                                                                                  | Probablement événement (`.camp`)                                |
| _(aucun)_ | 4     | `template-opnsense`, `controlplane-01.etsmtl.club`, `controlplane-01.management.etsmtl.ca`, `worker-01.management.etsmtl.club` — sur le VLAN natif/untag de `vmbr1` | **Non identifié** — à clarifier (intentionnel ou oubli ?)       |

**Tags définis dans `opnsense.internal` (10.0.21.1) mais sans aucune VM** : `1001`
(k8s01), `1002` (k8s02), `1004` (k8s04), `1005` (k8s05), `1006` (k8s06), `1007`
(k8s07), `1008` (k8s08), `1011`, `65` (Eclipse) — **confirmation forte** qu'il s'agit
de VLANs morts, cohérente avec l'absence de trafic observée côté OPNsense sur 30
jours. Voir le tableau "Morts confirmés" mis à jour dans
[`OpnsenseInternalETSMTL.md`](OpnsenseInternalETSMTL.md).

## Constats notables

### 1. VLAN 247 = sortie WAN partagée, pas un VLAN mort

Le tag 247 porte le NIC WAN de `opnsense.internal` (vmid 100201, `net1`) **et** celui
de `opnsense01.event.lanets.ca` (vmid 700101, `net4`) — c'est le segment qui relie les
deux pare-feux à l'uplink Internet réel au niveau Proxmox. Il porte aussi des IP
publiques directes pour des services qui n'ont pas besoin de passer par un pare-feu
applicatif (`uploadbox.dciets.com`, `ctfd.summercamp.dciets.com`,
`jumpbox.event.lanets.ca`, `testing.lan.etsmtl.club`) — cohérent et probablement
volontaire.

### 2. Plusieurs workers k8s ont un 3ᵉ NIC directement sur le VLAN 247 (WAN)

Les workers des trois clusters k8s (`k8s-cedille-sandbox-worker-*`,
`k8s-shared-worker-*`, `k8s-cedille-production-v2-worker-*`) ont systématiquement
3 NICs : `net0` (500, services), `net1` (1003/1009/1010, cluster k8s), **et `net2`
(247, WAN)**. Les control-planes, eux, n'ont que 2 NICs (500 + cluster), pas de NIC
WAN direct.

→ **Ceci bypass complètement `opnsense.internal`** : ces workers ont une IP publique
ou en tout cas un accès direct au WAN sans passer par le pare-feu interne — pattern
cohérent avec un usage MetalLB/LoadBalancer pour exposer des services k8s
publiquement, mais à valider que c'est bien voulu et pas un oubli d'architecture.
**Recommandation** : documenter explicitement ce choix (ou le retirer si les
workers n'ont plus besoin d'IP publique directe) avant la duplication de
l'infrastructure.

### 3. VLAN 601 (cluster k3s `k3s-m0x`/`k3s-w0x`) — gateway inconnue

8 VMs sur tag 601, mais ce tag n'apparaît dans la configuration VLAN d'aucun des
OPNsense inspectés (`opnsense.internal` ni le cluster CARP événement). Soit il existe
un troisième routeur/gateway pour ce réseau (à identifier), soit ce cluster n'a pas de
gateway L3 du tout (réseau purement L2/interne sans sortie). À clarifier avant toute
action de nettoyage qui toucherait au trunk.

### 4. VLAN 30 — gateway externe déclarée mais non identifiée

Le conteneur LXC `dhcp.deployment.etsmtl.club` déclare `gw=10.0.30.2` — ce n'est ni
`opnsense.internal` (10.0.21.1) ni un OPNsense visiblement inspecté. Probablement un
réseau de déploiement/CI séparé, à documenter séparément si pertinent.

### 5. VMs sur le VLAN natif (sans tag) de `vmbr1`

`controlplane-01.etsmtl.club`, `controlplane-01.management.etsmtl.ca`,
`worker-01.management.etsmtl.club` (et le template `template-opnsense`, normal pour
un template non démarré) n'ont aucun tag VLAN — donc sur le VLAN natif/untagged du
trunk. À vérifier si c'est intentionnel (réseau de management Proxmox lui-même,
potentiellement le même que VLAN 21 mais en untagged côté switch) ou une
incohérence de configuration.

### 6. VMs "fantômes"/doublons stoppées — candidats au nettoyage Proxmox

En plus des VLANs morts, plusieurs VMs **stoppées** semblent être des restes
d'anciennes itérations de l'infra événementielle, à nettoyer indépendamment de
l'audit OPNsense :

- `dhcp01-66/67/68-event`, `dhcp02-66/67/68-event` (6 VMs, vmid 3101-3302) et
  `dns01-66/67/68-event`, `dns02-66/67/68-event` (6 VMs, vmid 4101-4302) — toutes
  stoppées, remplacées en pratique par `dhcp01/02.camp` et `dns01/02.camp` qui
  tournent activement.
- `cs01.event.lanets.ca` en double : vmid 801100 (tag 310, stoppé) **et** vmid
  801101 (tag 66, stoppé) — config dupliquée/legacy.
- 20 VMs `cs01-cs20.event.lanets.ca` (vmid 801101-801120), toutes stoppées —
  probablement des challenge servers d'une édition précédente du CTF, à confirmer
  avant suppression définitive.
- `pxe-02`, `pxe-attempt`, `trackmania*`, `Copy-of-VM-trackmania*` (plusieurs copies)
  — restes de tests, tous stoppés.

---

## Méthode (pour reproductibilité)

Lecture directe des fichiers de config pmxcfs plutôt que des appels API séquentiels
par VM (`pvesh get /nodes/<node>/qemu/<vmid>/config` un par un est ~100x plus lent sur
un cluster de cette taille et a été abandonné en cours d'exécution) :

```bash
# Liste tous les statuts en un seul appel API
pvesh get /cluster/resources --output-format json

# Liste toutes les configs VM/CT directement via le filesystem cluster (instantané,
# synchronisé sur tous les nœuds)
/etc/pve/nodes/*/qemu-server/*.conf
/etc/pve/nodes/*/lxc/*.conf
```

## Limites de cet inventaire

- Les noms de VLAN/cluster (k3s, k8s-shared, "Lan ETS", etc.) sont déduits des noms de
  VM et des tags, pas confirmés explicitement par l'utilisateur.
- Les tags 30 et 601 n'ont pas de gateway identifiée dans ce document — nécessite une
  vérification additionnelle (autre routeur ? réseau purement L2 ?) avant toute
  modification de switch/trunk.
- Aucune action corrective n'a été effectuée — inventaire en lecture seule uniquement.
