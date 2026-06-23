# OPNsense interne du club — `opnsense.internal.etsmtl.club` (10.0.21.1)

> Document de référence — topologie, audit d'usage et audit pare-feu, basé sur une
> inspection SSH en lecture seule (`/conf/config.xml`, `pfctl`, RRD) en juin 2026.
>
> Objectif : servir de base fiable pour (1) une **duplication manuelle future** de
> cette instance (OPNsense ne se provisionne pas bien via cloud-init) et (2) son
> **adoption dans l'infra Ansible** (gestion de config via API plutôt que
> provisioning OS).
>
> ⚠️ Distinct du cluster CARP `opnsense01/02.event.lanets.ca` (10.120.0.2/10.120.0.3),
> dédié aux événements (CTF SummerCamp, Kea + BIND, voir `CLAUDE.md`). Cette instance-ci
> est le **routeur interne permanent du club**.

---

## Système

| Élément          | Valeur                                                       |
| ---------------- | ------------------------------------------------------------ |
| Version          | OPNsense 26.1.10, FreeBSD amd64                              |
| CPU              | Intel Xeon E5-2699 v4 @ 2.20GHz, 4 vCPU                      |
| RAM              | 8 GiB                                                        |
| Disque           | 23G (3.6G utilisés, 17%)                                     |
| Hypervisor       | VM virtio (`vtnet*`) — KVM/Proxmox, comme le cluster CARP    |
| HA/CARP          | **Aucun** — single-node (contrairement au cluster événement) |
| Hostname/domaine | `opnsense` / `internal.etsmtl.club`                          |

---

## Interfaces physiques

- **`vtnet0`** : trunk 802.1Q, porte tous les VLANs internes (LAN/k8s/services/VPN-bridge).
- **`vtnet1`** : WAN, IP publique `142.137.247.101/24` (config = DHCP, IP observée
  statique en pratique) — même `/24` que le cluster CARP événementiel, donc même
  brassage réseau opérateur du club.

## VLANs sur `vtnet0` — table de référence

| Tag  | Descr (config)                   | If OPNsense                     | IP/CIDR           | DHCP (isc-dhcp)      | Trafic ~4h boot    | Trafic moyen 30j (octets/échantillon)     |
| ---- | -------------------------------- | ------------------------------- | ----------------- | -------------------- | ------------------ | ----------------------------------------- |
| 21   | LAN                              | lan                             | 10.0.21.1/24      | .10–.245             | réel (admin)       | ~6 058 501 (élevé — interface management) |
| 1001 | k8s01                            | opt1                            | 10.10.0.129/25    | (scope, 0 bail)      | bruit boot only    | **0.0 — mort**                            |
| 1002 | k8s02                            | opt2                            | 10.10.1.1/25      | .2–.126              | bruit boot only    | **0.0 — mort**                            |
| 1003 | k8s03                            | opt3                            | 10.10.1.129/25    | .130–.254 (4 actifs) | réel               | 27 813.3 — **actif**                      |
| 1004 | k8s04                            | opt4                            | 10.5.4.1/24       | .2–.254              | bruit boot only    | **0.0 — mort**                            |
| 500  | services                         | opt5                            | 10.5.0.1/24       | (scope, 0 bail)      | bruit boot only    | 438.7 — faible mais non nul               |
| 1005 | k8s05                            | opt6                            | 10.10.2.129/25    | (scope, 0 bail)      | bruit boot only    | 228.9 — faible mais non nul               |
| 1006 | k8s06                            | opt7                            | 10.10.3.1/25      | (scope, 0 bail)      | bruit boot only    | **0.0 — mort**                            |
| 1007 | k8s07                            | opt8                            | 10.10.3.129/25    | (scope, 0 bail)      | bruit boot only    | **0.0 — mort**                            |
| 1008 | k8s08                            | opt9                            | 10.5.8.1/24       | .2–.254              | bruit boot only    | 779.7 — faible mais non nul               |
| 1009 | k8s09                            | opt10                           | 10.5.9.1/24       | .1–.254 (10 actifs)  | réel, le + chargé  | 1 924 051.8 — **très actif**              |
| 20   | Lan ETS                          | opt12                           | 172.16.0.1/16     | (pas de scope)       | quasi nul          | 4.9 — quasi mort (bruit ARP)              |
| 1010 | k8s10                            | opt13                           | 10.5.10.1/24      | .2–.254 (8 actifs)   | réel               | 989 956.1 — **actif**                     |
| 1011 | —                                | _(non assigné à une interface)_ | —                 | —                    | n/a                | n/a — **VLAN orphelin**                   |
| 247  | —                                | _(non assigné à une interface)_ | —                 | —                    | bruit entrant only | n/a — **VLAN orphelin, trafic suspect**   |
| 65   | "Vers Eclipse, pls don't delete" | opt14                           | 10.255.255.253/30 | (pas de scope)       | bruit boot only    | **0.0 — mort (30j)**                      |

