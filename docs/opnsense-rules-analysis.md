# Analyse des règles firewall OPNSense — prod CARP cluster

**Date du relevé :** 2026-06-30  
**Nœuds :** opnsense01.prod.etsmtl.club (10.0.21.2) / opnsense02.prod.etsmtl.club (10.0.21.3)  
**État :** opnsense01 = opnsense02 — configuration synchronisée via XMLRPC.

---

## Contexte

Les deux routeurs OPNSense fonctionnent en cluster CARP actif/backup. Les règles ont été
créées manuellement via la GUI. L'objectif à long terme est de les gérer via Ansible
(`oxlorg.opnsense.rule` → `/api/firewall/filter/`). Cette migration est **en attente
d'une analyse plus poussée** avant toute application.

**NAT :** Conservé tel quel — hors scope Ansible pour l'instant.

---

## Nouveau format — `/api/firewall/filter/` (48 règles)

### Catégorie A — Règles système OPNSense (30 règles)

Gérées automatiquement par OPNSense. **Ne pas toucher.**

| Interface | Action | Dir | Proto | Source | Destination | Description |
|-----------|--------|-----|-------|--------|-------------|-------------|
| `*` | block | in | — | — | — | Default deny / state violation rule |
| `*` | pass | in | ipv6-icmp | — | — | IPv6 RFC4890 requirements (ICMP) |
| `*` | pass | out | ipv6-icmp | (self) | fe80::/10, ff02::/16 | IPv6 RFC4890 requirements (ICMP) |
| `*` | pass | in | ipv6-icmp | fe80::/10 | fe80::/10, ff02::/16 | IPv6 RFC4890 requirements (ICMP) |
| `*` | pass | in | ipv6-icmp | ff02::/16 | fe80::/10 | IPv6 RFC4890 requirements (ICMP) |
| `*` | pass | in | ipv6-icmp | :: | ff02::/16 | IPv6 RFC4890 requirements (ICMP) |
| `*` | block | in | tcp/udp | — | — | block all targeting port 0 (×2) |
| `*` | pass | any | carp | — | 224.0.0.18 | CARP defaults |
| `*` | pass | any | carp | — | ff02::12 | CARP defaults |
| `*` | block | in | tcp | sshlockout | (self) | sshlockout (×2) |
| `*` | block | in | — | virusprot | — | virusprot overload table |
| `WAN` | block | in | — | bogons | — | Block bogon IPv4 networks from WAN |
| `WAN` | block | in | — | bogonsv6 | — | Block bogon IPv6 networks from WAN |
| `WAN` | block | in | — | 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,… | — | Block private networks from WAN (IPv4) |
| `WAN` | block | in | — | fd00::/8,fe80::/10,::/128 | — | Block private networks from WAN (IPv6) |
| `*` | pass | out | — | — | — | let out anything from firewall host itself |
| `LAN` | pass | in | tcp | — | (self) | anti-lockout rule (×3 — GUI/HTTPS/SSH) |
| `k8s03` | pass | in | udp | — | 255.255.255.255 | allow access to DHCP server |
| `k8s03` | pass | in | udp | — | (self) | allow access to DHCP server |
| `k8s03` | pass | out | udp | (self) | — | allow access to DHCP server |
| `k8s09` | pass | in | udp | — | 255.255.255.255 | allow access to DHCP server |
| `k8s09` | pass | in | udp | — | (self) | allow access to DHCP server |
| `k8s09` | pass | out | udp | (self) | — | allow access to DHCP server |
| `k8s10` | pass | in | udp | — | 255.255.255.255 | allow access to DHCP server |
| `k8s10` | pass | in | udp | — | (self) | allow access to DHCP server |
| `k8s10` | pass | out | udp | (self) | — | allow access to DHCP server |

### Catégorie B — Règles admin sans description (17 règles)

Créées via la GUI, sans description. Ce sont les doublons en nouveau format des règles
classiques (voir section suivante). **À supprimer manuellement après migration Ansible.**

| Interface | Action | Dir | Proto | Source | Destination | Port | Identité fonctionnelle |
|-----------|--------|-----|-------|--------|-------------|------|------------------------|
| `WAN` | pass | in | tcp/udp | any | (self) | 51820 | WireGuard in |
| `WAN` | pass | in | udp | any | (self),wanip | 1194 | OpenVPN in |
| `WAN` | pass | out | udp | any | (self),wanip | 1194 | OpenVPN out |
| `WAN` | pass | in | icmp | any | (self) | — | ICMP in |
| `WAN` | pass | out | icmp | any | (self) | — | ICMP out |
| `LAN` | pass | in | — | lan net | any | — | Default allow LAN (IPv4) |
| `LAN` | pass | in | — | lan net | any | — | Default allow LAN (IPv6) |
| `OpenVPN` | pass | in | — | any | any | — | OpenVPN in |
| `OpenVPN` | pass | out | — | any | any | — | OpenVPN out |
| `WireGuard (Group)` | pass | in | — | any | any | — | WireGuard group in |
| `WireGuard (Group)` | pass | out | — | any | any | — | WireGuard group out |
| `k8s03` | pass | in | — | any | any | — | k8s03 in |
| `services` | pass | in | — | any | any | — | services in |
| `k8s09` | pass | in | — | any | any | — | k8s09 in |
| `breakingglass` | pass | in | — | any | any | — | breakingglass WG in |
| `breakingglass` | pass | out | — | any | any | — | breakingglass WG out |
| `k8s10` | pass | in | — | any | any | — | k8s10 in |

### Catégorie C — Règles admin nommées (1 règle)

