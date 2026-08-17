# Runbook — resize k8s-shared (AnsibleInfra#30)

> Commandes à exécuter manuellement par l'opérateur, node par node. Rien ici n'est exécuté
> automatiquement — c'est un aide-mémoire avec les commandes exactes dans l'ordre.
> Contexte complet : [`../../docs/migration-prodv2-to-k8s-shared/notes.md`](../../docs/migration-prodv2-to-k8s-shared/notes.md).

## Avant de commencer

- `k8s-shared` est un cluster de **production** qui sert du trafic réel — un seul node à la
  fois en resize, jamais deux en parallèle.
- Vérifier l'état actuel avant chaque étape (ne pas supposer un état "zéro") :
  ```bash
  kubectl --context=cedille-k8s-shared get nodes -o wide
  ```
- Contexte kubectl : `cedille-k8s-shared`. Contexte Omni : cluster `k8s-shared`.

---

## Partie A — Resize des 6 workers + éventuellement les CP existants

Nodes concernés (host_vars déjà créés dans cette PR) :

| Node Ansible | Node Proxmox | Cible cores/RAM | Déjà conforme ? |
|---|---|---|---|
| `k8s-shared-worker-0` | pve01 | 24c / 64GB | RAM ✅, cores à monter |
| `k8s-shared-worker-1` | pve02 | 24c / 64GB | RAM ✅, cores à monter |
| `k8s-shared-worker-2` | pve03 | 24c / 64GB | ⚠️ RAM 24→64GB à corriger, cores à monter |
| `k8s-shared-worker-3` | pve04 | 24c / 64GB | RAM ✅, cores à monter |
| `k8s-shared-worker-4` | pve06 | 16c / 24GB | RAM ✅, cores à monter |
| `k8s-shared-worker-5` | pve07 | 24c / 64GB | RAM ✅, cores à monter |

Control-planes (pve03/04/06/07) : **ne pas toucher** — usage réel <65% (mesuré via
`talosctl memory`), rester à 4c/8GB (décision opérateur, cf. notes.md §2 et §10).

### Cycle par node (répéter pour chaque worker, un seul à la fois)

Remplacer `<node>` par le nom kubectl (ex. `k8s-shared-worker-2`), `<vmid>` par le
`vm_id` du host_vars correspondant, `<ip>` par l'IP interne Talos (`ansible_host` dans
`hosts.ini`, ou `kubectl get nodes -o wide`).

```bash
# a. Drain
kubectl --context=cedille-k8s-shared cordon <node>
kubectl --context=cedille-k8s-shared drain <node> --ignore-daemonsets --delete-emptydir-data

# b. Extinction propre (préférer talosctl à qm stop quand possible)
talosctl --context cedille-k8s-shared -n <ip> shutdown
# Vérifier l'arrêt côté Proxmox avant de continuer :
ssh root@10.0.21.51 "pvesh get /nodes/<pve-node>/qemu/<vmid>/status/current --output-format json"

# c. Resize (Ansible, cores+memory vers la cible host_vars)
cd ~/Cedille/AnsibleInfra
ansible-playbook playbooks/proxmox/resize-vm.yaml -i inventories/infra/ \
  --ask-vault-pass --limit <node>

# d. Redémarrage
ssh root@10.0.21.51 "pvesh create /nodes/<pve-node>/qemu/<vmid>/status/start"
# (ou, si le node PVE cible n'est pas pve01, adapter l'IP mgmt — cf. table topologie notes.md §2)

# Attendre Ready avant de continuer :
kubectl --context=cedille-k8s-shared get node <node> -w

# e. Reprise du trafic
kubectl --context=cedille-k8s-shared uncordon <node>

# f. Vérifier la capacité mise à jour
kubectl --context=cedille-k8s-shared get node <node> \
  -o custom-columns=NAME:.metadata.name,CPU:.status.capacity.cpu,MEM:.status.capacity.memory
```

Ordre recommandé (du moins au plus risqué — laisser worker-2 pour la fin car c'est le seul
avec un vrai changement de RAM, pas juste de cores) :
`worker-4 → worker-0 → worker-1 → worker-3 → worker-5 → worker-2`.

---

## Partie B — Ajout des 3 nouveaux nodes (worker-6/pve05, worker-7/pve08, controlplane-4/pve01)

**Ne pas exécuter avant feu vert explicite de l'opérateur** (cf. section "à ne pas faire" de
l'issue #30). Séquence complète une fois autorisée :

```bash
cd ~/Cedille/AnsibleInfra

# 1. Générer l'image Talos pour k8s-shared depuis l'UI Omni (token propre au cluster —
#    NE PAS réutiliser celui de k8s-poc) et l'uploader.
#    Adapter playbooks/proxmox/upload-talos-iso.yaml (nouveau nom de fichier ISO) avant.
ansible-playbook playbooks/proxmox/upload-talos-iso.yaml -i inventories/infra/

# 2. Provisionner les 3 VMs (worker-6, worker-7, controlplane-4)
ansible-playbook playbooks/omni/k8s-shared-vms.yaml -i inventories/infra/ --ask-vault-pass

# 3. Attendre ~5 min que les 3 machines apparaissent "Available" dans Omni
omnictl get machines

# 4. Créer les MachineSetNodes (rattache les 3 nodes aux MachineSets existants)
ansible-playbook playbooks/omni/k8s-shared-cluster.yaml -i inventories/infra/

# 5. Suivre la progression
omnictl cluster status k8s-shared
kubectl --context=cedille-k8s-shared get nodes -o wide

# 6. Post-setup : power-cycle pour activer le canal qemu-guest-agent (comme k8s-poc étape 6a)
ansible-playbook playbooks/omni/k8s-shared-vms.yaml -i inventories/infra/ \
  -e vm_power_cycle=true --ask-vault-pass --limit k8s-shared-worker-6,k8s-shared-worker-7,k8s-shared-controlplane-4
```

⚠️ Point à valider avant l'exécution réelle (non résolu par la recherche) : les 9 VMs
k8s-shared existantes n'ont pas de playbook d'origine retrouvé et un layout disque légèrement
différent du pattern k8s-poc connu (`ide0` direct plutôt que `virtio0` + cloud-init) — voir
le commentaire en tête de `playbooks/omni/k8s-shared-vms.yaml` et
`inventories/infra/group_vars/k8s_shared.yaml`. À confirmer/ajuster avant le provisionnement
réel des 3 nouveaux nodes.

---

## Vérification finale

```bash
kubectl --context=cedille-k8s-shared get nodes -o wide
# → 13 nodes Ready (5 CP + 8 workers), capacités conformes à la cible

omnictl cluster status k8s-shared
# → RUNNING
```
