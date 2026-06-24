# OPNsense événementiel — `OPNsense.lanets.ca` (172.16.10.2)

> Document de référence — topologie, audit d'usage et trafic 30 jours, basé sur
> une inspection SSH en lecture seule (`/conf/config.xml`, `pfctl`, RRD, `netstat`,
> `arp`) le 2026-06-23.
>
> ⚠️ Distinct de `opnsense.internal.etsmtl.club` (10.0.21.1, routeur interne club)
> et du cluster CARP `opnsense01/02.event.lanets.ca` (10.120.0.2/3, événement CTF).
> Cette instance est le **routeur général d'infrastructure de LAN Events** — elle
> gère les réseaux de staging, prod, jeux et VPN opérateur.

---

## Système

| Élément          | Valeur                                                       |
| ---------------- | ------------------------------------------------------------ |
| Version          | OPNsense 25.1.12, FreeBSD 14.2-RELEASE-p4, amd64            |
| Uptime           | 224 jours au moment de l'audit                               |
| CPU              | KVM/virtio (vtnet*) — VM Proxmox                             |
| Hostname/domaine | `OPNsense` / `lanets.ca`                                     |
| IP management    | `172.16.10.2/24` (interface `lan`)                           |
| IP WAN           | `142.137.247.106/24` (même /24 que les deux autres OPNsense) |
| HA/CARP          | **Aucun** — single-node                                      |

---

## Architecture réseau — NICs physiques séparées

**Pas de VLAN 802.1Q** sur cette instance : chaque réseau dispose d'une interface
virtio dédiée (`vtnet0`–`vtnet14`), sans trunk taggé. Cela signifie que cette
instance ne contribue **pas** aux tags VLAN du registre [`VLANRegistry.md`](VLANRegistry.md).

## Interfaces — table de référence

| If OPNsense | vtnet | Descr (config)       | IP/CIDR              | Trafic 30j (B/s moy)  | Statut    |
| ----------- | ------ | -------------------- | -------------------- | --------------------- | --------- |
| lan         | vtnet0 | Management           | 172.16.10.2/24       | in=857 / out=4170     | 🟢 Actif  |
| wan         | vtnet1 | WANLanETS            | 142.137.247.106/24   | in=82k / out=4.9k     | 🟢 Actif  |
| opt1        | vtnet2 | Wireguard            | 172.16.80.1/24       | no data (désactivée)  | ⚫ Désactivée |
| opt2        | vtnet3 | AXS_D2020            | 192.168.0.2/24       | in=1.8k / out=50k     | 🟢 Actif  |
| opt3        | vtnet4 | InfraLegacy          | 172.16.45.2/24       | in=11 / out=1.4k      | 🟢 Actif (faible) |
| opt4        | vtnet5 | InfraJennifer        | 192.168.20.5/30      | in=0 / out=0          | ⚪ Mort   |
| opt5        | vtnet6 | GameServers          | 172.16.116.2/24      | in=0 / out=0          | ⚪ Mort   |
| opt6        | ovpns1 | OpenVPN_Sysadmin     | 172.16.90.0/24       | in=428 / out=774      | 🟢 Actif  |
| opt7        | ovpns2 | OpenVPN_Exec         | 172.16.91.0/24       | in=1 / out=0          | 🟡 Quasi-mort |
| opt8        | ovpns3 | OpenVPN_Players      | 172.16.92.0/24       | in=0 / out=0          | ⚪ Mort   |
| opt9        | vtnet7 | Staging              | 172.16.55.2/24       | in=526 / out=24.6k    | 🟢 Actif  |
| opt10       | vtnet8 | EventStaging         | 172.16.200.1/24      | in=0 / out=0          | ⚪ Mort   |
| opt11       | vtnet9 | EventInfra           | 172.20.4.4/29        | in=9 / out=0          | 🟡 Réception seule — voir note |
| opt12       | vtnet10 | StagingPeeringVlan500 | 10.1.1.1/30         | in=169 / out=0        | 🟡 Réception seule (NTP?) |
| opt13       | vtnet11 | StagingPeeringVlan501 | 10.1.2.1/30         | in=0 / out=0          | ⚪ Mort   |
| opt14       | vtnet12 | ModernProd           | 172.16.46.2/24       | in=1.9k / out=1.1k    | 🟢 Actif  |
| opt15       | vtnet13 | LABO                 | 10.244.12.1/22       | in=0 / out=0          | ⚪ Mort   |
| opt16       | em0     | CertStorage          | 172.16.47.2/24       | no data RRD           | ❓ Inconnu |
| opt17       | wg0     | WireguardVPN         | 10.8.0.0/24          | in=0 / out=0          | ⚪ Mort   |
| —           | vtnet14 | *(non assigné)*      | —                    | —                     | 🔵 NIC connecté, non configuré |

> **Note EventInfra (opt11/vtnet9)** : interface UP, 172.20.4.4/29, mais 0 sortant
> côté OPNsense depuis 30 jours. Le trafic entrant (9 B/s en moyenne, 24 GB cumulé
> link-level) est du bruit émis par le réseau événement côté opposé — pf bloque tout
> (`block drop in log on ! vtnet9 inet from 172.20.4.0/29`). Les routes statiques
> vers `172.20.5.11` et `172.20.5.12` (gateway "Evenement") sont **désactivées** dans
> config.xml — ce lien de peering avec le cluster CARP événement existe mais est
> inactif.

