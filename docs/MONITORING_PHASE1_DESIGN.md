# Monitoring Phase 1 Design (event)

## Goal

Deploy a first monitoring iteration for the event environment with a dedicated host and a clear expansion path.

Phase 1 roles:

- cedille.monitoring.loki
- cedille.monitoring.alertmanager
- cedille.monitoring.prometheus
- cedille.monitoring.grafana

## Scope

In scope:

- Dedicated host: monitoring01.event.lanets.ca
- Core observability services: Loki, Alertmanager, Prometheus, Grafana
- Slack as the first alert destination
- Inventory and variables design ready for implementation

Out of scope:

- Alloy deployment (distributed or centralized)
- Node exporter rollout
- Blackbox exporter and SNMP exporter rollout
- Dashboard curation beyond datasource wiring

## Environment baseline

Current event hosts:

- opnsense01.event.lanets.ca (10.10.0.2)
- opnsense02.event.lanets.ca (10.10.0.3)
- dhcp01.event.lanets.ca (10.10.0.11)
- dhcp02.event.lanets.ca (10.10.0.12)
- dns01.event.lanets.ca (10.10.0.21)
- dns02.event.lanets.ca (10.10.0.22)
- stork01.event.lanets.ca (10.10.0.31)

Monitoring host to add:

- monitoring01.event.lanets.ca (proposed: 10.10.0.41)

## Architecture (Phase 1)

All services run on monitoring01:

- Loki on 3100
- Alertmanager on 9093
- Prometheus on 9090
- Grafana on 3000

Data flow:

- Prometheus scrapes local core targets first.
- Grafana reads from Prometheus and Loki.
- Alertmanager receives alerts from Prometheus.
- Slack notifications are handled by Alertmanager receiver.

## Inventory and file design

Planned file targets:

- inventories/event/hosts.ini
- inventories/event/group_vars/all.yaml
- inventories/event/group_vars/monitoring_core.yaml
- inventories/event/host_vars/monitoring01.event.lanets.ca.yaml
- playbooks/monitoring/core.yaml

## Proposed variable contract

Use role-native prefixes from cedille.monitoring:

- loki\_\*
- alertmanager\_\*
- prometheus\_\*
- grafana\_\*

Keep variables grouped in a dedicated file:

- inventories/event/group_vars/monitoring_core.yaml

Minimum structure:

- loki_enabled
- loki_server
- loki_storage
- alertmanager_enabled
- alertmanager_route
- alertmanager_receivers
- prometheus_enabled
- prometheus_scrape_configs
- prometheus_alerting
- grafana_enabled
- grafana_datasources

## Secrets and vault policy

All sensitive values must be Ansible Vault encrypted.
Expected secrets in Phase 1:

- Slack webhook URL (Alertmanager receiver)
- Optional Grafana admin password if overridden

Secret placement:

- Keep secret values in inventories/event/group_vars/monitoring_core.yaml as !vault values.
- Never commit plaintext webhook URLs.

## Deployment order

Recommended playbook role order:

1. cedille.monitoring.loki
2. cedille.monitoring.alertmanager
3. cedille.monitoring.prometheus
4. cedille.monitoring.grafana

Reasoning:

- Prometheus alerting endpoint should exist before Prometheus starts pushing alerts.
- Grafana datasources are valid once Prometheus and Loki are reachable.

## Acceptance criteria

Design is accepted when:

1. A dedicated monitoring host is defined in event inventory.
2. Monitoring variables are isolated in monitoring_core group vars.
3. Secrets are defined as vault entries, not placeholders.
4. A monitoring core playbook target exists and is listed by make list-playbooks.
5. Dry-run succeeds on event inventory for playbooks/monitoring/core.yaml.
6. Service endpoints are reachable on monitoring01:
   - 3000 (Grafana)
   - 3100 (Loki)
   - 9090 (Prometheus)
   - 9093 (Alertmanager)

## Operational validation checklist

After deployment:

1. Confirm systemd services are active.
2. Confirm Prometheus target health page has core targets up.
3. Confirm Grafana has both datasources configured and healthy.
4. Send a test alert and validate Slack delivery.

## Phase 2+ extension path

Next phases after Phase 1:

- Phase 2: node_exporter on dhcp/dns/stork hosts
- Phase 3: Alloy deployment for logs shipping
- Phase 4: blackbox_exporter and snmp_exporter rollout

This design intentionally keeps Phase 1 small, verifiable, and reversible.
