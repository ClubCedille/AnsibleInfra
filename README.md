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
│   ├─ cisco-pnp
│   ├─ cs2_server
│   ├─ netservices
│   ├─ proxmox
│   └─ sc/               ← playbooks summercamp (DNS, challenges, shellctf…)
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
make proxmox/update
```

Exécuter un playbook avec un inventaire spécifique:

```bash
make cisco-pnp/deployment inventory_name=event
make cisco-pnp/deployment inventory_name=sc
make cisco-pnp/deployment inventory_name=summercamp
```

Valider la qualité YAML/Ansible localement:

```bash
make lint
```

## Scripts utilitaires

### Génération de snippets PnP

`scripts/expand_switch_selection.py` génère des snippets de configuration pour les switches Cisco.

```bash
.venv/bin/python3 scripts/expand_switch_selection.py --help
```

### Génération de l'inventaire summercamp

`scripts/gen_inventory.py` régénère `inventories/summercamp/hosts.ini` à partir de `data/raw/passwords.csv` et, si `--challenge-dir` est fourni (repo de challenges externe, ex. DCISummerCamp2026), du `extra.deployment_info` de chaque `challenge.yml`. Workflow recommandé via le Makefile :

```bash
make gen-passwords                  # (re)génère data/raw/passwords.csv depuis le repo de challenges
make gen-inventory                  # régénère inventories/summercamp/hosts.ini
make sync-compose                   # copie les docker-compose.yml des challenges dans group_vars/
make regen                          # les trois étapes ci-dessus, dans l'ordre
```

`CHALLENGE_DIR` (défaut `../../DCISummerCamp2026`) pointe vers le repo de challenges. `DRY_RUN=1` affiche un diff sans rien écrire.

#### Deux types de challenges, deux groupes Ansible distincts

Chaque challenge déployable définit `extra.deployment_info.individual_instance` dans son `challenge.yml` (repo CTFd) :

| `individual_instance` | Comportement | Groupe Ansible généré | Sous-réseau / vm_id |
|---|---|---|---|
| `true` (ou absent du bloc, défaut) | **Une VM par équipe** | un groupe par challenge (ex. `[NanoControl_Credentials_1]`), tous rassemblés sous **`[chall:children]`** | `10.130.{idx}.{team}`, `vm_id = 2000000 + idx*1000 + team` |
| `false` | **Une seule VM partagée** par tout l'événement | un groupe par challenge, rassemblés sous **`[single_instance_challenges:children]`** (pas sous `chall`) | `10.130.0.{100+idx}`, `vm_id = 5000000 + idx*100` |
| absent / pas de `docker-compose.yml` | Pas d'infra à déployer (challenge statique) | aucun (loggé `[not to be deployed]` par le script) | — |

Le per-équipe (`individual_instance: true`) est aussi celui dont les hôtes/tokens viennent de `data/raw/passwords.csv` (une colonne CSV = un challenge par-équipe ; `genpass.py` n'y ajoute volontairement que les challenges `individual_instance: true`).

**`chall` et `single_instance_challenges` sont deux groupes complètement disjoints — `chall` ne contient jamais de challenge single-instance.**

#### Quel playbook déploie quoi

- `make sc/chall` exécute `playbooks/sc/chall.yaml`, dont **toutes les plays ciblent `hosts: chall`** (provisioning VM, install Docker, déploiement du docker-state-exporter). Il ne déploie donc **que les challenges par-équipe**.
- `make sc/single_instance_chall` exécute `playbooks/sc/single_instance_chall.yaml`, structure identique mais ciblant `hosts: single_instance_challenges`. Déploie **uniquement les challenges à instance unique**.
- Les deux playbooks partagent le même rôle `docker-state-exporter` ; le template d'environnement (`roles/docker-state-exporter/templates/ctf-docker-state-exporter.env.j2`) détecte le groupe d'appartenance pour renseigner `TEAM` (numéro d'équipe pour `chall`, `shared` pour `single_instance_challenges`) et `CHALLENGE` (nom du challenge dans les deux cas).
- Prometheus scrape les deux groupes via des jobs séparés mais symétriques : `node_exporter_chall` et `node_exporter_single_instance` (construits dynamiquement dans `playbooks/sc/monitoring.yaml`, aucune édition requise à l'ajout d'un challenge).

Pour ajouter un nouveau challenge par-équipe :

1. Le challenge définit `extra.deployment_info.individual_instance: true` dans son `challenge.yml` (repo CTFd)
2. `make regen` (ou les 3 étapes manuelles ci-dessus)
3. Créer `inventories/summercamp/group_vars/{challenge}.yaml` (configuration Proxmox, réseau, source du docker-compose)
4. `make sc/chall` — le challenge apparaît automatiquement dans `chall`, dans Prometheus (`node_exporter_chall` job, dynamique) et dans le dashboard Grafana "Summercamp Challenges" (variable `$challenge`)
5. Le challenge apparaît automatiquement dans la zone DNS `.ctf`

Pour ajouter un nouveau challenge single-instance, même procédure en remplaçant `individual_instance: true` par `false` et `make sc/chall` par `make sc/single_instance_chall` à l'étape 4 (job Prometheus `node_exporter_single_instance`).

> **Prérequis** : `data/raw/passwords.csv` n'est pas versionné. Il doit être présent localement avant de lancer le script ou les playbooks.

### Dépendance CTFd

Les définitions de challenges (flags, catégories, points) sont gérées dans un repo CTFd séparé. Ce repo doit être cloné et configuré avant le déploiement des challenges :

- Le repo CTFd doit être accessible pour peupler les challenges sur la plateforme
- Les tokens par équipe dans `passwords.csv` correspondent aux identifiants générés côté CTFd

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
