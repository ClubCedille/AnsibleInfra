# Provisionnement d'un cluster Kubernetes avec Omni self-hébergé

Procédure complète pour déployer un cluster Kubernetes Talos géré par l'Omni Cedille (`omni.etsmtl.club`), depuis la préparation réseau jusqu'à l'accès `kubectl`. Basé sur le déploiement du cluster `k8s-poc` (5 CP + 8 workers, VLAN 1300).

---

## Vue d'ensemble

```
[1] Réseau       → VLAN Proxmox + interface OPNsense + règles firewall
[2] DHCP         → Kea hot-standby avec réservations MAC→IP
[3] Image Talos  → Générer via Omni UI, uploader sur les hôtes Proxmox
[4] VMs          → Créer et démarrer via Ansible (ISO boot → install disk → reboot)
[5] Omni         → Machines apparaissent « Available » → créer Cluster + MachineSets
[6] Post-setup   → QEMU guest agent, kubeconfig, vérification
```

Les étapes 1–3 peuvent se faire en parallèle.

---

## Étape 1 — Réseau

### 1a — VLAN sur Proxmox

Ajouter l'ID VLAN dans `inventories/infra/group_vars/pve.yaml` sous `pve_vlans_desired` :

```yaml
- id: 1300
  comment: "k8s poc"
  mtu: 1500
```

```bash
ansible-playbook playbooks/network/update-vlans.yaml -i inventories/infra/
```

> Le VLAN doit aussi être ajouté manuellement sur le switch (trunk vers les hôtes Proxmox).

### 1b — Interface VLAN sur OPNsense

Ajouter dans `inventories/infra/group_vars/routers.yaml` sous `vm_net_trunk.vlans` :

```yaml
- id: 1300
  interface_name: opt16    # prochaine interface disponible
  vip: "10.0.130.1"
  network: "10.0.130.0"
  netmask: 24
```

L'assignation de l'interface (mapping vtnet0.1300 → opt16 + IP) passe par le SSH escape hatch :

```bash
ansible-playbook playbooks/infra/opnsense-interface-provision.yaml -i inventories/infra/ --tags apply
```

### 1c — Règles firewall OPNsense

Ajouter les règles dans `routers.yaml` (ou via `playbooks/infra/opnsense-k8s-poc.yaml`) :

```yaml
# k8s poc → mgmt/Ceph/GarageHQ
- interface: opt16
  source_net: "10.0.130.0/24"
  dest_net: "10.0.21.0/24"
  action: pass
  sequence: 340

# k8s poc → WAN (pull images)
- interface: opt16
  source_net: "10.0.130.0/24"
  dest_net: any
  action: pass
  sequence: 345

# mgmt → k8s poc (accès admin)
- interface: mgmt
  source_net: "10.0.21.0/24"
  dest_net: "10.0.130.0/24"
  action: pass
  sequence: 330
```

---

## Étape 2 — DHCP

Kea DHCP4 en hot-standby sur deux VMs dédiées avec réservations MAC→IP pour tous les nœuds. Pattern établi dans `inventories/infra/group_vars/k8s_poc_dhcp.yaml`.

```bash
ansible-playbook playbooks/omni/k8s-poc-dhcp.yaml -i inventories/infra/ --ask-vault-pass
```

Les réservations statiques sont essentielles : Omni utilise les hostnames des machines pour l'auto-découverte, et les IPs doivent être stables pour les règles firewall et le DNS.

---

## Étape 3 — Image Talos

L'image Talos pour Omni **n'est pas l'ISO standard Talos** — elle est générée par Omni et contient le join token + l'endpoint SideroLink pré-configurés.

### 3a — Générer l'image depuis l'UI Omni

1. Aller sur `https://omni.etsmtl.club` → **Download Installation Media**
2. Choisir :
   - Type : **ISO** (pour boot BIOS depuis CDROM virtuel)
   - Architecture : `amd64`
   - Version Talos : dernière disponible (ex. `1.13.5`)
   - Extensions à inclure : `qemu-guest-agent`, `lldpd` (et toute autre extension nécessaire au cluster)
