# Switches Cisco — topologie, inventaire et propagation des VLANs

> État opérationnel observé le **2026-11-27** (LLDP/CDP + `show run` sur les équipements
> accessibles). Ce document décrit **l'état et les liens**, pas la procédure de mise à jour
> d'une interface. Il complète [`docs/VLANRegistry.md`](../../docs/VLANRegistry.md) (registre
> des VLANs côté Proxmox/OPNsense) et [`docs/cisco-pnp.md`](../../docs/cisco-pnp.md) (workflow PnP).

---

## 1. Périmètre des playbooks

| Fichier | Hôtes (inventaire `infra`) | Effet |
|---|---|---|
| `deployment.yaml` | `switches_event` | Config Day-1 (trunk, ports access, AAA) via le rôle `cedille.cisco-3850.config` |
| `snmp.yaml` | `ios` (play commenté), `nxos` | Communauté SNMP v2c read-only pour Prometheus |

**Source de vérité des VLANs** : `inventories/infra/group_vars/pve.yaml`
(`pve_vlans_desired` / `pve_vlans_to_remove`), synchronisée par
`playbooks/network/update-vlans.yaml` :

- Play 1 : sous-interfaces `vmbr1.<id>` sur les 8 PVE ;
- Play 2 : création des VLANs sur les switches du groupe `nxos` (`state: merged` — les VLANs
  non listés ne sont **pas** supprimés, d'où la persistance de VLANs legacy sur les switches).

Conventions de connexion Ansible : `inventories/infra/group_vars/switches.yaml`
(`ansible.netcommon.network_cli` + paramiko, `HostKeyAlgorithms: [ssh-rsa]`) et
`group_vars/nxos.yaml` (`ansible_user: admin`, mot de passe vaulté).

---

## 2. Inventaire vs équipements réels

| Nom dans l'inventaire | Hostname réel | IP de mgmt | Modèle | OS / version | Rôle |
|---|---|---|---|---|---|
| `data01.mgmt.etsmtl.club` (`nxos`) | `core01.etsmtl.club` | 10.0.21.11 | Cisco Nexus **C3064PQ** | NX-OS 7.0(3)I6(2) | Agrégation / cœur de réseau |
| `data02.mgmt.etsmtl.club` (`nxos`) | `top-sw1.infra.lanets.ca` (« TopRack D2021 ») | 10.0.21.12 | Cisco Nexus **C3064PQ** | NX-OS 7.0(3)I6(2) | Top-of-rack PVE |
| *(absent de l'inventaire)* | `mgmt-02.etsmtl.club` | 10.0.21.13 | Cisco **WS-C3850-48P** | IOS XE 16.12.10a | Switch de management |
| *(absent de l'inventaire)* | `mgmt-03.etsmtl.club` | 10.0.21.15 | Cisco **WS-C3560X-48** | IOS 15.0(2)SE10a | Switch de management |
| `management.prod.lanets.ca` (`ios`) | inconnu | 10.0.21.21 | inconnu | inconnu | **Non joignable** (ARP `INCOMPLETE`, ports filtrés) |
| *(absent de l'inventaire)* | inconnu | 10.0.21.22 | inconnu | inconnu | **Non joignable** |
| *(absent de l'inventaire)* | `daswitch.eclipse.ca` | 10.241.92.15 | WS-C3560X-48P | IOS 15.2(4)E10 | Lien vers l'infra ÉTS « eclipse » |
| *(absent de l'inventaire)* | `sw001.etsmtl.club.pnp01.mgmt.etsmtl.club` | — | WS-C3850-48P | IOS XE 16.12.10a | Switch PnP / management |
| *(absent de l'inventaire)* | `NServSw1-D2-1-SwSvrClub` | gateway 10.194.24.1 | HPE ANW **R8Q69A** | ML.10.16.1040 | Lien infrastructure ÉTS (VLAN 2206) — **non-Cisco** |

> **Écart important** : mgmt-02 (`.13`) et mgmt-03 (`.15`) ne sont pas dans l'inventaire
> Ansible, alors qu'ils portent les liens de management et le chemin du VLAN 1009 vers le
> nouveau Proxmox. À ajouter aux groupes `ios`/`switches` si leur configuration doit être
> gérée par Ansible.

---

## 3. Topologie physique

```mermaid
graph TD
    HPE["HPE Aruba NServSw1-D2-1-SwSvrClub<br/>port 2/1/8 — access VLAN 2206"]
    NPVE["Nouveau PVE — 10.194.24.101<br/>hostname 'pve01' (collision de nom avec la prod)"]
    MGM3["mgmt-03 — 10.0.21.15<br/>WS-C3560X-48"]
    MGM2["mgmt-02 — 10.0.21.13<br/>WS-C3850-48P"]
    TSW["top-sw1 / data02 — 10.0.21.12<br/>Nexus C3064PQ"]
    CORE["core01 / data01 — 10.0.21.11<br/>Nexus C3064PQ"]
    PVE["PVE01–PVE08 — 10.0.21.51–58"]
    ECL["daswitch.eclipse.ca — 10.241.92.15"]

    HPE -->|nic0, untagged 2206| NPVE
    NPVE -->|nic1 — trunk natif 21, tag 1009| MGM3
    MGM3 -->|Gi0/48 ↔ Gi1/0/37 — trunk natif 21, 21+1009| MGM2
    MGM2 -->|Po5 (Ten1/1/3-4) ↔ Po100 (Eth1/45-46)| TSW
    TSW -->|Po7 « LIEN_PROD » (Eth1/41-42) ↔ Po100 (Eth1/47-48)| CORE
    CORE -->|Eth1/1–16| PVE
    TSW -->|Eth1/1–16| PVE
    CORE -->|Eth1/31| ECL
    CORE -->|Eth1/44| SW001["sw001…pnp01… (WS-C3850)"]
    MGM3 -->|Gi0/9| RT["RT-AC68U (routeur WiFi)"]
```

### Liens inter-switches

| Local | Port / channel | Remote | Remote port | Remarque |
|---|---|---|---|---|
| core01 | `Eth1/47-48` → `Po100` | top-sw1 | `Eth1/42`, `Eth1/41` → `Po7` (`LIEN_PROD`) | Trunk `1-4094`, natif 1. Côté top-sw1, `spanning-tree bpdufilter enable` |
| top-sw1 | `Eth1/45-46` → `Po100` | mgmt-02 | `Ten1/1/3-4` → `Po5` | Trunk natif **21**, autorise `21,1009` |
| mgmt-02 | `Gi1/0/37` | mgmt-03 | `Gi0/48` | Trunk natif **21**, autorise `21,1009` |
| mgmt-03 | `Gi0/9` | RT-AC68U | — | Accès VLAN 21 — chemin historique des sessions SSH |
| top-sw1 | `Po5` (`Eth1/47-48`) | *(pair / lien non identifié)* | — | Trunk `66-69,247,1009,2206`, natif 1 — à confirmer |

### Ports des hyperviseurs (LLDP/CDP observés)

| Switch | Ports | Équipement |
|---|---|---|
| core01 | `Eth1/1-2`, `3-4`, `5-6`, `7-8`, `9-10`, `11-12`, `13-14`, `15-16` | PVE01 … PVE08 (trunks 10G, port-channels `Po1`–`Po8`) |
| core01 | `Eth1/17-18` | NAS01 (`Po14`, VLAN 21) |
| top-sw1 | `Eth1/1-2`, `3-4`, `5-6`, `10`, `13-14`, `15` | PVE01, PVE02, PVE03, PVE05, PVE07, PVE08 |
| top-sw1 | `Eth1/17-18` | NAS01 |
| mgmt-02 | `Gi1/0/1`, `/3`, `/41` | PVE01, PVE02 |
| mgmt-02 | `Gi1/0/5`, `/9`, `/12`, `/13`, `/16` | PVE03, PVE05, PVE06, PVE08, PVE07 |
| mgmt-03 | `Gi0/23`, `Gi0/25` | PVE03, PVE01 (voisins LLDP historiques) |
| mgmt-03 | `Gi0/26` | **Nouveau PVE**, `nic1` (MAC `d8:5e:d3:8e:9e:a8`) |

---

## 4. Propagation des VLANs

### 4.1 Rôle des VLANs (source : `group_vars/pve.yaml`)

| VLAN | Nom / rôle | Réseau | Remarque |
|---|---|---|---|
| 15 | CEPH | 10.0.15.0/24 | MTU 9216 |
| 21 | LAN management | 10.0.21.0/24 | Natif sur tous les liens mgmt-02/mgmt-03 |
| 30 | Deploiement Day 0 — Switches | 10.0.30.0/24 | Bootstrap Cisco PnP |
| 40 / 45 / 48 | CI/CD Forgejo / Monitoring / Utilitaires | 10.0.40/45/48.0/24 | Segmentation en cours du VLAN 21 |
| 65 | Eclipse link | 10.255.255.252/30 | Conservé explicitement |
| 66–69 | Événements (CLIENT / AP-MGMT / DNS-CTF / additionnel) | 10.66–69.0.0/16 | Réservé pour les prochains événements ; voir `VLANRegistry.md` |
| 110 / 120 / 130 | Kumulus (mgmt / runners / k8s) | 10.100.110/120/130.0/24 | |
| 247 | WAN | 142.137.247.0/24 | Livraison Internet |
| 255 | PFSYNC OPNsense | 10.255.254.252/30 | |
| 500 | k8s services inter-nœuds | 10.5.0.0/24 | |
| 1003 | k8s cedille-sandbox | 10.10.1.128/25 | |
| **1009** | **k8s shared** | **10.5.9.0/24** | Propagé jusqu'au nouveau PVE (voir 4.3) |
| 1010 | k8s cedille-production-v2 | 10.5.10.0/24 | |
| 1300 | k8s poc | 10.0.130.0/24 | |
| 2206 | Lien infrastructure ETS | — | Géré côté ÉTS ; natif sur le port HPE du nouveau PVE |

> core01 conserve également des VLANs legacy non présents dans `pve_vlans_desired`
> (20, 31, 81-82, 90-99, 105, 121-122, 205, 501, 601, 1001-1008, 2001…). Ils persistent
> parce que `update-vlans.yaml` utilise `state: merged` et que `pve_vlans_to_remove` ne
> contient que le VLAN 1000.

### 4.2 État des trunks

| Équipement | Interface | Natif | VLANs autorisés | STP (VLAN 1009) |
|---|---|---|---|---|
| core01 | `Po100` (vers top-sw1) | 1 | 1-4094 | Forwarding (1001-1010 inclus) |
| top-sw1 | `Po7` (vers core01) | 1 | 1-4094 | Forwarding |
| top-sw1 | `Po100` (vers mgmt-02) | 21 | 21,1009 | Forwarding |
| top-sw1 | `Po5` | 1 | 66-69,247,1009,2206 | Forwarding |
| mgmt-02 | `Po5` (vers top-sw1) | 21 | 21,66-69,247,1009,2206 | Forwarding |
| mgmt-02 | `Gi1/0/37` (vers mgmt-03) | 21 | 21,1009 | Forwarding |
| mgmt-03 | `Gi0/48` (vers mgmt-02) | 21 | 21,1009 | Root FWD |
| mgmt-03 | `Gi0/26` (vers nouveau PVE) | 21 | 21,1009 | Desg FWD |

> Sur les liens mgmt, le VLAN 21 reste **natif/non tagué** : la connectivité de
> management ne dépend pas des VLANs tagués ajoutés. Les uplinks NX-OS ↔ NX-OS ont un
> natif VLAN 1 (cohérent des deux côtés).

### 4.3 Nouveau Proxmox (hors cluster de production)

`10.194.24.101`, hostname `pve01` (à ne pas confondre avec `pve01.mgmt.etsmtl.club`
= 10.0.21.51). Debian 13, deux NICs :

| Interface | Lien | Configuration |
|---|---|---|
| `nic0` | HPE Aruba `NServSw1-D2-1-SwSvrClub` port `2/1/8` | `vmbr0`, `10.194.24.101/24`, gateway `.1` — port HPE en **access VLAN 2206** (`ENS-FE-CLUBS`) |
| `nic1` | mgmt-03 `Gi0/26` | `vmbr1` (bridge **vlan-aware**) + `vmbr1.1009` — trunk natif 21, VLAN **1009 tagué** |

Chemin validé de bout en bout pour le VLAN 1009 :

```
PVE nic1 → mgmt-03 Gi0/26 → mgmt-02 Gi1/0/37 → top-sw1 Po100 → core01 Po100
```

L'apprentissage de la MAC `d85e.d38e.9ea8` en VLAN 1009 a été confirmé sur mgmt-03,
mgmt-02, top-sw1 (`Po100`) et core01 (`Po100`). Les VMs du cluster `k8s-shared` se
brancheront sur `vmbr1` avec le tag 1009.

---

## 5. LLDP / CDP

- **LLDP** : `feature lldp` sur les deux Nexus, `lldp run` + `lldp transmit/receive` sur
  les deux IOS. Actif et voisins visibles sur les 4 switches.
- **CDP** : actif sur les 4 (RSTP/PVST+ selon les plateformes ; mgmt-03 est en STP legacy
  802.1D et nécessite `vtp mode transparent` pour les VLAN > 1005).
- Voisins marquants : `top-sw1` ↔ `core01` et `mgmt-02` ; `mgmt-02` ↔ `mgmt-03` ;
  `core01` ↔ `daswitch.eclipse.ca` et `sw001…pnp01…` ; `mgmt-03` ↔ `RT-AC68U`.
- Côté serveurs, `lldpd` est actif sur le nouveau Proxmox (`lldpctl`) et a permis
  d'identifier les deux voisins physiques ci-dessus.

---

## 6. Accès SSH (état opérationnel)

| Équipement | User | Clé | Privilege |
|---|---|---|---|
| core01 (`.11`) | `admin` | `id_ed25519` (déjà dans `username admin sshkey ssh-ed25519 …`) | network-admin |
| top-sw1 (`.12`) | `admin` | `id_ed25519` | 15 |
| mgmt-02 (`.13`) | `lanets` | `id_rsa_switch` (RSA 4096) | 15 |
| mgmt-03 (`.15`) | `lanets` | `id_rsa_switch` | 15 |

Les switches IOS n'acceptant que des clés utilisateur **RSA**, une clé dédiée
`~/.ssh/id_rsa_switch` est utilisée pour `.13`/`.15` (avec `PubkeyAcceptedAlgorithms +ssh-rsa`
côté client). Les algorithmes dégradés nécessaires à chaque plateforme sont documentés
dans `~/.ssh/config` (KEX `group14-sha1`/`group1-sha1`, `ssh-rsa`, HMAC-SHA1, AES-CBC).

---

## 7. Points d'attention / lacunes connues

1. **`.21` et `.22` ne répondent pas** (ARP `INCOMPLETE`, tout port `filtered`) — l'entrée
   `management.prod.lanets.ca` de l'inventaire `ios` est donc inexploitable actuellement.
2. **mgmt-02 / mgmt-03 absents de l'inventaire** : à ajouter si leur config doit être gérée
   par Ansible.
3. **top-sw1 porte un banner « config managed by Ansible, never edit by hand »** : tout
   changement fait en CLI doit être reporté dans la source Ansible, sinon il sera écrasé.
4. **3560X (mgmt-03)** : VLAN > 1005 impossible en VTP server/client → `vtp mode transparent`
   requis ; et `switchport trunk encapsulation dot1q` requis avant `switchport mode trunk`.
5. **Collision de hostname** : le nouveau Proxmox et le PVE de production `.51` s'appellent
   tous deux `pve01`. Préférer les FQDN/IP dans l'inventaire et les sorties LLDP.
6. Le `ping 10.0.21.11` depuis mgmt-02 échoue (aucun default gateway sur ces switches de
   management) — comportement préexistant, sans lien avec le VLAN 1009.
