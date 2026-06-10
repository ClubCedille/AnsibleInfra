# CTF DHCP Track — Project Context

## Project Overview

This is the Ansible implementation for a **DHCP-themed CTF challenge track** for the SummerCamp CTF event. The track teaches participants to explore lesser-known DHCP options by hiding flags in various parts of the DHCP exchange.

The infrastructure is deployed on a **dedicated event network** (no pre-existing config to preserve). The DHCP server must distribute functional IPs while embedding CTF flags in non-critical options.

---

## Network Topology

| Element         | Value                                                           |
| --------------- | --------------------------------------------------------------- |
| Network         | `10.110.0.0/16`                                                 |
| Gateway         | `10.110.0.1`                                                    |
| DNS server      | `10.130.0.21-22` (BIND9, redundant)                             |
| DHCP/Kea server | `10.110.0.31-32`                                                |
| TFTP server     | `10.110.0.41-42` (same host or separate)                        |
| HTTP portal     | `10.110.0.51` (nginx)                                           |
| DHCP pool       | `10.110.1.10 – 10.110.5.255`                                    |
| Event domain    | `.ctf and .camp` (.camp for the infra, .ctf for the challenges) |

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

Missing a role for the tftp server, http server, pxe image creation

---

## Ansible Repository Structure (to be created)

```txt
roles/
├── tftp/
│   ├── files/
│   │   └── pxe/                   # PXE files served over TFTP
│   └── tasks/
│       └── main.yml
├── http-portal/
│   ├── templates/
│   │   └── index.html.j2          # Portal page containing flag #5
│   └── tasks/
│       └── main.yml
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
| 4   | Lease timers (valid-lifetime / T1 / T2) | Spot unusual values, decode encoding scheme                 | Medium      |
| 5   | Option 114 — captive portal URI         | Follow URL to nginx page, find flag in HTML                 | Easy-Medium |
| 6   | Option 43 — CTFClient class             | Forge DISCOVER with `vendor-class-identifier = "CTFClient"` | Hard        |
| 7   | Option 66/67 — TFTP bootfile            | Fetch file from TFTP server                                 | Medium      |
| 8   | PXE bootable image                      | Boot or extract the PXE image, find flag inside             | Hard        |
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

**Flag #4 — Lease timers**
Unusual values for `valid-lifetime`, `renew-timer`, `rebind-timer` that encode something.
Choose values intentionally in `flags.yml` (`dhcp_lease_time`, `dhcp_t1_time`, `dhcp_t2_time`).

**Flag #5 — Option 114 (captive portal)**
Points to `http://portal.ctf/index.html`. Flag is hidden in the nginx-served HTML
(HTML comment, HTTP response header, or body text). Configured in `roles/http-portal`.

**Flag #6 — CTFClient class (active)**
Kea returns a different option 43 payload only when the DISCOVER contains
`vendor-class-identifier = "CTFClient"` (option 60). Participant must forge the request:

```bash
# dhclient approach
dhclient -v -cf <(echo 'send vendor-class-identifier "CTFClient";') eth0

# or scapy
```

**Flag #7 — TFTP bootfile**
Option 66 = TFTP server IP, option 67 = `image.iso`. The file on the TFTP server
contains the flag (in a text file, in metadata, or as a comment in the boot config).

**Flag #8 — PXE image**
The bootable image pointed to by option 67 contains a flag embedded in the
kernel cmdline, initrd, or filesystem. Image construction is handled separately.

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
- Client classes use Kea expression language:
  - PXEClient: `substring(option[60].hex, 0, 9) == 'PXEClient'`
  - CTFClient: `option[60].text == 'CTFClient'`
- PXEClient class sets options 66 + 67 only (other clients don't see TFTP options)

---

## BIND9 Notes

- Authoritative for `.ctf` and `.camp`
- A records needed: `portal.ctf`, `secret.ctf`, server IPs
- TXT record on `secret.ctf` = flag #9
- Acts as recursive resolver for participants (option 6 points here)
- Forwarders configured for external resolution if needed

---

## What Is NOT Yet Implemented

- [ ] `roles/tftp/` — TFTP server setup and file deployment
- [ ] `roles/http-portal/` — nginx install + portal page template
- [ ] BIND9 zone files `ctf.j2` and `camp.j2` with TXT record
- [ ] PXE image construction (flag #8) — deferred
- [ ] `scripts/encode_tlv.py` — helper to generate option 43 hex values
- [ ] Actual flag values in `flags.yml` (all placeholders currently)
- [ ] Lease time values chosen to encode flag #4
- [ ] DHCP snooping config on switches (out of Ansible scope, done on Cisco gear)

---

## Out of Scope / Warnings

- **Option 252 (WPAD)**: do NOT use — Windows auto-proxy will break participant connectivity
- **Options 3/6**: must remain functional (gateway + DNS) — no flags here
- **Rogue DHCP protection**: handled at switch level (DHCP snooping), not in this repo