3. Télécharger l'ISO

> L'URL contient un token d'enrôlement — traiter comme un secret.

### 3b — Uploader sur les hôtes Proxmox

```bash
ansible-playbook playbooks/proxmox/upload-talos-iso.yaml -i inventories/infra/
```

Le playbook distribue l'ISO sur tous les hôtes PVE dans `/var/lib/vz/template/iso/`.

---

## Étape 4 — VMs Proxmox

### Inventaire

Créer le groupe dans `inventories/infra/hosts.ini` :

```ini
[k8s_poc_controlplanes]
k8s-poc-controlplane01.k8s.etsmtl.club ansible_host=10.0.130.11
# ... (controlplane02–05)

[k8s_poc_workers]
k8s-poc-worker01.k8s.etsmtl.club ansible_host=10.0.130.21
# ... (worker02–08)

[k8s_poc:children]
k8s_poc_controlplanes
k8s_poc_workers
```

`group_vars/k8s_poc.yaml` définit les valeurs communes (storage, réseau, API Proxmox).
`host_vars/<hostname>.yaml` définit par nœud : `vm_id`, `vm_proxmox_node`, `vm_cpu_cores`, `vm_memory_mb`, `vm_disk_size`.

### Provisionnement

```bash
ansible-playbook playbooks/omni/k8s-poc-vms.yaml -i inventories/infra/ --ask-vault-pass
```

Le playbook :
1. Crée la VM avec disque vierge + ISO en CDROM, `agent: enabled=1`
2. Active le QEMU guest agent sur les VMs existantes (`update: true`)
3. Démarre la VM

Talos boot depuis l'ISO, s'installe sur `virtio0`, reboot depuis le disque. L'enrôlement dans Omni se fait automatiquement via SideroLink (WireGuard IPv6).

**Attendre ~5 minutes** que les machines apparaissent comme « Available » dans l'UI Omni avant de continuer.

---

## Étape 5 — Cluster Omni

### 5a — Créer les ressources Omni

```bash
ansible-playbook playbooks/omni/k8s-poc-cluster.yaml -i inventories/infra/
```

Ce playbook :
1. Récupère automatiquement les UUIDs des machines depuis Omni (par hostname)
2. Génère le manifest depuis `playbooks/omni/templates/k8s-poc-cluster.yaml.j2`
3. Applique via `omnictl apply`

Le manifest crée :
- `Clusters.omni.sidero.dev` — le cluster avec les versions Talos/k8s
- `MachineSets.omni.sidero.dev` — control-planes et workers
- `MachineSetNodes.omni.sidero.dev` — assignation UUID → MachineSet
- `ConfigPatches.omni.sidero.dev` — config lldpd (ExtensionServiceConfig)

### 5b — Vérifier la progression

```bash
omnictl cluster status k8s-poc
```

Le cluster passe par : `SCALING_UP` → `INSTALLING` → `RUNNING`.

---

## Étape 6 — Post-setup

### 6a — QEMU guest agent (power-cycle requis)

L'activation de `agent: enabled=1` sur Proxmox ne suffit pas — le canal virtio-serial n'apparaît qu'après un **arrêt/démarrage complet** (pas un reboot Talos).

```bash
ansible-playbook playbooks/omni/k8s-poc-vms.yaml -i inventories/infra/ \
  -e vm_power_cycle=true --ask-vault-pass
```

Sans ce power-cycle, le service `ext-qemu-guest-agent` reste en attente de `/dev/virtio-ports/org.qemu.guest_agent.0` et la machine ne passe jamais `ready` dans Omni.

### 6b — Kubeconfig

Depuis l'UI Omni : cluster `k8s-poc` → **Download kubeconfig**.

Merger dans `~/.kube/config` :