→ Le cœur de cette infra est un **cluster Kubernetes** (k8s01–k8s10), un VLAN
**"services"** (10.5.0.0/24), un VLAN **"Lan ETS"** (172.16.0.0/16) et un lien
point-à-point étiqueté **"Eclipse"**.

---

## Audit d'usage réel — VLANs/interfaces candidats au nettoyage

Méthode : compteurs `netstat -i` depuis le boot (~4h17) **et** historique RRD sur
30 jours (`rrdtool fetch ... -s -30d`) pour éviter de qualifier un VLAN de mort à
cause d'un simple redémarrage récent d'un nœud.

### Morts confirmés (0 octet de trafic sur 30 jours)

| VLAN               | Interface | Constat                                                                                                                                                  |
| ------------------ | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| k8s01 (1001)       | opt1      | 0 trafic 30j (1 seul échantillon non-nul sur toute la fenêtre)                                                                                           |
| k8s02 (1002)       | opt2      | 0 trafic 30j                                                                                                                                             |
| k8s04 (1004)       | opt4      | 0 trafic 30j                                                                                                                                             |
| k8s06 (1006)       | opt7      | 0 trafic 30j                                                                                                                                             |
| k8s07 (1007)       | opt8      | 0 trafic 30j                                                                                                                                             |
| Eclipse (65)       | opt14     | 0 trafic 30j — **et aucune règle pare-feu définie pour cette interface** (cf. audit pf ci-dessous), donc bloqué par défaut même si le lien était utilisé |
| OpenVPN (`ovpns1`) | openvpn   | 0 trafic 30j — serveur configuré ("sysadmin") mais aucun client connecté depuis au moins un mois                                                         |

**Recommandation** : ces 6 VLANs k8s + le lien Eclipse sont de bons candidats à
retirer (désassignation d'interface OPNsense, puis suppression du tag VLAN si
confirmé inutile). Le serveur OpenVPN peut être désactivé si WireGuard
("breakingglass") couvre déjà tous les besoins d'accès admin distant — **à
confirmer avec l'utilisateur avant toute action**, certains de ces nœuds peuvent être
simplement éteints/en attente de réutilisation plutôt que définitivement abandonnés.

### Actifs confirmés

| VLAN         | Interface | Constat                                                         |
| ------------ | --------- | --------------------------------------------------------------- |
| k8s03 (1003) | opt3      | Actif, 4 baux DHCP actifs, trafic régulier                      |
| k8s09 (1009) | opt10     | Le plus chargé — 10 baux actifs, ~1.9 MB/échantillon en moyenne |
| k8s10 (1010) | opt13     | Actif — 8 baux actifs, ~990 KB/échantillon en moyenne           |
| LAN (21)     | lan       | Interface de management — trafic web/SSH admin réel             |

### Cas ambigus — faible trafic, pas clairement morts

| VLAN                              | Interface | Constat                                                                                                                                                 |
| --------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| services (500)                    | opt5      | 438.7 octets/échantillon en moyenne — non nul mais très faible (probable trafic de heartbeat/monitoring, pas de charge réelle)                          |
| k8s05 (1005)                      | opt6      | 228.9 octets/échantillon — idem, faible mais non nul                                                                                                    |
| k8s08 (1008)                      | opt9      | 779.7 octets/échantillon — idem                                                                                                                         |
| Lan ETS (20)                      | opt12     | 4.9 octets/échantillon — quasiment nul, probablement juste du bruit ARP/broadcast, pas d'hôte réellement actif dessus malgré l'absence de scope DHCP    |
| WireGuard "breakingglass" (opt11) | opt11     | 120.5 octets/échantillon — usage léger, cohérent avec un VPN d'accès admin ponctuel (7 peers nommés : Cydrick, aime, Louis, Max, Matai2, Max2, Julien2) |

