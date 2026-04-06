# AnsibleInfra

Gestion de l'infrastructure physique de Cedille via Ansible

## Layout

```
.
├─ inventory/
│   ├─ infra
│   └─ staging
├─ out/
│   ├─ generic-config
│   └─ rack-config
├─ playbook/
│   ├─ ceph
│   ├─ networking
│   ├─ proxmox
│   └─ SAN
├─ ansible.conf
├─ Makefile
└─ requirements.txt
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
cd ansible-staging
make venv
```

Optionnel: installer les packages ansible et ansible-lint localement pour que l'autocomplétion fonctionne dans le terminal ainsi que le serveur de langage dans VSCode et/ou autres éditeurs de textes

```bash
pip3 install ansible
pip3 install ansible-lint
```

