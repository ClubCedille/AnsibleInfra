# AnsibleInfra

Gestion de l'infrastructure physique de Cedille via Ansible

## Layout

```
.
├─ inventories/
│   ├─ infra
│   ├─ event
│   └─ summercamp
├─ playbooks/
│   ├─ cisco-config/   ← config switches (Day-1, SNMP)
│   ├─ cisco-pnp/      ← serveur Zero Touch Provisioning
│   ├─ cs2_server/     ← serveur CS2 (LanETS)
│   ├─ infra/          ← OPNsense CARP (config, diff, interface-provision, règles k8s-poc, telegraf)
│   ├─ monitoring/     ← Prometheus/Grafana/Loki (infra-* = infra permanente, sans préfixe = event SC)
│   ├─ network/        ← réseau transverse : VLANs PVE+NX-OS, DHCP Kea, DNS BIND9, Stork
│   ├─ omni/           ← Omni (gestionnaire Talos k8s) + cycle de vie cluster k8s-poc
│   ├─ proxmox/        ← images cloud, audit réseau PVE
│   └─ sc/             ← infra événementielle SummerCamp (DHCP CTF, challenges, portails…)
│
├─ scripts/
│   ├─ expand_switch_selection.py
│   └─ gen_inventory.py  ← génération de l'inventaire summercamp depuis le CSV
├─ data/
│   └─ raw/
│      ├─ lanets-inventaire-switch.csv
│      └─ passwords.csv  ← mots de passe et tokens par équipe (non versionné)
├─ collections/
│   └─ requirements.yml
├─ ansible.cfg
├─ Makefile
└─ requirements.txt
```

## Utilisation rapide

Lister les playbooks disponibles:

```bash
make list-playbooks
```

Exécuter un playbook (inventaire infra par défaut):

```bash
make network/update-vlans
```

Exécuter un playbook avec un inventaire spécifique:

```bash
make cisco-pnp/deployment inventory_name=event
```

Valider la qualité YAML/Ansible localement:

```bash
make lint
```

## Installation

Documentation faite en fonction d'une distribution Debian-based:

Installer make, python, pip, virtualenv

```bash
sudo apt update
sudo apt install python3 python3-pip make
pip3 install virtualenv
```

Éditer le PATH pour incorporer le path des exécutable python

```bash
echo -e "export PATH=\$PATH:/home/$USER/.local/bin" >> ~/.bashrc
source ~/.bashrc
```

Exécuter le playbook pour générer l'environnement

```bash
# Depuis le répertoire cloné du projet
make venv
```

Installer les collections et rôles Ansible:

```bash
make galaxy-install
```

Optionnel: installer les packages ansible et ansible-lint localement pour que l'autocomplétion fonctionne dans le terminal ainsi que le serveur de langage dans VSCode et/ou autres éditeurs de textes

```bash
pip3 install ansible
pip3 install ansible-lint
```

## CI

Le workflow GitHub Actions `Lint` exécute `make lint` sur chaque Pull Request,
sur `main` et via déclenchement manuel.

---

## Documentation thématique

| Sujet | Document |
|---|---|
| SummerCamp CTF — inventaire, challenges, déploiement | [docs/summercamp.md](docs/summercamp.md) |
| Cisco PnP — génération de snippets de configuration | [docs/cisco-pnp.md](docs/cisco-pnp.md) |
| Registre des VLANs | [docs/VLANRegistry.md](docs/VLANRegistry.md) |
| Audit complet des VMs Proxmox | [docs/VMInventoryAudit.md](docs/VMInventoryAudit.md) |
| OPNsense événementiel (lanets.ca) | [docs/OpnsenseLanetsCA.md](docs/OpnsenseLanetsCA.md) |
| OPNsense prod CARP (etsmtl.club) — topologie, audit, gestion Ansible | [docs/OpnsenseInternalETSMTL.md](docs/OpnsenseInternalETSMTL.md) |
| OPNsense prod CARP — analyse des règles et état post-migration Ansible | [docs/opnsense-rules-analysis.md](docs/opnsense-rules-analysis.md) |
| Cisco WLC — notes de troubleshooting | [docs/CiscoWLC.md](docs/CiscoWLC.md) |
| Monitoring — design phase 1 | [docs/MONITORING_PHASE1_DESIGN.md](docs/MONITORING_PHASE1_DESIGN.md) |
