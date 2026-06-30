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

## Gestion Ansible (état au 2026-06-30)

Le cluster CARP est géré via `playbooks/infra/opnsense-config.yaml` (rôle
`cedille.opnsense.config`, collection `oxlorg.opnsense` v25.7.8+).

```bash
# Appliquer la configuration
make infra/opnsense-config VAULT_PASSWORD_FILE=~/CEDILLE/.vault

# Dry-run
make infra/opnsense-config VAULT_PASSWORD_FILE=~/CEDILLE/.vault CHECK=--check

# Vue de l'état courant (interfaces, VIPs, HA sync)
make infra/opnsense-diff VAULT_PASSWORD_FILE=~/CEDILLE/.vault
```

| Composant | État Ansible | Notes |
|-----------|-------------|-------|
| Règles firewall (18 règles nommées) | ✅ géré | Automation/Filter, séq 10–600 |
| HA sync (pfsync + XMLRPC) | ✅ géré | pfsync=opt15, syncitems vide |
| VLANs (assertion) | ✅ assertion seulement | VLANs déjà présents, API ne supporte pas la mise à jour |
| VIPs CARP | ⚠️ skippé (`opnsense_manage_vips: false`) | descriptions vides → doublons si activé |
| NAT sortant | ⚠️ skippé (`opnsense_manage_nat: false`) | NAT classique conservé, migration pendante |
| OpenVPN | ⚠️ skippé (`opnsense_openvpn: []`) | non configuré via Ansible |

Analyse complète des règles et nettoyage restant : [`docs/opnsense-rules-analysis.md`](opnsense-rules-analysis.md)

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

Méthode : compteurs `netstat -i` depuis le boot (~4h17), historique RRD sur 30 jours
(`rrdtool fetch ... -s -30d`), **et croisement avec l'inventaire complet des VMs du
cluster Proxmox** (voir [`ProxmoxVMInventory.md`](ProxmoxVMInventory.md)) — cette
dernière source est la plus fiable : un VLAN sans aucune VM assignée nulle part dans
le cluster ne peut pas avoir de trafic réel, peu importe ce que montrent les compteurs.

### Morts confirmés (0 trafic 30j **et** 0 VM dans tout le cluster Proxmox)

| VLAN               | Interface | Constat                                                                                                                                                  | Décision |
| ------------------ | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| k8s01 (1001)       | opt1      | 0 trafic 30j (1 seul échantillon non-nul sur toute la fenêtre)                                                                                           | **Supprimée de config.xml (2026-06-23)** |
| k8s02 (1002)       | opt2      | 0 trafic 30j                                                                                                                                             | **Supprimée de config.xml (2026-06-23)** |
| k8s04 (1004)       | opt4      | 0 trafic 30j, **0 VM** dans tout le cluster Proxmox sur ce tag                                                                                           | **Supprimée de config.xml (2026-06-23)** |
| k8s05 (1005)       | opt6      | Trafic résiduel observé (228.9 octets/échantillon) mais **0 VM** sur ce tag — bruit de trunk, pas un hôte réel. Reclassé "mort" suite au croisement Proxmox | **Supprimée de config.xml (2026-06-23)** |
| k8s06 (1006)       | opt7      | 0 trafic 30j, **0 VM**                                                                                                                                    | **Supprimée de config.xml (2026-06-23)** |
| k8s07 (1007)       | opt8      | 0 trafic 30j, **0 VM**                                                                                                                                    | **Supprimée de config.xml (2026-06-23)** |
| k8s08 (1008)       | opt9      | Trafic résiduel observé (779.7 octets/échantillon) mais **0 VM** sur ce tag — même cas que k8s05, reclassé "mort"                                         | **Supprimée de config.xml (2026-06-23)** |
| Lan ETS (20)       | opt12     | Toutes les VMs k3s (k3sm1-3, k3sa1-6) supprimées lors du cleanup 2026-06-23                                                                              | **Supprimée de config.xml (2026-06-23)** — tag et OS interface déjà retirés lors du cleanup précédent |
| Eclipse (65)       | opt14     | 0 trafic 30j, **0 VM**, et aucune règle pare-feu définie pour cette interface (cf. audit pf ci-dessous) — bloqué par défaut de toute façon                | **Conservé** — décision explicite de l'utilisateur (2026-06-23), malgré l'absence de trafic mesuré ; cohérent avec le commentaire "pls don't delete" déjà présent dans la config |
| Tag 1011           | *(non assigné)* | 0 trafic, **0 VM** — VLAN orphelin, jamais utilisé                                                                                                  | **Tag supprimé (2026-06-23)** |
| OpenVPN (`ovpns1`) | openvpn   | 0 trafic 30j — serveur configuré ("sysadmin") mais aucun client connecté depuis au moins un mois                                                         | À confirmer séparément (hors décision VLAN) |

