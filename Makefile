infra_inventory = inventories/infra/hosts.ini
event_inventory = inventories/event/hosts.ini
use_event_inventory ?= 0

ifeq ($(use_event_inventory),1)
inventory ?= $(event_inventory)
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
LOCAL_ROLES_DIR = .cache/roles

# DRY_RUN=1 active le mode Ansible check+diff.
DRY_RUN ?= 0
ANSIBLE_MODE_FLAGS =
ifeq ($(DRY_RUN),1)
ANSIBLE_MODE_FLAGS += --check --diff
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
$(1): galaxy-install $(playbook)/$(1).yaml
	$(VENV_BIN)/ansible-playbook -i $(inventory) $(playbook)/$(1).yaml --ask-vault-pass $(ANSIBLE_MODE_FLAGS)
endef

$(foreach target,$(playbook_targets),$(eval $(call PLAYBOOK_TARGET_TEMPLATE,$(target))))

