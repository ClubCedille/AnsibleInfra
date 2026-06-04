# Monitoring LLM Context (event integration)

## Purpose

Provide a stable, repo-versioned context for implementing cedille.monitoring roles in AnsibleInfra.

This file is the canonical context for this repository.
Do not rely only on .cache content, because galaxy-install can overwrite it.

## Collection usage in this repo

The monitoring collection is installed from:

- collections/requirements.yml -> .cache/AnsibleRoles/monitoring

Primary roles considered:

- prometheus
- grafana
- loki
- alertmanager
- alloy
- node_exporter
- blackbox_exporter
- snmp_exporter

## Event integration decisions

Current decisions:

- Phase 2 rollout target: node_exporter on netservices hosts (dhcp, dns, stork)
- Phase 3 rollout target: Alloy on netservices hosts with push to Loki on monitoring01
- Phase 4 rollout target: blackbox_exporter and snmp_exporter on monitoring01

## Naming and placement conventions

Inventory:

Files:

- phase 2 playbook: playbooks/monitoring/node-exporters.yaml
- node exporter group vars: inventories/event/group_vars/netservices_node_exporter.yaml
- phase 3 playbook: playbooks/monitoring/alloy.yaml
- alloy group vars: inventories/event/group_vars/netservices_alloy.yaml
- phase 4 playbook: playbooks/monitoring/exporters.yaml
- exporters group vars: inventories/event/group_vars/monitoring_exporters.yaml

## Variable conventions

Use role-native prefixes from cedille.monitoring defaults:

- grafana\_\*
- loki\_\*
- alloy\_\*
- node*exporter*\*
- blackbox*exporter*\*
- snmp*exporter*\*

## Secret handling

Vault required for:

- Alertmanager Slack webhook value
- Any explicit Grafana admin credential override

Never store plaintext webhook tokens in git.

## Rollout strategy

Phase 1:

- Deploy core services on monitoring host only.

Phase 2:

- Add node_exporter on netservices hosts.

Phase 3:

- Add Alloy for log shipping.

Phase 4:

- Add blackbox_exporter and snmp_exporter.

## Validation targets

Core service ports expected on monitoring01:

- Grafana: 3000
- Loki: 3100
- Prometheus: 9090
- Alertmanager: 9093

Prometheus should expose healthy local core targets before adding external targets.
