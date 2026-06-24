#!/usr/bin/env python3
"""
Suppression des VMs liées aux VLANs 20, 310, 601, untagged et zone grise.
Doit être exécuté directement sur un nœud Proxmox (pve01).

  scp scripts/cleanup_vlans_20_310_601.py root@10.0.21.51:/tmp/
  ssh root@10.0.21.51 python3 /tmp/cleanup_vlans_20_310_601.py --dry-run
  ssh root@10.0.21.51 python3 /tmp/cleanup_vlans_20_310_601.py --execute

vmid 100201 (opnsense01.prod.lanets.ca) EXCLU — routeur de production.
"""

import argparse, subprocess, time, sys

NODE_IPS = {
    'pve01': '10.0.21.51', 'pve02': '10.0.21.52', 'pve03': '10.0.21.53',
    'pve04': '10.0.21.54', 'pve06': '10.0.21.56', 'pve07': '10.0.21.57',
}

# VMs running — nécessitent kill PID puis destroy
RUNNING = {
    10110:  ('pve02', 'k3sm1.lan.etsmtl.club',              'VLAN 20'),
    10120:  ('pve04', 'k3sm2.lan.etsmtl.club',              'VLAN 20'),
    10210:  ('pve01', 'k3sa1.lan.etsmtl.club',              'VLAN 20'),
    10220:  ('pve02', 'k3sa2.lan.etsmtl.club',              'VLAN 20'),
    10230:  ('pve03', 'k3sa3.lan.etsmtl.club',              'VLAN 20'),
    10240:  ('pve04', 'k3sa4.lan.etsmtl.club',              'VLAN 20'),
    10250:  ('pve06', 'k3sa5.lan.etsmtl.club',              'VLAN 20'),
    10510:  ('pve01', 'testing.lan.etsmtl.club',            'ZONE GRISE'),
    300101: ('pve03', 'controlplane-01.etsmtl.club',        'UNTAGGED'),
    500001: ('pve03', 'controlplane-01.management.etsmtl.ca','UNTAGGED'),
    500011: ('pve02', 'worker-01.management.etsmtl.club',   'UNTAGGED'),
    600101: ('pve01', 'k3s-m01',                            'VLAN 601'),
    600102: ('pve02', 'k3s-m02',                            'VLAN 601'),
    600103: ('pve01', 'k3s-m03',                            'VLAN 601'),
    600201: ('pve01', 'k3s-w01',                            'VLAN 601'),
    600202: ('pve02', 'k3s-w02',                            'VLAN 601'),
    600203: ('pve01', 'k3s-w03',                            'VLAN 601'),
    600204: ('pve02', 'k3s-w04',                            'VLAN 601'),
    600205: ('pve01', 'k3s-w05',                            'VLAN 601'),
}

# VMs stoppées — destroy direct
STOPPED = {
    1000:   ('pve01', 'template-cloud-init',                'VLAN 20 (template)'),
    2000:   ('pve01', 'template-opnsense',                  'UNTAGGED (template)'),
    10130:  ('pve07', 'k3sm3.lan.etsmtl.club',              'VLAN 20'),
    10260:  ('pve07', 'k3sa6.lan.etsmtl.club',              'VLAN 20'),
    200004: ('pve01', 'gui.lan.etsmtl.club',                'VLAN 20'),
    400101: ('pve03', 'opnsense01 (old test)',               'UNTAGGED'),
    400102: ('pve02', 'opnsense02 (old test)',               'UNTAGGED'),
    801100: ('pve04', 'cs01.event.lanets.ca (tag 310)',      'VLAN 310'),
}


def ssh_cmd(ip, cmd, dry_run=False):
    if dry_run:
        print(f'    [DRY] ssh root@{ip} "{cmd}"')
        return 0
    r = subprocess.run(
        ['ssh', '-o', 'StrictHostKeyChecking=no', f'root@{ip}', cmd],
        capture_output=True, text=True
    )
    return r.returncode


def pvesh_delete(node, vmid, dry_run=False):
    cmd = ['pvesh', 'delete', f'/nodes/{node}/qemu/{vmid}',
           '--purge', '1', '--destroy-unreferenced-disks', '1']
    if dry_run:
        print(f'    [DRY] {" ".join(cmd)}')
        return 0
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f'    ERREUR: {r.stderr.strip()[:120]}')
    return r.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    dry_run = not args.execute

    total = len(RUNNING) + len(STOPPED)
    print(f'\n{"="*60}')
    print(f'Cleanup VLANs 20 / 310 / 601 / untagged / zone grise')
    print(f'{total} VMs  —  mode: {"DRY-RUN" if dry_run else "EXÉCUTION RÉELLE"}')
    print(f'{"="*60}\n')

    if not dry_run:
        confirm = input('Confirmer la suppression de toutes ces VMs ? (tapez "oui") : ')
        if confirm.strip().lower() != 'oui':
            print('Annulé.')
            sys.exit(0)

    # Phase 1 — kill PIDs sur chaque nœud (running only)
    print('--- Phase 1 : kill -9 processus QEMU (running VMs) ---')
    by_node = {}
    for vmid, (node, name, cat) in RUNNING.items():
        by_node.setdefault(node, []).append(vmid)

    for node in sorted(by_node):
        vmids = by_node[node]
        ip = NODE_IPS[node]
        kill_cmds = ' '.join(
            f'kill -9 $(cat /var/run/qemu-server/{v}.pid 2>/dev/null) 2>/dev/null;'
            for v in vmids
        )
        rc = ssh_cmd(ip, kill_cmds, dry_run)
        status = '✓' if rc == 0 else f'✗ (rc={rc})'
        print(f'  {node} {status} : {vmids}')

    if not dry_run:
        print('  Attente 12s (expiry watchers RBD)...')
        time.sleep(12)

    # Phase 2 — destroy stoppées
    print('\n--- Phase 2 : destroy VMs déjà stoppées ---')
    errors = []
    for vmid, (node, name, cat) in sorted(STOPPED.items()):
        print(f'  {vmid:7d} {name[:40]:40s} ({cat})')
        rc = pvesh_delete(node, vmid, dry_run)
        if rc != 0:
            errors.append(vmid)
        else:
            print(f'           ✓ supprimée')

    # Phase 3 — destroy ex-running
    print('\n--- Phase 3 : destroy VMs ex-running ---')
    for vmid, (node, name, cat) in sorted(RUNNING.items()):
        print(f'  {vmid:7d} {name[:40]:40s} ({cat})')
        rc = pvesh_delete(node, vmid, dry_run)
        if rc != 0:
            errors.append(vmid)
        else:
            print(f'           ✓ supprimée')

    print(f'\n{"="*60}')
    if errors:
        print(f'⚠️  Erreurs sur {len(errors)} VMs : {errors}')
        print('    Pour les disques RBD orphelins : rbd ls RBD_pool-metadata | grep <vmid>')
        print('    puis : rbd rm RBD_pool-metadata/vm-<vmid>-disk-0')
    else:
        print(f'✅  {total} VMs supprimées sans erreur.')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
