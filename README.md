# AnsibleInfra

Gestion de l'infrastructure physique de Cedille via Ansible

## Layout

```
.
├─ inventories/
│   ├─ infra
│   └─ event
├─ playbooks/
│   ├─ cisco-pnp
│   └─ proxmox
├─ scripts/
│   └─ expand_switch_selection.py
├─ data/
│   └─ raw/
│      └─ lanets-inventaire-switch.csv
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
make cisco-pnp/deployment inventory=inventories/event/hosts.ini
```

Valider la qualité YAML/Ansible localement:

```bash
make lint
```

## Script utilitaire inventaire

Le script de génération de snippets PnP est maintenant dans `scripts/expand_switch_selection.py`.

Exemple:

```bash
.venv/bin/python3 scripts/expand_switch_selection.py --help
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