**Recommandation** : ne pas retirer ces VLANs sans vérification active (demander aux
porteurs des nœuds k8s05/k8s08/services si ces machines sont censées tourner) — le
trafic est trop faible pour conclure à un abandon, mais trop faible aussi pour
justifier le maintien sans confirmation explicite.

### VLANs orphelins (tag défini mais jamais assigné à une interface)

- **Tag 1011** : aucune interface OPNsense associée, 0 trafic. Candidat direct à la
  suppression du tag si aucun usage futur n'est prévu.
- **Tag 247** : aucune interface OPNsense associée, mais reçoit du trafic entrant
  (61 765 paquets en ~4h, 0 paquet sortant) — **comportement suspect**, possible
  mistrunk/bruit d'un switch en amont. À investiguer côté switch avant de supprimer
  le tag (ne pas juste l'ignorer).

---

## Audit des règles de pare-feu

Source : section `<filter>` de `/conf/config.xml` (25 règles), recoupée avec
`pfctl -sr` (131 règles actives — l'écart vient des règles auto-générées par
interface : anti-lockout, NAT outbound implicite, etc., non présentes telles quelles
dans `config.xml`).

### Constat principal — absence totale de microsegmentation inter-VLAN

**Chaque interface optionnelle (`opt1` à `opt13`, soit tous les VLANs k8s + services +
Lan ETS + WireGuard) porte une règle `pass <interface> any any`** — source `any`,
destination `any`, tout protocole. Concrètement :

- N'importe quel hôte sur n'importe quel VLAN (y compris les VLANs **morts** comme
  k8s01/02/04/06/07) peut atteindre n'importe quel autre VLAN, y compris le LAN de
  management (10.0.21.0/24) et le WAN.
- Il n'existe **aucune règle qui isole le cluster k8s du reste du réseau**, ni qui
  isole les VLANs entre eux.
- Risque concret : si un de ces VLANs "morts" est un jour réactivé par erreur
  (reconnexion d'un câble, redémarrage d'une VM oubliée), l'hôte aura un accès complet
  à tout le réseau interne sans aucune restriction.

### Règles dupliquées

- **`opt11` (WireGuard "breakingglass")** : deux règles `pass any any` strictement
  identiques.
- **Groupe `wireguard`** : deux règles `pass any any` identiques également.

→ Aucun impact fonctionnel (redondant, pas contradictoire), mais à nettoyer pour la
lisibilité — clair signe de configuration faite à la main via la GUI sans revue.

### Description trompeuse

- `opt12` (Lan ETS, VLAN 172.16.0.0/16) porte la description **"Default allow LAN to
  any rule"** — copiée depuis le template par défaut d'OPNsense pour l'interface
  `lan`, mais appliquée ici à une interface optionnelle. Ce n'est pas un bug
  fonctionnel, mais une source de confusion lors d'un futur audit (on pourrait croire
  à tort que c'est la règle de l'interface `lan` principale).

### WAN

Règles standard et raisonnables : accès UDP au service DHCP/NTP, ICMP entrant
(ping), HTTPS/SSH limités à l'IP du firewall lui-même (`(self)`) — **aucune règle de
port-forward (NAT `rdr`) n'est définie**, donc aucun service interne n'est exposé
directement sur le WAN. Bon point de sécurité de base.

### Recommandations résumées

