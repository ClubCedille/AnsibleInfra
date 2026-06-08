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

`scripts/gen_inventory.py` régénère `inventories/summercamp/hosts.ini` à partir de `data/raw/passwords.csv`.

Le CSV doit avoir les colonnes `team`, `vmid`, `password`, puis une colonne par challenge (ex. `nanocontrol`, `nanocontrol2`). Chaque colonne challenge est détectée automatiquement : son nom devient le slug du groupe Ansible et le suffixe du hostname (`{hash}-{challenge}.ctf`).

```bash
python3 scripts/gen_inventory.py
```

Pour ajouter un nouveau challenge :

1. Ajouter une colonne dans `data/raw/passwords.csv` avec le nom du challenge et les tokens par équipe
2. Relancer `python3 scripts/gen_inventory.py`
3. Créer `inventories/summercamp/group_vars/{challenge}.yaml` (configuration Proxmox, réseau, docker-compose)
4. Le challenge apparaît automatiquement dans la zone DNS `.ctf`

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