**Décision (2026-06-23)** : le VLAN 65 ("Eclipse") est **conservé tel quel**. Les 8
VLANs morts (k8s01/02/04/05/06/07/08 + Lan ETS/20) + le tag orphelin 1011 ont été
**entièrement supprimés de config.xml** le 2026-06-23 : entrées d'interface retirées,
règles pare-feu supprimées, tags VLAN retirés de `<vlans>`, interfaces VLAN OS
détruites. Backup : `/conf/backup/config-pre-disabled-iface-cleanup-1782262587.xml`.
Config rechargée via `configctl filter reload` + `configctl dhcpd restart` — 11
interfaces actives, 106 règles pf, uptime continu.

Reste à faire : valider/pruner ces tags côté switch (hors périmètre OPNsense).

### Actifs confirmés

| VLAN                               | Interface | Constat                                                                                                                                                          |
| ----------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| k8s03 (1003)                       | opt3      | 4 VMs Proxmox (cluster "cedille-sandbox"), 4 baux DHCP actifs, trafic régulier                                                                                  |
| k8s09 (1009)                       | opt10     | 10 VMs Proxmox (cluster "shared"), le plus chargé — ~1.9 MB/échantillon en moyenne                                                                              |
| k8s10 (1010)                       | opt13     | 10 VMs Proxmox (cluster "cedille-production-v2"), 8 baux actifs                                                                                                 |
| services (500)                     | opt5      | 24 VMs Proxmox (clusters k8s) — NIC inter-nœuds, trafic OPNsense faible mais actif                                                                             |
| LAN (21)                           | lan       | 5 VMs Proxmox (cisco-pnp, eclipse-vm, clonezilla, forgejo-runner01-03) + trafic web/SSH admin réel                                                             |
| WireGuard "breakingglass" (opt11)  | opt11     | Usage léger mais réel (120.5 octets/échantillon, 7 peers nommés : Cydrick, aime, Louis, Max, Matai2, Max2, Julien2)                                             |

