infra_inventory = inventory/infra/hosts.ini
staging_inventory = inventory/staging/hosts.ini
inventory ?= $(infra_inventory)

playbook = playbook

playbook_files = $(wildcard $(playbook)/*/*.yaml)
playbook_targets = $(patsubst $(playbook)/%.yaml,%,$(playbook_files))

PYTHON = .venv/bin/python3

VENV_DIR = .venv
VENV_BIN = $(VENV_DIR)/bin

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
	@if [ -f roles/requirements.yml ]; then \
		$(VENV_BIN)/ansible-galaxy install -r roles/requirements.yml; \
	else \
		printf '%s\n' "roles/requirements.yml not found; skipping galaxy-install"; \
	fi

.PHONY: list-playbooks
list-playbooks:
	@printf '%s\n' $(playbook_targets)

define PLAYBOOK_TARGET_TEMPLATE
.PHONY: $(1)
$(1): galaxy-install $(playbook)/$(1).yaml
	$(VENV_BIN)/ansible-playbook -i $(inventory) $$< --ask-vault-pass $(ANSIBLE_MODE_FLAGS)
endef

$(foreach target,$(playbook_targets),$(eval $(call PLAYBOOK_TARGET_TEMPLATE,$(target))))