```bash
KUBECONFIG=~/.kube/config:~/Downloads/k8s-poc-kubeconfig.yaml kubectl config view --flatten > /tmp/merged && mv /tmp/merged ~/.kube/config
kubectl config use-context omni-k8s-poc
kubectl get nodes
```

---

## Pièges connus

### Omni COSI — champs en minuscules

Tous les champs `spec` des ressources Omni sont en **minuscules** — le camelCase est silencieusement ignoré :

```yaml
# FAUX (ignoré silencieusement, donne des erreurs "invalid talos version")
spec:
  talosVersion: "1.13.5"
  kubernetesVersion: "1.33.1"
  features:
    enableWorkloadProxy: false

# CORRECT
spec:
  talosversion: "1.13.5"
  kubernetesversion: "1.33.1"
  features:
    enableworkloadproxy: false
```

Idem pour `updatestrategy: 1` (entier, pas un dict `{type: Rolling}`).

### MachineSetNode — trois labels obligatoires

Un `MachineSetNode` sans le label de rôle reste à `machines.total: 0` sans erreur visible :

```yaml
labels:
  omni.sidero.dev/cluster: k8s-poc
  omni.sidero.dev/machine-set: k8s-poc-control-planes
  omni.sidero.dev/role-controlplane: ""   # ← obligatoire, souvent oublié
```

Le label correct est `role-controlplane` (sans tiret entre "control" et "plane") et `machine-set` (avec tiret).

### lldpd — ExtensionServiceConfig, pas machine.files

La configuration de l'extension lldpd passe par `ExtensionServiceConfig` avec `configFiles`, **pas** par `machine.files`. Le chemin est `/usr/local/etc/lldpd/lldpd.conf` (pas `/etc/lldpd.d/`).

```yaml
# Dans spec.data du ConfigPatch Omni :
---
apiVersion: v1alpha1
kind: ExtensionServiceConfig
name: lldpd
configFiles:
  - content: |
      configure lldp portidsubtype ifname
      configure system interface pattern *
    mountPath: /usr/local/etc/lldpd/lldpd.conf
```

> L'éditeur de patch dans l'UI Omni affiche ce type de document comme « vide » — c'est un bug d'affichage, la config est bien appliquée (vérifiable via `omnictl get clustermachineconfigpatches <uuid>`).

### machine.files — op: create restreint à /var

Si `machine.files` est utilisé pour d'autres besoins :
- `op: create` → interdit hors de `/var` (erreur au boot : `create operation not allowed outside of /var`)
- `op: overwrite` → fonctionne pour les chemins `/etc` (si le répertoire parent existe)

### Boolean via -e dans Ansible

Passer un booléen via `-e` le transmet comme string. Utiliser `| bool` dans le `when` :

```yaml
when: vm_power_cycle | default(false) | bool
```

### Source de vérité pour le format des ressources Omni

En cas de doute sur le format d'une ressource Omni, générer un template de référence :

```bash
omnictl cluster template render --name <cluster> | head -100
```

C'est la source authoritative — les exemples en ligne peuvent être outdatés.

---

## Adapter pour un nouveau cluster

1. Copier `inventories/infra/group_vars/k8s_poc.yaml` → `k8s_<nom>.yaml`
2. Adapter subnet/VLAN/IPs, vm_ids, distribution sur les nœuds Proxmox
3. Créer les host_vars pour chaque nœud
4. Copier `playbooks/omni/k8s-poc-vms.yaml` et `k8s-poc-cluster.yaml`, adapter les noms
5. Copier `playbooks/omni/templates/k8s-poc-cluster.yaml.j2`, adapter l'id du cluster et les counts dans l'assert
6. Générer une nouvelle image Talos depuis l'UI Omni (chaque cluster a son propre token d'enrôlement)

Le playbook `k8s-poc-cluster.yaml` découvre automatiquement les UUIDs des machines par hostname — le seul prérequis est que les machines soient nommées avec un pattern incluant `controlplane` ou `worker`.