| Constat                                                 | Action recommandée                                                                                                                                      |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pass any any` sur tous les VLANs k8s/services/Lan ETS  | Définir des règles explicites par VLAN (ex. k8s ne devrait parler qu'au LAN de management + entre nœuds k8s, pas au WAN directement ni aux VLANs morts) |
| VLANs morts avec accès total au reste du réseau         | Retirer l'accès (ou retirer le VLAN entièrement, cf. section précédente) avant toute réactivation accidentelle                                          |
| Règles dupliquées sur `opt11`/`wireguard`               | Supprimer les doublons                                                                                                                                  |
| Description "Default allow LAN to any rule" sur `opt12` | Renommer pour éviter la confusion                                                                                                                       |
| Tag VLAN 247 recevant du trafic sans interface assignée | Investiguer côté switch avant suppression                                                                                                               |

Ces recommandations ne sont **pas appliquées** dans ce document — audit uniquement,
en attente de validation.

---

## DHCP

DHCPv4 via **`os-isc-dhcp`** (et non Kea, contrairement au cluster événementiel).
Plages par interface : voir la colonne "DHCP" du tableau VLANs ci-dessus. Aucune
réservation statique notable détectée hors scope de cet audit.

## DNS

Plugin **`os-bind`**, autoritaire pour deux zones primaires :

- `etsmtl.club`
- `cedille.club`

Les deux zones sont en serial récent (juillet 2025), TTL 86400, refresh 21600 — config
DNS standard, pas d'anomalie relevée.

## VPN

### WireGuard — instance "breaking-glass"

- Port UDP `51820`, réseau tunnel `10.254.0.0/24`.
- 7 peers nommés (admin distant individuel, pas de site-à-site) : Cydrick, aime,
  Louis, Max, Matai2, Max2, Julien2.
- Usage léger mais régulier (~120 octets/échantillon en moyenne sur 30j).
- ⚠️ Clés publiques/privées et PSK présents dans `/conf/config.xml` — **volontairement
  omis de ce document**.

### OpenVPN — instance "sysadmin"

- Serveur UDP/1194 sur `local 142.137.247.101`, réseau client `192.168.254.0/24`.
- `push route` vers `10.0.21.0/24`, `172.16.0.0/16`, `10.5.0.0/24`, `142.137.247.0/24`.
- Auth locale (base utilisateurs OPNsense), `client-to-client` + `duplicate-cn`
  autorisés.
- **0 trafic sur 30 jours** — semble inutilisé, probablement superseded par
  WireGuard. À confirmer avant désactivation.

## NAT

Mode **hybrid** : règle outbound automatique pour tout le reste + une règle manuelle
explicite pour `source=wireguard → wan` (NAT vers l'IP WAN). **Aucun port-forward
(`rdr`) défini** — pas de service interne exposé directement depuis Internet.

---

## Notes pour duplication manuelle future

Points à régénérer/recréer manuellement lors d'une nouvelle installation (pas
transférable tel quel, et volontairement non documentés en détail ici pour des
raisons de sécurité) :

- **Certificats** : CA et certificats serveur OpenVPN liés à cette instance précise
  (champ `cert` référencé dans la config OpenVPN) — à régénérer.
- **Clés WireGuard** (privée serveur + clés publiques/PSK des 7 peers) — à régénérer
  et à redistribuer aux utilisateurs concernés.
- **Mot de passe root** — l'utilisateur a indiqué qu'il le changerait après cette
  session d'audit.
- **Provisioning OS** : pas de cloud-init fiable pour OPNsense connu à ce jour →
  installation manuelle (ISO/image) reste le chemin recommandé pour la VM dupliquée.
  Une fois l'OS installé et accessible (SSH/API), la configuration (interfaces,
  VLANs, DHCP, BIND, règles pare-feu nettoyées) pourrait être poussée via une
  collection Ansible orientée API REST OPNsense (ex. `ansibleguy.opnsense`), à
  intégrer dans ce repo comme un nouveau rôle — travail non démarré, à planifier une
  fois ce document validé.
- **VLANs à recréer** : se limiter aux VLANs confirmés actifs (21, 1003, 1009, 1010,
  1009...) plutôt que de copier l'historique complet "mort" (1001,1002,1004,1006,
  1007,500,1005,1008,20,65,1011,247) — l'occasion de partir sur une base plus propre.

---

## Limites de cet audit

- Mesures de trafic en temps réel basées sur ~4h17 d'uptime au moment du relevé,
  recoupées avec 30 jours d'historique RRD — un VLAN "mort" sur ces deux fenêtres
  reste théoriquement reactivable s'il correspond à du matériel physiquement éteint
  ou en attente (pas une garantie absolue d'abandon définitif).
- Les noms de VLAN ("k8s01"–"k8s10", "services", "Lan ETS", "Eclipse") sont des
  indices tirés de la config, pas des certitudes confirmées par l'utilisateur — à
  valider avant toute action de nettoyage.
- Aucune action corrective (suppression de VLAN, modification de règle) n'a été
  effectuée — ce document est strictement un audit + des recommandations.
