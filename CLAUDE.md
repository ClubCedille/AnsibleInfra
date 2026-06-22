# CTF DHCP Track — Project Context

## Project Overview

This is the Ansible implementation for a **DHCP-themed CTF challenge track** for the SummerCamp CTF event. The track teaches participants to explore lesser-known DHCP options by hiding flags in various parts of the DHCP exchange.

The infrastructure is deployed on a **dedicated event network** (no pre-existing config to preserve). The DHCP server must distribute functional IPs while embedding CTF flags in non-critical options.

---

## Network Topology

| Element              | Value                                                           |
| -------------------- | --------------------------------------------------------------- |
| Network              | `10.110.0.0/16`                                                 |
| Gateway              | `10.110.0.1`                                                    |
| DNS server           | `10.130.0.21-22` (BIND9, redundant, sur VLAN 68)               |
| DHCP/Kea server      | `10.110.0.31-32` (dhcp01.camp / dhcp02.camp, hot-standby)      |
| TFTP server          | **co-localisé sur les VMs DHCP** (`10.110.0.31-32`)            |
| HTTP portal          | `10.110.0.51` (nginx)                                           |
| DHCP pool            | `10.110.1.10 – 10.110.5.255`                                    |
| Event domain         | `.ctf and .camp` (.camp for the infra, .ctf for the challenges) |

> **TFTP co-localisé** : le rôle `tftp` est déployé sur les VMs DHCP via `playbooks/sc/dhcp.yaml` (rôles `cedille.netservices.dhcp` + `tftp`). Les options 66/67 et `next-server` pointent vers `{{ ansible_host }}` (IP du serveur DHCP lui-même). Le groupe `netservices_tftp` (`.41-42`) existe encore dans l'inventaire SC mais n'est pas utilisé pour le challenge DHCP.

---

## Stack

- **OS**: Ubuntu (VM, provisioned by existing Ansible roles)
- **DHCP**: Kea DHCP4 + kea-ctrl-agent
- **DNS**: BIND9 (authoritative + recursive for participants)
- **TFTP**: tftpd-hpa or atftpd
- **HTTP**: nginx (captive portal page)
- **PXE**: iPXE or PXELINUX chain

Existing roles already handle: VM creation, Kea install/deploy, BIND9 install/deploy.
You can look for them in ./.cache/roles (cedille.proxmox.vm, cedille.netservices.dhcp/dns)

Rôles locaux existants : `roles/tftp/` (tftpd-hpa + iPXE + PXE files), `roles/http-portal/` (nginx + page portail).
Manquant : logique de construction de l'image PXE (flag #7).

---

## Ansible Repository Structure

```txt
roles/
├── tftp/                          # tftpd-hpa + iPXE; files/: bzImage, initrd, netboot.ipxe
├── http-portal/                   # nginx + page portail (flag #5 en commentaire HTML)
├── secret-portal/                 # nginx + page narrative (secret.ctf)
├── docker-state-exporter/         # Prometheus textfile exporter for Docker Compose challenges
├── monitoring-dashboard/          # Grafana dashboards summercamp
└── kea/vars/flags.yml             # Toutes les valeurs de flags CTF (source de vérité unique)
playbooks/sc/
├── dhcp.yaml                      # VMs DHCP (Kea + TFTP co-localisé)
├── dns.yaml                       # VMs DNS (BIND9 + zones camp/ctf)
├── http-portal.yaml               # VM portail captif
├── secret_portal.yaml             # VM secret.ctf
├── chall.yaml                     # Challenges par équipe (Docker Compose sur VM)
├── single_instance_chall.yaml     # Challenges à instance unique
├── monitoring.yaml                # Stack Prometheus/Grafana/Loki
└── includes/                      # Fragments réutilisables (apt_proxy, pip_proxy)
scripts/
└── encode_tlv.py                  # Encodes a flag string to TLV hex for option 43
```

### Key conventions

- **All flags live in `roles/kea/vars/flags.yml`** — never hardcode flag values in templates
- Flags are injected into templates via Jinja2 variables
- Run `kea-dhcp4 -t /etc/kea/kea-dhcp4.conf` to validate before restart (add as Ansible task)
- Kea supports C-style `//` comments in its JSON config natively

---

## Challenge Map

| #   | DHCP Option                             | Method                                                      | Difficulty  |
| --- | --------------------------------------- | ----------------------------------------------------------- | ----------- |
| 1   | Option 15 — domain-name                 | Read DHCP OFFER directly                                    | Easy        |
| 2   | Option 119 — domain search list         | Decode DNS-compressed wire format (RFC 1035)                | Medium      |
| 3   | Option 43 — vendor-specific (TLV)       | Parse TLV sub-options (type+length+value hex)               | Medium      |
| 5   | Option 114 — captive portal URI         | Follow URL to nginx page, find flag in HTML                 | Easy-Medium |
| 6   | Option 43 — summercamp class            | Forge DISCOVER avec `vendor-class-identifier = "summercamp"` | Hard        |
| 7   | Option 66/67 — PXE boot                 | Booter l'image PXE, flag visible dans le wallpaper          | Hard        |
| 9   | DNS TXT record                          | Follow domain from DHCP option, `dig TXT`                   | Medium      |