**Note** : le croisement avec l'inventaire Proxmox (voir
[`ProxmoxVMInventory.md`](ProxmoxVMInventory.md)) a corrigé deux faux-négatifs
(services/500 et Lan ETS/20, classés "ambigus" sur la seule base du trafic OPNsense) et
deux faux-positifs (k8s05/1005, k8s08/1008 — déplacés dans "Morts confirmés" ci-dessus,
leur trafic résiduel n'étant corrélé à aucune VM réelle).

### VLAN orphelin avec trafic suspect — élucidé

- **Tag 247** : aucune interface OPNsense dédiée côté `opnsense.internal` (le tag existe
  dans la liste des VLANs mais n'est assigné à aucune interface), pourtant ce tag reçoit
  du trafic entrant (61 765 paquets en ~4h côté OPNsense) **et porte 33 VMs dans le
  cluster Proxmox** — dont le NIC WAN de cette instance OPNsense elle-même et celui de
  l'autre OPNsense (`opnsense01/02.event.lanets.ca`). **Ce n'est pas un VLAN mort ni un
  mistrunk** : c'est le VLAN de livraison WAN/Internet partagé au niveau Proxmox
  (`vmbr1`), utilisé par les deux pare-feux pour leur uplink ET par une vingtaine
  d'autres VMs/services qui ont une IP publique directe sur ce même segment (jumpbox,
  uploadbox, ctfd, plusieurs workers k8s avec un 3e NIC tag 247 — voir
  [`ProxmoxVMInventory.md`](ProxmoxVMInventory.md) pour le détail complet). **Point de
  sécurité notable** : plusieurs workers k8s ont un accès WAN direct qui bypasse
  complètement le pare-feu OPNsense.

---

## Audit des règles de pare-feu

Source : section `<filter>` de `/conf/config.xml` (25 règles à l'origine, **18
depuis le nettoyage du 2026-06-23**), recoupée avec `pfctl -sr` (131 règles actives à
l'origine, **108 après nettoyage** — l'écart vient des règles auto-générées par
interface : anti-lockout, DHCP, etc., non présentes telles quelles dans `config.xml`,
et qui disparaissent aussi quand une interface est désactivée).

### ✅ Nettoyage exécuté (2026-06-23)

Les 7 règles `pass any any` orphelines correspondant aux interfaces désassignées
(`opt1, opt2, opt4, opt6, opt7, opt8, opt9` — k8s01,02,04,05,06,07,08) ont été
**retirées** de `config.xml` (par UUID, donc sans ambiguïté) et le changement a été
appliqué en live via `configctl filter reload` (mécanisme officiel "Apply changes" du
firewall). Vérifié après coup : `pfctl -sr` ne référence plus aucune de ces 7
interfaces, et le ruleset complet de chaque VLAN actif (k8s03, services, k8s09, Lan
ETS, k8s10) est resté intact. Sauvegarde prise avant modification :
`/conf/backup/config-pre-pfrule-cleanup-1782244859.xml`.

### Constat principal (historique) — absence totale de microsegmentation inter-VLAN

**Chaque interface optionnelle active (`opt3, opt5, opt10, opt12, opt13` — k8s03,
services, k8s09, Lan ETS, k8s10) porte encore une règle `pass <interface> any any`**
— source `any`, destination `any`, tout protocole. Ce constat reste valable pour les
VLANs **actifs** restants (les VLANs morts ont été traités ci-dessus) :

- N'importe quel hôte sur un de ces VLANs actifs peut atteindre n'importe quel autre
  VLAN, y compris le LAN de management (10.0.21.0/24) et le WAN.
- Il n'existe **aucune règle qui isole le cluster k8s du reste du réseau**, ni qui
  isole les VLANs entre eux.
- **Reste à faire** (hors périmètre de ce nettoyage) : remplacer ces `pass any any`
  par des règles explicites par VLAN actif.

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

| Constat                                                 | Action recommandée                                                                                                                                      | Statut |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| `pass any any` sur les VLANs k8s/services/Lan ETS encore actifs | Définir des règles explicites par VLAN (ex. k8s ne devrait parler qu'au LAN de management + entre nœuds k8s, pas au WAN directement)            | À faire |
| VLANs morts avec accès total au reste du réseau         | Retirer l'accès                                                                                                                                          | ✅ Fait le 2026-06-23 (interfaces désassignées + règles retirées pour opt1,2,4,6,7,8,9) |
| Règles dupliquées sur `opt11`/`wireguard`                | Supprimer les doublons                                                                                                                                  | À faire (hors périmètre de ce nettoyage) |
| Description "Default allow LAN to any rule" sur `opt12` | Renommer pour éviter la confusion                                                                                                                        | À faire |
| Tag VLAN 247 recevant du trafic sans interface assignée  | Élucidé — c'est le VLAN de livraison WAN partagé, pas une anomalie (voir `ProxmoxVMInventory.md`)                                                       | ✅ Élucidé, aucune action requise |

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
  Une fois l'OS installé et accessible (SSH/API), la configuration peut être poussée
  via `make infra/opnsense-config` (rôle `cedille.opnsense.config`, collection
  `oxlorg.opnsense`) — disponible dans ce repo depuis 2026-06-30.
- **VLANs à recréer** : les actifs confirmés (21, 20, 500, 1003, 1009, 1010) plus le
  VLAN 65 ("Eclipse", conservé par décision explicite). Ne pas recréer 1001, 1002,
  1004, 1005, 1006, 1007, 1008, 1011 — orphelinés (cf. décision du 2026-06-23 et
  [`VLANRegistry.md`](VLANRegistry.md)).

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