---

## Interfaces actives — détail ARP

| Interface | Hôtes actifs dans la table ARP (au moment de l'audit) |
| --------- | ------------------------------------------------------ |
| vtnet0 (Management) | ~15 hôtes (172.16.10.9–252, MACs Proxmox/physiques) |
| vtnet1 (WAN) | 142.137.247.1 (gateway), .78, .101, .106, .108, .121, .206–208 |
| vtnet3 (AXS_D2020) | 192.168.0.35, .197, .28 (+ lease database) |
| vtnet4 (InfraLegacy) | 172.16.45.115 |

---

## DHCP

| Interface | Scope DHCP           | Baux actifs au moment de l'audit |
| --------- | -------------------- | -------------------------------- |
| lan (vtnet0) | 172.16.10.200–.240 | Quelques hôtes (ARP visibles) |
| opt2 (vtnet3) | 192.168.0.10–.200 | Historique de baux `free` (anciens) — ARP montre 3 hôtes actifs |

---

## VPN

### OpenVPN — 3 instances

| Instance | Interface | Tunnel | Trafic 30j | État |
| -------- | --------- | ------ | ---------- | ---- |
| Sysadmin | ovpns1 | 172.16.90.0/24 | in=428 / out=774 B/s | 🟢 Actif |
| Exec | ovpns2 | 172.16.91.0/24 | in=1 / out=0 B/s | 🟡 Quasi-mort |
| Players | ovpns3 | 172.16.92.0/24 | in=0 / out=0 B/s | ⚪ Mort |

Config stockée dans `/var/etc/openvpn/instance-*.conf` (format OPNsense 25.x,
pas dans la section `<openvpn>` du XML legacy — section vide en conséquence).

### WireGuard

- Instance `opt1` (vtnet2, 172.16.80.0/24) : **désactivée** dans OPNsense (flag
  `<enable>` absent), NIC vtnet2 down — aucun trafic, aucune donnée RRD.
- Instance `opt17` (wg0, 10.8.0.0/24) : UP mais 0 trafic sur 30 jours. 2 peers
  WireGuard configurés (IPs 10.8.0.2, 10.8.0.3 dans la routing table) mais aucune
  activité.

---

## Routage et NAT

- **Défaut** : `default via 142.137.247.1` (gateway WAN ETS)
- **NAT outbound** : 2 règles (hybride)
- **Routes statiques désactivées** :
  - `10.162.54.54/32` via WANLanETS_GWv4 — "SSH - ETS Network Team" (désactivée)
  - `172.20.5.11/32` et `172.20.5.12/32` via "Evenement" — "EventSSH" (désactivées)

---

## Interfaces mortes — candidates au nettoyage

| Interface | Descr | IP | Justification |
| --------- | ----- | -- | ------------- |
| opt1/vtnet2 | Wireguard | 172.16.80.0/24 | Désactivée dans OPNsense, 0 trafic, NIC down |
| opt4/vtnet5 | InfraJennifer | 192.168.20.4/30 | 0 trafic 30j, 42 B sortant (ARP unique) |
| opt5/vtnet6 | GameServers | 172.16.116.0/24 | 0 trafic 30j |
| opt8/ovpns3 | OpenVPN_Players | 172.16.92.0/24 | 0 trafic 30j |
| opt10/vtnet8 | EventStaging | 172.16.200.0/24 | 0 trafic 30j |
| opt13/vtnet11 | StagingPeeringVlan501 | 10.1.2.0/30 | 0 trafic 30j |
| opt15/vtnet13 | LABO | 10.244.12.0/22 | 0 trafic 30j |
| opt17/wg0 | WireguardVPN | 10.8.0.0/24 | 0 trafic 30j |

> ⚠️ Ces interfaces ont des règles pare-feu encore actives (`pfctl -sr`). Toute
> désactivation devrait suivre le même processus que pour `opnsense.internal` :
> désassignation dans config.xml + retrait des règles pf + application en live.
> **Ne pas agir sans confirmation explicite** — certaines pourraient être dormantes
> (GameServers, Players) mais réactivées lors des événements.

---

## Points notables

- **vtnet14** : NIC connectée (10Gbase-T, `status: active`) mais non assignée à
  aucune interface OPNsense et aucune IP. Peut être une spare ou un lien futur.
- **opt12/StagingPeeringVlan500** (10.1.1.1/30) : 169 B/s entrant, 0 sortant —
  probable trafic NTP entrant depuis le réseau peering (OPNsense écoute NTP sur toutes
  ses interfaces), pas un hôte réel actif.
- **opt16/em0/CertStorage** (172.16.47.2/24) : `em0` est un driver différent de `vtnet*`
  — pourrait être un NIC physique distinct ou un contrôleur legacy dans la VM. Pas de
  données RRD disponibles ; statut réel inconnu.
- **opt7/OpenVPN_Exec** (ovpns2, 1 B/s in) : keepalive TLS ou sonde de monitoring —
  fonctionnellement dormant mais pas mort au sens strict.

---

## Relation avec les zones grises de `VLANRegistry.md`

Cette instance **ne gère aucun des VLANs taggés** du registre (30, 601, 2206, natif).
Elle est sur un plan d'adressage entièrement distinct (172.16.x.x / 192.168.x.x).
Les tags 30 et 601 du cluster Proxmox restent sans gateway identifiée après cet audit.