### Flag hiding locations in detail

**Flag #1 — Option 15**
Embedded directly in the domain name string. Visible in any packet capture.

```
flag_01_domain: "DCI{xxx}.ctf"
```

**Flag #2 — Option 119**
Kea encodes the domain search list in DNS-compressed wire format (RFC 1035) automatically when `csv-format: true`.
Participant must decode the wire format to read the flag.

```
flag_02_domain_search: "DCI{xxx}.ctf,search.ctf"
```

**Flag #3 — Option 43**
Raw TLV hex. Format: `type(1B) + length(1B) + value(ASCII) + 0xFF`.
Generate with `scripts/encode_tlv.py`:

```bash
python3 scripts/encode_tlv.py "DCI{xxx}"
# paste output into flag_03_tlv_hex in flags.yml
```

**Flag #5 — Option 114 (captive portal)**
Points to `http://portal.ctf/index.html`. Flag is hidden in the nginx-served HTML
(HTML comment, HTTP response header, or body text). Configured in `roles/http-portal`.

**Flag #6 — `summercamp` class (active)**
Kea returns a different option 43 payload only when the DISCOVER contains
`vendor-class-identifier = "summercamp"` (option 60). Participant must forge the request:

```bash
# dhclient approach
dhclient -v -cf <(echo 'send vendor-class-identifier "summercamp";') eth0

# or scapy
```

**Flag #7 — PXE boot (challenges #7 et #8 fusionnés)**
Options 66 (`tftp-server-name`) et 67 (`boot-file-name`) pointent vers le serveur TFTP co-localisé.
La chaîne iPXE charge `bzImage` + `initrd` depuis TFTP. Le flag est visible dans le **wallpaper** de l'image bootée.
Valeur dans `flags.yml` : `flag_07_pxe_wallpaper`. L'image doit être construite pour y intégrer ce flag.

**Flag #9 — DNS TXT record**
A subdomain referenced in an earlier DHCP option (e.g. option 15 or 119) has a
TXT record with the flag. Configured in the BIND9 zone file:

```
secret.ctf.  IN  TXT  "DCI{xxx}"
```

---

## Kea Config Notes

- `option-def` required for non-standard options before use in `option-data`:
  - Option 114 (`v4-captive-portal`, type `string`)
  - Option 119 (`domain-search`, type `fqdn`, array)
- Option 43 uses `"csv-format": false` with raw hex value
- `next-server` (siaddr) est défini au niveau subnet et pointe vers `{{ ansible_host }}`
- HA : mode `hot-standby`, rôles `primary` / `standby` (plus `secondary`)
- Client classes définies dans `group_vars/netservices_dhcp.yaml` :
  - `summercamp` : `option[60].text == 'summercamp'` → option 43 flag #6
- Options 66+67 (`tftp-server-name`/`boot-file-name: netboot.ipxe`) et `next-server` définis au niveau subnet — couvrent tous les clients BIOS sans client class dédiée

---

## BIND9 Notes

- Authoritative for `.ctf` and `.camp`
- A records needed: `portal.ctf`, `secret.ctf`, server IPs
- TXT record on `secret.ctf` = flag #9
- Acts as recursive resolver for participants (option 6 points here)
- Forwarders configured for external resolution if needed

---

## Status

**Implémenté :**
- `roles/tftp/` — tftpd-hpa + iPXE (undionly.kpxe, ipxe.efi, netboot.ipxe, bzImage, initrd)
- `roles/http-portal/` — nginx + page portail (flag #5)
- `scripts/encode_tlv.py` — génération hex TLV option 43
- Flags #1–#3, #5–#7, #9 définis dans `roles/kea/vars/flags.yml`
- BIND9 zone files `playbooks/sc/templates/ctf.zone.j2` et `camp.zone.j2`

**Non implémenté / hors scope Ansible :**
- Construction de l'image PXE (flag #7) — intégrer `flag_07_pxe_wallpaper` dans le wallpaper de `bzImage`/`initrd` (à faire hors repo)
- DHCP snooping sur les switches (Cisco gear, hors scope Ansible)

---

## Out of Scope / Warnings

- **Option 252 (WPAD)**: do NOT use — Windows auto-proxy will break participant connectivity
- **Options 3/6**: must remain functional (gateway + DNS) — no flags here
- **Rogue DHCP protection**: handled at switch level (DHCP snooping), not in this repo
