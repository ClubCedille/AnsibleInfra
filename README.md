# AnsibleInfra

Gestion de l'infrastructure physique de Cedille via Ansible

## Séparation rôles / exécution

Ce repository ne contient **aucun rôle Ansible local**. Tous les rôles
réutilisables (Proxmox, OPNsense, DHCP/DNS/TFTP, monitoring, Docker, Forgejo,
Omni, Cisco 3850, CS2, pkgcache…) vivent dans
[AnsibleRoles](https://github.com/ClubCedille/AnsibleRoles) et sont consommés
ici via `collections/requirements.yml` (résolu par `make galaxy-install`, qui
clone AnsibleRoles dans `.cache/AnsibleRoles/` et matérialise chaque rôle sous
`.cache/roles/cedille.<collection>.<role>` — voir `ansible.cfg` / `roles_path`).

AnsibleInfra ne garde localement que ce qui est intrinsèquement lié à un
contexte d'exécution précis et ne se prête pas à la réutilisation : les
templates de manifest du cluster k8s-poc (`playbooks/omni/templates/`), les
dashboards Grafana JSON de cette infra (`playbooks/monitoring/files/dashboards/`,
copiés via des tasks inline plutôt qu'un faux rôle), et les secrets/flags de
l'événement SummerCamp (`playbooks/sc/vars/flags.yml`).

## Layout

```
.
├─ inventories/
│   ├─ infra          ← infra permanente du club
│   ├─ lanets          ← LAN party ETS (hosts *.lanets.ca)
│   └─ summercamp      ← SummerCamp CTF (archivé entre deux éditions)
├─ playbooks/
│   ├─ cisco-config/   ← config switches physiques (Day-1, SNMP) — infra permanente
│   ├─ cisco-pnp/      ← serveur Zero Touch Provisioning — infra permanente
│   ├─ dci/            ← VMs de pratique pour le club DCI
│   ├─ events/         ← playbooks événementiels (VLANs 66-69 : déployer un événement
│   │   │                 implique de détruire l'infra de l'autre). vlan66/67-dhcp.yaml
│   │   │                 restent ici (pas dans lanets/) : VMs taguées LANETS mais dont
│   │   │                 l'inventaire vit dans infra/ (agrégats ubuntu_vms/virtual_machines)
│   │   └─ lanets/     ← spécifique Lan ETS (serveur CS2)
│   ├─ includes/       ← fragments de tasks réutilisables entre playbooks (pip_proxy, grafana-dashboards…) — pas des playbooks autonomes
│   ├─ infra/          ← OPNsense CARP (config, diff, interface-provision, règles k8s-poc) — infra permanente
│   ├─ monitoring/     ← Prometheus/Grafana/Loki — infra-* = infra permanente, sans préfixe = event SC
│   │   └─ files/dashboards/  ← dashboards Grafana JSON statiques, spécifiques à cette infra
│   ├─ netbox/         ← synchronisation NetBox (source de vérité = inventaire Ansible) — infra permanente
│   ├─ network/        ← réseau transverse permanent : VLANs PVE+NX-OS, DHCP/DNS Kea/BIND9, Stork, runners CI
│   ├─ omni/           ← Omni (gestionnaire Talos k8s) : k8s-shared (permanent) + k8s-poc (PoC/temporaire)
│   ├─ oneoff/         ← correctifs ponctuels déjà exécutés, conservés pour trace historique — PAS à ré-exécuter en routine
│   ├─ proxmox/        ← images cloud, audit et cycle de vie des VMs — infra permanente
│   └─ sc/             ← infra événementielle SummerCamp (DHCP CTF, challenges, portails…) — archivé entre éditions
│       └─ vars/flags.yml  ← valeurs des flags CTF (source de vérité unique, non réutilisable ailleurs)
│
├─ scripts/
│   ├─ expand_switch_selection.py
│   └─ gen_inventory.py  ← génération de l'inventaire summercamp depuis le CSV
├─ data/
│   └─ raw/
│      ├─ lanets-inventaire-switch.csv
│      └─ passwords.csv  ← mots de passe et tokens par équipe (non versionné)
├─ collections/
│   └─ requirements.yml  ← collections Galaxy + rôles AnsibleRoles consommés (type: dir)
├─ ansible.cfg
├─ Makefile
└─ requirements.txt
```

## Catégories de playbooks

Les dossiers ci-dessus répondent à deux axes : **le domaine technique** (réseau,
monitoring, Proxmox…) et **le cycle de vie**. C'est ce second axe qui définit les
quatre grandes catégories :

- **Infra permanente** — tourne en continu, hors événement : `cisco-config/`,
  `cisco-pnp/`, `infra/`, `monitoring/infra-*`, `netbox/`, `network/`,
  `omni/` (sauf `k8s-poc-*`), `proxmox/`.
- **Événements** — éphémère/saisonnier, et **mutuellement exclusif** : mettre en
  place l'infra d'un événement suppose de détruire celle de l'autre (même
  segment réseau, VLANs 66-69 réutilisés d'une édition à l'autre). `events/lanets/`
  et `sc/` sont les arborescences spécifiques à chaque événement (LanETS,
  SummerCamp). `events/vlan66-dhcp.yaml`/`vlan67-dhcp.yaml` restent au niveau
  `events/` plutôt que dans `events/lanets/` : ce sont des VMs taguées LANETS,
  mais leur inventaire vit dans `infra/` (elles sont membres de
  `ubuntu_vms:children`/`virtual_machines:children`, utilisés par l'apt mirror
  et la sync NetBox) — aucun signe qu'elles aient jamais servi à SummerCamp,
  malgré le chevauchement de numéro de VLAN. `omni/k8s-poc-*` (PoC) et `dci/`
  (pratique du club étudiant DCI) sont aussi des contextes ponctuels, mais hors
  du duo LanETS/SummerCamp.
- **Ponctuel / historique** (`oneoff/`) — correctifs déjà exécutés une fois,
  conservés pour traçabilité. Ne pas les relancer en routine ; certains sont
  franchement obsolètes (ex. `sc-tftp-obsolete.yaml`, remplacé par le TFTP
  co-localisé de `sc/dhcp.yaml`).
- **Fragments** (`includes/`) — tasks réutilisables via `include_tasks`, pas
  des playbooks à exécuter directement.

> **`playbooks/sc/` est actuellement archivé** : l'infra SummerCamp est détruite
> entre deux éditions (dernier teardown : 2026-06-23). Ces playbooks ne doivent
> être exécutés qu'avec l'inventaire summercamp (`inventory_name=sc`, sélectionné
> par défaut pour toute cible `sc/*` — voir plus bas), jamais contre `infra` ou
> `lanets`.

### Détail par dossier

| Playbook                                                                          | Description                                                                          | Hôtes                                     |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------- |
| **cisco-config/**                                                                 |                                                                                      |                                           |
| `cisco-config/deployment.yaml`                                                    | Config Day-1 des switches événement (trunk VLAN, ports access, AAA)                  | `switches_event`                          |
| `cisco-config/snmp.yaml`                                                          | SNMP v2c read-only pour le scraping Prometheus (section IOS commentée, bug upstream) | `ios`, `nxos`                             |
| **cisco-pnp/**                                                                    |                                                                                      |                                           |
| `cisco-pnp/deployment.yaml`                                                       | Serveur Cisco PnP (Zero Touch Provisioning), répertoires profils/configs Day-0       | `pnp-server`                              |
| **dci/**                                                                          |                                                                                      |                                           |
| `dci/setup-pratique.yaml`                                                         | Provisionne les VMs de pratique du club étudiant DCI + Docker                        | `dci_vms`                                 |
| **events/** (VMs taguées LANETS, inventaire dans `infra/` — voir Catégories ci-dessus) |                                                                                 |                                           |
| `events/vlan66-dhcp.yaml`                                                         | DHCP Kea HA (VLAN 66), pool `10.66.1-20.0.255`                                       | `vlan66_dhcp`                             |
| `events/vlan67-dhcp.yaml`                                                         | DHCP Kea HA (VLAN 67), réplique le pool WLC Cisco "AP-MGMT" — **incomplet**, groupe `vlan67_dhcp` jamais déclaré dans `hosts.ini` | `vlan67_dhcp`                             |
| **events/lanets/** (spécifique LAN party ETS)                                     |                                                                                      |                                           |
| `events/lanets/cs2-create-vm.yaml`                                                | Crée la VM du serveur CS2 sur Proxmox                                                | connection: local → API Proxmox           |
| `events/lanets/cs2-server.yaml`                                                   | Déploie le serveur CS2 complet (prérequis + serveur)                                 | `cs2`                                     |
| `events/lanets/start-cs2-server.yaml`                                             | Démarre le serveur CS2                                                               | `cs2`                                     |
| `events/lanets/close-cs2-server.yaml`                                             | Arrête le serveur CS2 proprement                                                     | `cs2`                                     |
| `events/lanets/cs2-adding-plugin.yaml`                                            | Installe un plugin CounterStrike                                                     | `cs2`                                     |
| `events/lanets/cs2-tailscale.yaml`                                                | Installe Tailscale pour le VPN get5                                                  | `cs2`                                     |
| **includes/** (fragments, pas des playbooks autonomes)                            |                                                                                      |                                           |
| `includes/pip_proxy.yaml`                                                         | Configure le proxy pip                                                               | inclus via `include_tasks`                |
| `includes/grafana-dashboards.yaml`                                                | Copie des dashboards Grafana JSON vers le répertoire de provisioning                 | inclus via `include_tasks`                |
| **infra/** (OPNsense CARP, permanent)                                             |                                                                                      |                                           |
| `infra/opnsense-config.yaml`                                                      | Applique la config OPNsense au cluster CARP via l'API REST                           | connection: local                         |
| `infra/opnsense-diff.yaml`                                                        | Diff/validation en lecture seule (API + SSH) — menu par tags                         | connection: local                         |
| `infra/opnsense-interface-provision.yaml`                                         | Escape-hatch SSH pour l'assignation d'interfaces (API OPNsense limitée)              | `routers`                                 |
| `infra/opnsense-k8s-poc.yaml`                                                     | Règles firewall spécifiques au cluster k8s-poc (VLAN 1300)                           | `routers`                                 |
| **monitoring/** (infra-\* = permanent, sans préfixe = event SC)                   |                                                                                      |                                           |
| `monitoring/infra-core.yaml`                                                      | Stack monitoring infra permanente : Loki, Alertmanager, Prometheus, Grafana          | `monitoring_core`                         |
| `monitoring/infra-dashboards.yaml`                                                | Dashboards Grafana JSON statiques (infra Cedille)                                    | `monitoring_core`                         |
| `monitoring/infra-alloy.yaml`                                                     | Grafana Alloy (logs) sur PVE + NAS → Loki centralisé (k8s-shared)                    | `monitoring_alloy`                        |
| `monitoring/infra-node-exporters.yaml`                                            | node_exporter sur PVE + NAS                                                          | `monitoring_node_exporter`                |
| `monitoring/infra-smartctl-exporter.yaml`                                         | smartctl_exporter (S.M.A.R.T.) sur PVE + NAS                                         | `monitoring_node_exporter`                |
| `monitoring/infra-opnsense.yaml`                                                  | os-telegraf (métriques Prometheus) + syslog distant pour le cluster CARP             | `routers`                                 |
| `monitoring/infra-syslog-switches.yaml`                                           | Alloy en récepteur syslog (switches + OPNsense) sur monitoring01                     | `monitoring_core`                         |
| `monitoring/infra-pve-ceph.yaml`                                                  | Module Prometheus du Ceph MGR sur le cluster PVE                                     | `pve`                                     |
| `monitoring/core.yaml`                                                            | Stack monitoring event SC : Loki, Alertmanager, Prometheus, Grafana                  | `monitoring_core`                         |
| `monitoring/exporters.yaml`                                                       | blackbox_exporter + snmp_exporter (event SC)                                         | `monitoring_core`                         |
| `monitoring/node-exporters.yaml`                                                  | node_exporter sur les hôtes netservices (event SC)                                   | `netservices_node_exporter`               |
| `monitoring/alloy.yaml`                                                           | Grafana Alloy (logs) sur les hôtes netservices (event SC)                            | `netservices_alloy`                       |
| **netbox/** (permanent, source de vérité = inventaire Ansible)                    |                                                                                      |                                           |
| `netbox/report.yaml`                                                              | Rapport lecture-seule de l'état NetBox actuel                                        | `localhost`                               |
| `netbox/sync_vlans.yaml`                                                          | Synchronise VLANs/prefixes depuis `group_vars/pve.yaml`                              | `localhost`                               |
| `netbox/sync_vms.yaml`                                                            | Synchronise les VMs depuis le groupe `virtual_machines`                              | `localhost`                               |
| `netbox/sync_vm_interfaces.yaml`                                                  | Synchronise interfaces réseau + VLAN + IP de chaque VM                               | `localhost`                               |
| **network/** (permanent)                                                          |                                                                                      |                                           |
| `network/dhcp.yaml`                                                               | Kea DHCP4 sur `netservices_dhcp`                                                     | `netservices_dhcp`                        |
| `network/dns.yaml`                                                                | BIND9 (autoritative + récursif) sur `netservices_dns`                                | `netservices_dns`                         |
| `network/stork.yaml`                                                              | Dashboard Stork (monitoring Kea/BIND9)                                               | `netservices_stork`                       |
| `network/update-vlans.yaml`                                                       | Synchronise les VLANs sur les hôtes Proxmox ET le switch core NX-OS                  | `pve`, `nxos`                             |
| `network/sync-proxmox-pool-tags.yaml`                                             | Sync pool/tags Proxmox sans toucher au cycle de vie des VMs                          | `all`                                     |
| `network/forgejo-runners.yaml`                                                    | Provisionne + enregistre une paire de runners Forgejo Actions                        | `forgejo_runners`                         |
| `network/github-runners.yaml`                                                     | Provisionne + enregistre la flotte de runners GitHub Actions self-hosted             | `github_runners`                          |
| **omni/** (Omni/Talos k8s)                                                        |                                                                                      |                                           |
| `omni/deploy.yaml`                                                                | Provisionne la VM + déploie Omni (Docker Compose)                                    | `omni`                                    |
| `omni/k8s-shared-vms.yaml`                                                        | _(permanent)_ Provisionne les nodes du cluster k8s-shared sur Proxmox                | `k8s-shared-*`                            |
| `omni/k8s-shared-cluster.yaml`                                                    | _(permanent)_ Rattache les nouveaux nodes au cluster k8s-shared existant             | `localhost`                               |
| `omni/k8s-poc-vms.yaml`                                                           | _(PoC/temporaire)_ Provisionne les VMs k8s-poc (boot ISO Talos)                      | `k8s_poc`                                 |
| `omni/k8s-poc-dhcp.yaml`                                                          | _(PoC/temporaire)_ DHCP Kea HA pour le VLAN 1300 (k8s-poc)                           | `k8s_poc_dhcp`                            |
| `omni/k8s-poc-cluster.yaml`                                                       | _(PoC/temporaire)_ Crée les ressources Omni (Cluster + MachineSets)                  | `localhost`                               |
| `omni/k8s-poc-bootstrap.yaml`                                                     | _(PoC/temporaire)_ Bootstrap ArgoCD + k8s-base sur k8s-poc                           | `omni`                                    |
| **oneoff/** (correctifs ponctuels déjà exécutés — historique, ne pas relancer)    |                                                                                      |                                           |
| `oneoff/netbox-cleanup-2026-09-17b.yaml`                                          | Corrige les prefixes VLAN événementiels dans NetBox (2e passe du 2026-09-17)         | `localhost`                               |
| `oneoff/netbox-fixups-2026-09-17.yaml`                                            | Remédiation post-audit `netbox/report.yaml` (site "OneBigCluster" erroné)            | `localhost`                               |
| `oneoff/proxmox-vm-cleanup-2026-09-17.yaml`                                       | Nettoyage de VMs Proxmox obsolètes suite au recensement `proxmox/census_vms.yaml`    | `pve01.mgmt.etsmtl.club`                  |
| `oneoff/network-migrate-forgejo-runners-vlan40.yaml`                              | Migration ponctuelle de la flotte Forgejo runners vers le VLAN CI/CD dédié           | `forgejo_runners`                         |
| `oneoff/opnsense-nat-new-vlans-classic.yaml`                                      | Ajout de règles NAT classiques pour les VLANs nouvellement segmentés (40/45/48)      | `routers`                                 |
| `oneoff/opnsense-carp-wireguard-hook.yaml`                                        | Correctif du hook CARP/WireGuard (bug actif-actif sur le nœud backup)                | `routers`                                 |
| `oneoff/opnsense-cleanup-legacy-rules.yaml`                                       | Suppression des règles firewall legacy (doublons GUI pré-Ansible)                    | `routers`                                 |
| `oneoff/sc-fix-mtu-proxmox.yaml`                                                  | Force `mtu=1` (héritage bridge Proxmox) sur toutes les VMs SC                        | `all:!pve:!switch:!ctfd`                  |
| `oneoff/sc-tftp-obsolete.yaml`                                                    | **Obsolète** — TFTP désormais co-localisé sur les VMs DHCP via `sc/dhcp.yaml`        | `netservices_tftp`                        |
| **proxmox/** (permanent)                                                          |                                                                                      |                                           |
| `proxmox/census_vms.yaml`                                                         | Recensement lecture-seule des VMs/CT du cluster (tags VLAN inclus)                   | `pve01.mgmt.etsmtl.club`                  |
| `proxmox/gather-network.yaml`                                                     | Audit lecture-seule de la config réseau sur tous les nœuds PVE                       | `pve`                                     |
| `proxmox/pull_disk.yaml`                                                          | Télécharge les images cloud (Ubuntu, Alpine, Talos) sur tous les PVE                 | `pve`                                     |
| `proxmox/upload-talos-iso.yaml`                                                   | Télécharge l'ISO Talos (schéma Omni/SideroLink) sur tous les PVE                     | `pve`                                     |
| `proxmox/upload-talos-iso-k8s-shared.yaml`                                        | Télécharge l'ISO Talos pour k8s-shared sur les 3 PVE cibles                          | `pve01/05/08.mgmt.etsmtl.club`            |
| `proxmox/resize-vm.yaml`                                                          | Resize cores/mémoire de VMs existantes selon `host_vars`                             | `k8s_shared`                              |
| **sc/** (SummerCamp CTF — archivé entre éditions, `inventory_name=sc` par défaut) |                                                                                      |                                           |
| `sc/dhcp.yaml`                                                                    | Kea DHCP4 CTF (flags options 15/43/114/119) + TFTP co-localisé                       | `netservices_dhcp`                        |
| `sc/dns.yaml`                                                                     | BIND9 (zones `.ctf`/`.camp`)                                                         | `netservices_dns`                         |
| `sc/http-portal.yaml`                                                             | Portail captif nginx (flag #5)                                                       | `http_portal`                             |
| `sc/secret_portal.yaml`                                                           | Portail secret nginx (`secret.ctf`, page narrative)                                  | `secret_portal`                           |
| `sc/monitoring.yaml`                                                              | Stack monitoring CTF complète (Loki/Prometheus/Grafana/blackbox/snmp/node_exporter)  | `monitoring_core`, `monitoring_exporters` |
| `sc/ctfd.yaml`                                                                    | CTFd (scoreboard, challenges, équipes) via Docker Compose                            | `ctfd`                                    |
| `sc/shellctf.yaml`                                                                | VMs ShellCTF (SSH par mot de passe)                                                  | `shellctf`                                |
| `sc/deploy_shellctf_flag.yaml`                                                    | Dépose le flag ShellCTF dans `/home/sc/flag`                                         | `shellctf`                                |
| `sc/dockercache.yaml`                                                             | Cache Docker Registry (pull-through) pour les VMs de challenges                      | `dockercache`                             |
| `sc/chall.yaml`                                                                   | Déploie les challenges par-équipe (VM → Docker Compose + exporters)                  | `chall`                                   |
| `sc/single_instance_chall.yaml`                                                   | Déploie les challenges à instance unique (partagés par tout l'événement)             | `single_instance_challenges`              |
| `sc/reset_chall.yaml`                                                             | Reset d'un challenge par-équipe (`down -v` puis `up`)                                | `chall`                                   |
| `sc/update_chall.yaml`                                                            | Pull + down/up d'un challenge par-équipe                                             | `chall`                                   |
| `sc/update_single_chall.yaml`                                                     | Pull + reconcile d'un challenge single-instance (sans down/up)                       | `single_instance_challenges`              |
| `sc/update.yaml`                                                                  | `apt dist-upgrade` + `qemu-guest-agent` sur toutes les VMs SC                        | `all:!pve:!switch`                        |
| `sc/reboot.yaml`                                                                  | Hard-stop + redémarrage de toutes les VMs SC via l'API Proxmox                       | `all:!pve:!switch:!ctfd`                  |

## Utilisation rapide

Lister les playbooks disponibles:

```bash
make list-playbooks
```

Exécuter un playbook — l'inventaire par défaut est déduit automatiquement du
chemin de la cible (`sc/*` et `oneoff/sc-*` → `summercamp`, `events/lanets/*` →
`lanets`, le reste — y compris `events/vlan66-dhcp.yaml`/`vlan67-dhcp.yaml`,
dont les VMs sont déclarées dans l'inventaire infra — → `infra`) :

```bash
make network/update-vlans        # infra
make events/vlan66-dhcp          # infra (VM déclarée dans inventories/infra)
make sc/dhcp                     # summercamp, automatiquement
make events/lanets/cs2-server    # lanets, automatiquement
```

Forcer un inventaire explicitement (prioritaire sur la déduction automatique) :

```bash
make cisco-pnp/deployment inventory_name=lanets
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

| Sujet                                                                  | Document                                                             |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------- |
| SummerCamp CTF — inventaire, challenges, déploiement                   | [docs/summercamp.md](docs/summercamp.md)                             |
| Cisco PnP — génération de snippets de configuration                    | [docs/cisco-pnp.md](docs/cisco-pnp.md)                               |
| Registre des VLANs                                                     | [docs/VLANRegistry.md](docs/VLANRegistry.md)                         |
| Audit complet des VMs Proxmox                                          | [docs/VMInventoryAudit.md](docs/VMInventoryAudit.md)                 |
| OPNsense événementiel (lanets.ca)                                      | [docs/OpnsenseLanetsCA.md](docs/OpnsenseLanetsCA.md)                 |
| OPNsense prod CARP (etsmtl.club) — topologie, audit, gestion Ansible   | [docs/OpnsenseInternalETSMTL.md](docs/OpnsenseInternalETSMTL.md)     |
| OPNsense prod CARP — analyse des règles et état post-migration Ansible | [docs/opnsense-rules-analysis.md](docs/opnsense-rules-analysis.md)   |
| Cisco WLC — notes de troubleshooting                                   | [docs/CiscoWLC.md](docs/CiscoWLC.md)                                 |
| Monitoring — design phase 1                                            | [docs/MONITORING_PHASE1_DESIGN.md](docs/MONITORING_PHASE1_DESIGN.md) |
