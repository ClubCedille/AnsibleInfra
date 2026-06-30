infra_inventory = inventories/infra/hosts.ini
event_inventory = inventories/event/hosts.ini
sc_inventory = inventories/summercamp/hosts.ini
inventory_name ?= infra

ifeq ($(inventory_name),event)
inventory ?= $(event_inventory)
else ifeq ($(inventory_name),sc)
inventory ?= $(sc_inventory)
else ifeq ($(inventory_name),summercamp)
inventory ?= $(sc_inventory)
else
inventory ?= $(infra_inventory)
endif

playbook = playbooks

playbook_files = $(wildcard $(playbook)/*/*.yaml)
playbook_targets = $(patsubst $(playbook)/%.yaml,%,$(playbook_files))

PYTHON = .venv/bin/python3

VENV_DIR = .venv
VENV_BIN = $(VENV_DIR)/bin
ANSIBLE_ROLES_REPO_URL = https://github.com/ClubCedille/AnsibleRoles.git
ANSIBLE_ROLES_REPO_REF = main
ANSIBLE_ROLES_REPO_DIR = .cache/AnsibleRoles
ANSIBLE_ROLES_DEV_REF = feature/opnsense-rules-interfaces
LOCAL_ROLES_DIR = .cache/roles

# VAULT_PASSWORD_FILE=<path> utilise un fichier vault au lieu de --ask-vault-pass.
# Ex. : make infra/opnsense-config VAULT_PASSWORD_FILE=~/.vault
#        make infra/opnsense-diff   VAULT_PASSWORD_FILE=~/CEDILLE/.vault
VAULT_PASSWORD_FILE ?=
VAULT_FLAG = --ask-vault-pass
ifneq ($(strip $(VAULT_PASSWORD_FILE)),)
VAULT_FLAG = --vault-password-file "$(VAULT_PASSWORD_FILE)"
endif

# DRY_RUN=1 active le mode Ansible check+diff.
DRY_RUN ?= 0
ANSIBLE_MODE_FLAGS =
ifeq ($(DRY_RUN),1)
ANSIBLE_MODE_FLAGS += --check --diff
endif

# EXTRA_VARS="key=value ..." est passé à ansible-playbook via --extra-vars sur
# toutes les cibles (ex. EXTRA_VARS="vm_delete_if_exists=true" pour forcer la
# suppression d'une VM dans cedille.proxmox.vm avant de la recréer).
EXTRA_VARS ?=
EXTRA_VARS_FLAG =
ifneq ($(strip $(EXTRA_VARS)),)
EXTRA_VARS_FLAG = --extra-vars "$(EXTRA_VARS)"
endif

# LIMIT=<pattern> limite l'exécution à un sous-ensemble d'hôtes (ex. LIMIT=pve01)
LIMIT ?=
LIMIT_FLAG =
ifneq ($(strip $(LIMIT)),)
LIMIT_FLAG = --limit "$(LIMIT)"
endif

.PHONY: venv
venv:
	test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	touch $(VENV_DIR)/bin/activate

.PHONY: galaxy-install
galaxy-install: venv
	@if [ -d "$(ANSIBLE_ROLES_REPO_DIR)/.git" ]; then \
		git -C "$(ANSIBLE_ROLES_REPO_DIR)" fetch --depth 1 origin "$(ANSIBLE_ROLES_REPO_REF)"; \
		git -C "$(ANSIBLE_ROLES_REPO_DIR)" checkout --force FETCH_HEAD; \
		git -C "$(ANSIBLE_ROLES_REPO_DIR)" reset --hard FETCH_HEAD; \
	else \
		git clone --depth 1 --branch "$(ANSIBLE_ROLES_REPO_REF)" "$(ANSIBLE_ROLES_REPO_URL)" "$(ANSIBLE_ROLES_REPO_DIR)"; \
	fi
	@mkdir -p "$(LOCAL_ROLES_DIR)"
	@find "$(ANSIBLE_ROLES_REPO_DIR)" -mindepth 3 -maxdepth 3 -type d -path '*/roles/*' | while read src; do \
		collection_name=$$(basename $$(dirname $$(dirname "$$src"))); \
		role_name=$$(basename "$$src"); \
		dest="$(LOCAL_ROLES_DIR)/cedille.$$collection_name.$$role_name"; \
		rm -rf "$$dest"; \
		mkdir -p "$$dest"; \
		cp -a "$$src"/. "$$dest"/; \
		done
	$(VENV_BIN)/ansible-galaxy collection install -r collections/requirements.yml --force

.PHONY: galaxy-install-dev
galaxy-install-dev: venv
	@if [ -d "$(ANSIBLE_ROLES_REPO_DIR)/.git" ]; then \
		git -C "$(ANSIBLE_ROLES_REPO_DIR)" fetch --depth 1 origin "$(ANSIBLE_ROLES_DEV_REF)"; \
		git -C "$(ANSIBLE_ROLES_REPO_DIR)" checkout --force FETCH_HEAD; \
		git -C "$(ANSIBLE_ROLES_REPO_DIR)" reset --hard FETCH_HEAD; \
	else \
		git clone --depth 1 --branch "$(ANSIBLE_ROLES_DEV_REF)" "$(ANSIBLE_ROLES_REPO_URL)" "$(ANSIBLE_ROLES_REPO_DIR)"; \
	fi
	@mkdir -p "$(LOCAL_ROLES_DIR)"
	@find "$(ANSIBLE_ROLES_REPO_DIR)" -mindepth 3 -maxdepth 3 -type d -path '*/roles/*' | while read src; do \
		collection_name=$$(basename $$(dirname $$(dirname "$$src"))); \
		role_name=$$(basename "$$src"); \
		dest="$(LOCAL_ROLES_DIR)/cedille.$$collection_name.$$role_name"; \
		rm -rf "$$dest"; \
		mkdir -p "$$dest"; \
		cp -a "$$src"/. "$$dest"/; \
		done
	$(VENV_BIN)/ansible-galaxy collection install -r collections/requirements.yml --force

.PHONY: list-playbooks
list-playbooks:
	@printf '%s\n' $(playbook_targets)

.PHONY: lint-tools
lint-tools: venv
	$(PYTHON) -m pip install ansible-lint yamllint

.PHONY: lint
lint: galaxy-install lint-tools
	$(VENV_BIN)/ansible-lint playbooks
	$(VENV_BIN)/yamllint -c .yamllint inventories playbooks collections .github/workflows

define PLAYBOOK_TARGET_TEMPLATE
.PHONY: $(1)
$(1): $(playbook)/$(1).yaml
	$(VENV_BIN)/ansible-playbook -i $(inventory) $(playbook)/$(1).yaml $(VAULT_FLAG) $(ANSIBLE_MODE_FLAGS) $(LIMIT_FLAG) $(EXTRA_VARS_FLAG)
endef

$(foreach target,$(playbook_targets),$(eval $(call PLAYBOOK_TARGET_TEMPLATE,$(target))))

# ---------------------------------------------------------------------------
# Summercamp — déploiement d'un challenge spécifique (évite de surcharger
# l'infra en lançant les ~300 VMs de tous les challenges d'un coup).
#
# Usage : make sc/chall/<NomDuChallenge> inventory_name=sc
#   ex.  make sc/chall/MITM inventory_name=sc
#   ex.  make sc/chall/NanoControl_Credentials_1,Acces_Interdit inventory_name=sc
# <NomDuChallenge> doit correspondre à un nom de groupe de l'inventaire
# (voir [chall:children] dans inventories/summercamp/hosts.ini), et accepte
# tout ce que comprend --limit d'Ansible (liste séparée par virgules, motifs).
# ---------------------------------------------------------------------------

.PHONY: sc/chall/%
sc/chall/%: $(playbook)/sc/chall.yaml
	$(VENV_BIN)/ansible-playbook -i $(inventory) $(playbook)/sc/chall.yaml $(VAULT_FLAG) --limit "$*" $(ANSIBLE_MODE_FLAGS) $(EXTRA_VARS_FLAG)

# Même principe pour playbooks/sc/reset_chall.yaml (docker compose down/up sur
# des hosts précis) : make sc/reset_chall/<hosts ou groupe> inventory_name=sc
.PHONY: sc/reset_chall/%
sc/reset_chall/%: $(playbook)/sc/reset_chall.yaml
	$(VENV_BIN)/ansible-playbook -i $(inventory) $(playbook)/sc/reset_chall.yaml $(VAULT_FLAG) --limit "$*" $(ANSIBLE_MODE_FLAGS) $(EXTRA_VARS_FLAG)

# Même principe pour playbooks/sc/update_chall.yaml (docker compose pull puis
# down/up, pour forcer la mise à jour d'une image plus récente) :
# make sc/update_chall/<hosts ou groupe> inventory_name=sc
.PHONY: sc/update_chall/%
sc/update_chall/%: $(playbook)/sc/update_chall.yaml
	$(VENV_BIN)/ansible-playbook -i $(inventory) $(playbook)/sc/update_chall.yaml $(VAULT_FLAG) --limit "$*" $(ANSIBLE_MODE_FLAGS) $(EXTRA_VARS_FLAG)

# Met à jour les challenges single-instance (playbooks/sc/update_single_chall.yaml) :
# resynchronise install_docker_compose_content depuis CHALLENGE_DIR (sync-compose),
# pousse le docker-compose.yml résultant sur les VMs, puis pull + reconcile
# (pas de down/up ni de suppression de volumes : ce sont des VMs partagées
# par tout l'événement, contrairement au groupe `chall` par équipe).
# Usage : make sc/update_single_chall/<hosts ou groupe> inventory_name=sc
.PHONY: sc/update_single_chall/%
sc/update_single_chall/%: $(playbook)/sc/update_single_chall.yaml
	$(VENV_BIN)/ansible-playbook -i $(inventory) $(playbook)/sc/update_single_chall.yaml $(VAULT_FLAG) --limit "$*" $(ANSIBLE_MODE_FLAGS) $(EXTRA_VARS_FLAG)

# Même principe pour playbooks/sc/reboot.yaml (hard-stop + start via l'API
# Proxmox, ex. apt/dpkg lock coincé après un boot cloud-init) :
# make sc/reboot/<hosts ou groupe> inventory_name=sc
.PHONY: sc/reboot/%
sc/reboot/%: $(playbook)/sc/reboot.yaml
	$(VENV_BIN)/ansible-playbook -i $(inventory) $(playbook)/sc/reboot.yaml $(VAULT_FLAG) --limit "$*" $(ANSIBLE_MODE_FLAGS) $(EXTRA_VARS_FLAG)

# Déploie le fichier flag dans /home/sc sur toutes les VMs shellctf :
# make deploy-shellctf-flag
.PHONY: deploy-shellctf-flag
deploy-shellctf-flag: $(playbook)/sc/deploy_shellctf_flag.yaml
	$(VENV_BIN)/ansible-playbook -i $(sc_inventory) $(playbook)/sc/deploy_shellctf_flag.yaml $(VAULT_FLAG) $(ANSIBLE_MODE_FLAGS) $(EXTRA_VARS_FLAG)

# Provisionne et déploie le host secret.ctf (nginx + page narrative) :
# make deploy-secret-portal
.PHONY: deploy-secret-portal
deploy-secret-portal: $(playbook)/sc/secret_portal.yaml
	$(VENV_BIN)/ansible-playbook -i $(sc_inventory) $(playbook)/sc/secret_portal.yaml $(VAULT_FLAG) $(ANSIBLE_MODE_FLAGS) $(EXTRA_VARS_FLAG)

# ---------------------------------------------------------------------------
# Summercamp — génération des credentials et de l'inventaire
# ---------------------------------------------------------------------------

CHALLENGE_DIR ?= ../../DCISummerCamp2026
SC_CSV        = data/raw/passwords.csv

# PRUNE=1 pour supprimer du CSV les challenges absents/non-individuels
PRUNE ?= 0
PRUNE_FLAG =
ifeq ($(PRUNE),1)
PRUNE_FLAG = --prune
endif

# DRY_RUN=1 s'applique aussi aux scripts Python (affiche les diffs sans écrire)
PY_DRY_RUN_FLAG =
ifeq ($(DRY_RUN),1)
PY_DRY_RUN_FLAG = --dry-run
endif

# Génère/met à jour le CSV des credentials.
# Usage normal : make gen-passwords
# Avec purge    : make gen-passwords PRUNE=1
# Repo custom   : make gen-passwords CHALLENGE_DIR=/autre/chemin
.PHONY: gen-passwords
gen-passwords: venv
	$(PYTHON) scripts/genpass.py $(CHALLENGE_DIR) --output $(SC_CSV) $(PRUNE_FLAG) $(PY_DRY_RUN_FLAG)

# Génère l'inventaire Ansible depuis le CSV + le repo challenges.
# Les challenges single-instance (individual_instance=false) sont inclus.
# Les challenges sans deployment_info sont loggés [not to be deployed].
.PHONY: gen-inventory
gen-inventory: venv
	$(PYTHON) scripts/gen_inventory.py --challenge-dir $(CHALLENGE_DIR) $(PY_DRY_RUN_FLAG)

# Synchronise les docker-compose.yml des challenges dans group_vars/.
# Écrit challenge_docker_compose dans group_vars/{challenge}/main.yml.
# GROUP_VARS_DIR optionnel (défaut: inventories/summercamp/group_vars).
.PHONY: sync-compose
sync-compose: venv
	$(PYTHON) scripts/gen_inventory.py --challenge-dir $(CHALLENGE_DIR) --sync-compose \
		$(if $(GROUP_VARS_DIR),--group-vars-dir $(GROUP_VARS_DIR),) \
		$(PY_DRY_RUN_FLAG)

# Supprime les group_vars/{challenge}/ obsolètes générés par --sync-compose
# (challenge renommé/retiré, ou déplacé entre per-team et single-instance).
# Ne touche jamais un group_vars écrit à la main.
# Usage : make prune-group-vars CHALLENGE_DIR=...
#         make prune-group-vars DRY_RUN=1   (valide la liste sans rien supprimer)
.PHONY: prune-group-vars
prune-group-vars: venv
	$(PYTHON) scripts/gen_inventory.py --challenge-dir $(CHALLENGE_DIR) --prune-group-vars \
		$(if $(GROUP_VARS_DIR),--group-vars-dir $(GROUP_VARS_DIR),) \
		$(PY_DRY_RUN_FLAG)

# Régénération complète : passwords, inventaire, sync des composes.
.PHONY: regen
regen: gen-passwords gen-inventory sync-compose