| Interface | Action | Dir | Source | Description |
|-----------|--------|-----|--------|-------------|
| `CARP-sync` (opt15) | pass | in | 10.255.254.252/30 | **HASync + diag depuis subnet sync** |

---

## Format classique — `config.xml <filter>` (18 règles)

Règles créées dans l'ancienne UI (per-interface). Chacune a un équivalent exact dans la
Catégorie B/C ci-dessus — OPNSense les expose dans les deux vues simultanément.
OPNSense évalue les règles Automation (nouveau format) **avant** les règles classiques.

```
wan      pass  tcp/udp  any → (self):51820           ""  ← WireGuard in
wan      pass  udp      any → (self),wanip:1194       ""  ← OpenVPN in
wan      pass  udp      any → (self),wanip:1194       ""  ← OpenVPN out
wan      pass  icmp     any → (self)                  ""  ← ICMP in
wan      pass  icmp     any → (self)                  ""  ← ICMP out
lan      pass  any      lan → any                     "Default allow LAN to any rule"
lan      pass  any      lan → any                     "Default allow LAN IPv6 to any rule"
openvpn  pass  any      any → any                     ""  ← OpenVPN in
openvpn  pass  any      any → any                     ""  ← OpenVPN out
opt3     pass  any      any → any                     ""  ← k8s03 in
opt5     pass  any      any → any                     ""  ← services in
opt10    pass  any      any → any                     ""  ← k8s09 in
opt11    pass  any      any → any                     ""  ← breakingglass in
opt11    pass  any      any → any                     ""  ← breakingglass out
opt13    pass  any      any → any                     ""  ← k8s10 in
wireguard pass any      any → any                     ""  ← WireGuard group in
wireguard pass any      any → any                     ""  ← WireGuard group out
opt15    pass  any      10.255.254.252/30 → any       "HASync + diag depuis subnet sync"
```

---

## Ce qu'Ansible ferait si on appliquait `make infra/opnsense-config`

Le rôle utilise `match_fields: ["description"]`. Les règles sans description ne seront
**pas mises à jour** — Ansible va créer 18 nouvelles règles nommées en parallèle.

### Règles qui seraient créées (18)

| Séq | Interface | Action | Dir | Proto | Port/Source | Description Ansible |
|-----|-----------|--------|-----|-------|-------------|---------------------|
| 10 | wan | pass | in | UDP | dst:51820 | WAN \| Allow WireGuard inbound (UDP 51820) |
| 20 | wan | pass | in | UDP | dst:1194 | WAN \| Allow OpenVPN inbound (UDP 1194) |
| 30 | wan | pass | out | UDP | dst:1194 | WAN \| Allow OpenVPN outbound (UDP 1194) |
| 40 | wan | pass | in | ICMP | — | WAN \| Allow ICMP inbound |
| 50 | wan | pass | out | ICMP | — | WAN \| Allow ICMP outbound |
| 100 | lan | pass | in | any | src:lan | LAN \| Allow LAN to any (IPv4) |
| 110 | lan | pass | in | any | src:lan | LAN \| Allow LAN to any (IPv6) |
| 200 | openvpn | pass | in | any | — | OpenVPN \| Allow inbound |
| 210 | openvpn | pass | out | any | — | OpenVPN \| Allow outbound |
| 300 | opt3 | pass | in | any | — | k8s03 (opt3) \| Allow all inbound |
| 310 | opt5 | pass | in | any | — | services (opt5) \| Allow all inbound |
| 320 | opt10 | pass | in | any | — | k8s09 (opt10) \| Allow all inbound |
| 330 | opt13 | pass | in | any | — | k8s10 (opt13) \| Allow all inbound |
| 400 | opt11 | pass | in | any | — | breakingglass WG (opt11) \| Allow inbound |
| 410 | opt11 | pass | out | any | — | breakingglass WG (opt11) \| Allow outbound |
| 500 | wireguard | pass | in | any | — | WireGuard group \| Allow inbound |
| 510 | wireguard | pass | out | any | — | WireGuard group \| Allow outbound |
| 600 | opt15 | pass | in | any | src:10.255.254.252/30 | HA \| Allow sync traffic from peer (pfsync + XMLRPC) |

### État résultant (si appliqué sans nettoyage préalable)

- Catégorie A (30) : inchangées
- Catégorie B (17) : toujours présentes — **doublons fonctionnels**
- Catégorie C (1) : `HASync + diag depuis subnet sync` reste — **doublon de la règle HA Ansible (séq 600)**
- Nouvelles règles Ansible (18) : créées, nommées, séquencées

### Nettoyage post-apply

1. Supprimer les 17 règles Catégorie B (sans description) via `Firewall → Automation → Filter`
2. Supprimer l'ancienne règle HA `HASync + diag depuis subnet sync` (remplacée par séq 600)
3. Migrer ou supprimer les 18 règles classiques via `Firewall → Rules → Migration Assistant`

---

## Questions ouvertes pour l'analyse à venir

- Les règles `pass any any` sur opt3/opt5/opt10/opt13 sont très permissives — faut-il les affiner ?
- opt11 (breakingglass WireGuard) : policy identique aux autres k8s VLANs — est-ce intentionnel ?
- Faut-il des règles inter-VLAN explicites, ou le `let out anything from firewall host` suffit ?
- Les règles ICMP WAN in/out permettent le ping vers le WAN VIP — à restreindre ou conserver ?
- Stratégie de migration : appliquer Ansible + nettoyage en une fenêtre de maintenance,
  ou migrer interface par interface ?
