#!/usr/bin/env python3
"""
CTF VM Cleanup — suppression par groupes de 15

Doit être exécuté sur un nœud du cluster Proxmox (utilise pvesh/qm).
Copier sur pve01 et lancer depuis là :

  scp scripts/cleanup_ctf_vms.py root@10.0.21.51:/tmp/
  ssh root@10.0.21.51 python3 /tmp/cleanup_ctf_vms.py --list
  ssh root@10.0.21.51 python3 /tmp/cleanup_ctf_vms.py --group 1 --dry-run
  ssh root@10.0.21.51 python3 /tmp/cleanup_ctf_vms.py --group 1

Usage:
  --list          Affiche tous les groupes et leurs VMs
  --group NAME    Exécute le groupe spécifié (1-6, legacy, ou 'all')
  --dry-run       Simule sans toucher aux VMs (défaut si --group sans --execute)
  --execute       Requis pour effectuer les suppressions réelles
"""

import argparse
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# Définition des groupes
# ---------------------------------------------------------------------------
# Format : (vmid, node, status_attendu)
# status_attendu : "running" → stop avant destroy ; "stopped" → destroy direct

GROUPS = {
    "1": {
        "name": "NanoControl-Credentials-1.ctf (VLAN 68)",
        "vms": [
            (2001036, "pve02", "running"),
            (2001037, "pve03", "running"),
            (2001038, "pve04", "running"),
            (2001039, "pve07", "running"),
            (2001040, "pve01", "running"),
            (2001041, "pve02", "running"),
            (2001042, "pve03", "running"),
            (2001043, "pve04", "running"),
            (2001044, "pve07", "running"),
            (2001045, "pve01", "running"),
            (2001046, "pve02", "running"),
            (2001047, "pve03", "running"),
            (2001048, "pve04", "running"),
            (2001049, "pve07", "running"),
            (2001050, "pve01", "running"),
        ],
    },
    "2": {
        "name": "NanoControl-NanoControl-2.ctf (VLAN 68)",
        "vms": [
            (2002036, "pve02", "running"),
            (2002037, "pve03", "running"),
            (2002038, "pve04", "running"),
            (2002039, "pve07", "running"),
            (2002040, "pve01", "running"),
            (2002041, "pve02", "running"),
            (2002042, "pve03", "running"),
            (2002043, "pve04", "running"),
            (2002044, "pve07", "running"),
            (2002045, "pve01", "running"),
            (2002046, "pve02", "running"),
            (2002047, "pve03", "running"),
            (2002048, "pve04", "running"),
            (2002049, "pve07", "running"),
            (2002050, "pve01", "running"),
        ],
    },
    "3": {
        "name": "MITM.ctf (VLAN 68)",
        "vms": [
            (2003036, "pve02", "running"),
            (2003037, "pve03", "running"),
            (2003038, "pve04", "running"),
            (2003039, "pve07", "running"),
            (2003040, "pve01", "running"),
            (2003041, "pve02", "running"),
            (2003042, "pve03", "running"),
            (2003043, "pve04", "running"),
            (2003044, "pve07", "running"),
            (2003045, "pve01", "running"),
            (2003046, "pve02", "running"),
            (2003047, "pve03", "running"),
            (2003048, "pve04", "running"),
            (2003049, "pve07", "running"),
            (2003050, "pve01", "running"),
        ],
    },
    "4": {
        "name": "Acces-Interdit.ctf (VLAN 68)",
        "vms": [
            (2004036, "pve02", "running"),
            (2004037, "pve03", "running"),
            (2004038, "pve04", "running"),
            (2004039, "pve07", "running"),
            (2004040, "pve01", "running"),
            (2004041, "pve02", "running"),
            (2004042, "pve03", "running"),
            (2004043, "pve04", "running"),
            (2004044, "pve07", "running"),
            (2004045, "pve01", "running"),
            (2004046, "pve02", "running"),
            (2004047, "pve03", "running"),
            (2004048, "pve04", "running"),
            (2004049, "pve07", "running"),
            (2004050, "pve01", "running"),
        ],
    },
    "5": {
        "name": "Avis-de-mauvais-temps.ctf (VLAN 68)",
        "vms": [
            (2005036, "pve02", "running"),
            (2005037, "pve03", "running"),
            (2005038, "pve04", "running"),
            (2005039, "pve07", "running"),
            (2005040, "pve01", "running"),
            (2005041, "pve02", "running"),
            (2005042, "pve03", "running"),
            (2005043, "pve04", "running"),
            (2005044, "pve07", "running"),
            (2005045, "pve01", "running"),
            (2005046, "pve02", "running"),
            (2005047, "pve03", "running"),
            (2005048, "pve04", "running"),
            (2005049, "pve07", "running"),
            (2005050, "pve01", "running"),
        ],
    },
    "6": {
        "name": "Camp-Maintenance-Signal-Brut.ctf (VLAN 68)",
        "vms": [
            (2006036, "pve02", "running"),
            (2006037, "pve03", "running"),
            (2006038, "pve04", "running"),
            (2006039, "pve07", "running"),
            (2006040, "pve01", "running"),
            (2006041, "pve02", "running"),
            (2006042, "pve03", "running"),
            (2006043, "pve04", "running"),
            (2006044, "pve07", "running"),
            (2006045, "pve01", "running"),
            (2006046, "pve02", "running"),
            (2006047, "pve03", "running"),
            (2006048, "pve04", "running"),
            (2006049, "pve07", "running"),
            (2006050, "pve01", "running"),
        ],
    },
    "legacy": {
        "name": "VMs stoppées legacy CTF (toutes VLANs)",
        "vms": [
            # dhcp/dns -66/-67/-68 event (remplacés par dhcp01/02.camp, dns01/02.camp)
            (3101, "pve01", "stopped"),   # dhcp01-66-event
            (3102, "pve01", "stopped"),   # dhcp02-66-event
            (3201, "pve01", "stopped"),   # dhcp01-67-event
            (3202, "pve01", "stopped"),   # dhcp02-67-event
            (3301, "pve01", "stopped"),   # dhcp01-68-event
            (3302, "pve01", "stopped"),   # dhcp02-68-event
            (4101, "pve01", "stopped"),   # dns01-66-event
            (4102, "pve01", "stopped"),   # dns02-66-event
            (4201, "pve01", "stopped"),   # dns01-67-event
            (4202, "pve01", "stopped"),   # dns02-67-event
            (4301, "pve01", "stopped"),   # dns01-68-event
            (4302, "pve01", "stopped"),   # dns02-68-event
            # NOTE: trackmania (200001, 200003, 200005, 200006, 801201) et
            # PXE (200007, 200008) sont EXCLUS — conservés intentionnellement.
            # cs01 doublon (VLAN 310, stoppé — doublon de 801101)
            (801100, "pve04", "stopped"), # cs01.event.lanets.ca (tag 310)
            # cs01-cs20 event (édition précédente CTF, tous stoppés)
            (801101, "pve02", "stopped"), # cs01.event.lanets.ca
            (801102, "pve03", "stopped"), # cs02.event.lanets.ca
            (801103, "pve04", "stopped"), # cs03.event.lanets.ca
            (801104, "pve01", "stopped"), # cs04.event.lanets.ca
            (801105, "pve02", "stopped"), # cs05.event.lanets.ca
            (801106, "pve03", "stopped"), # cs06.event.lanets.ca
            (801107, "pve04", "stopped"), # cs07.event.lanets.ca
            (801108, "pve01", "stopped"), # cs08.event.lanets.ca
            (801109, "pve02", "stopped"), # cs09.event.lanets.ca
            (801110, "pve03", "stopped"), # cs10.event.lanets.ca
            (801111, "pve04", "stopped"), # cs11.event.lanets.ca
            (801112, "pve01", "stopped"), # cs12.event.lanets.ca
            (801113, "pve02", "stopped"), # cs13.event.lanets.ca
            (801114, "pve03", "stopped"), # cs14.event.lanets.ca
            (801115, "pve04", "stopped"), # cs15.event.lanets.ca
            (801116, "pve01", "stopped"), # cs16.event.lanets.ca
            (801117, "pve02", "stopped"), # cs17.event.lanets.ca
            (801118, "pve02", "stopped"), # cs18.event.lanets.ca
            (801119, "pve04", "stopped"), # cs19.event.lanets.ca
            (801120, "pve01", "stopped"), # cs20.event.lanets.ca
            # Jeux stoppés (édition précédente) — trackmania exclu (conservé)
            # (801201, "pve01", "stopped"),  # trackmania.event.lanets.ca — CONSERVÉ
            (801202, "pve01", "stopped"), # archipelago.event.lanets.ca
            (801203, "pve01", "stopped"), # minecraft.event.lanets.ca
        ],
    },
}

# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def run(cmd, dry_run=False):
    print(f"  {'[DRY-RUN] ' if dry_run else ''}$ {' '.join(cmd)}")
    if dry_run:
        return 0
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERREUR: {result.stderr.strip()}")
    return result.returncode


def stop_vm(vmid, node, dry_run=False):
    """Force-stop via qm stop (immédiat, équivalent power-off)."""
    return run(
        ["qm", "stop", str(vmid), "--skiplock", "1"],
        dry_run=dry_run,
    )


def wait_stopped(vmid, node, timeout=60):
    """Poll jusqu'à ce que la VM soit stopped ou timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(
            ["pvesh", "get", f"/nodes/{node}/qemu/{vmid}/status/current",
             "--output-format", "json"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            import json
            status = json.loads(r.stdout).get("status", "")
            if status == "stopped":
                return True
        time.sleep(2)
    return False


def destroy_vm(vmid, node, dry_run=False):
    """Détruit la VM et efface les disques non référencés."""
    return run(
        ["pvesh", "delete", f"/nodes/{node}/qemu/{vmid}",
         "--purge", "1", "--destroy-unreferenced-disks", "1"],
        dry_run=dry_run,
    )


def process_group(group_key, dry_run=False):
    group = GROUPS[group_key]
    vms = group["vms"]
    print(f"\n{'='*60}")
    print(f"Groupe {group_key!r} : {group['name']}")
    print(f"{len(vms)} VMs — mode: {'DRY-RUN' if dry_run else 'EXÉCUTION RÉELLE'}")
    print(f"{'='*60}")

    errors = []
    for vmid, node, expected_status in vms:
        print(f"\n  VM {vmid} (nœud {node}, statut attendu: {expected_status})")

        if expected_status == "running":
            rc = stop_vm(vmid, node, dry_run=dry_run)
            if rc != 0:
                errors.append(vmid)
                continue
            if not dry_run:
                print(f"  Attente arrêt VM {vmid}...", end=" ")
                if wait_stopped(vmid, node):
                    print("OK")
                else:
                    print("TIMEOUT — la VM est peut-être encore running !")
                    errors.append(vmid)
                    continue

        rc = destroy_vm(vmid, node, dry_run=dry_run)
        if rc != 0:
            errors.append(vmid)

    print(f"\n  {'='*40}")
    if errors:
        print(f"  ⚠️  Erreurs sur {len(errors)} VMs : {errors}")
    else:
        print(f"  ✅ Groupe {group_key!r} terminé sans erreur.")
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Suppression des VMs CTF par groupes de 15"
    )
    parser.add_argument("--list", action="store_true",
                        help="Affiche les groupes disponibles")
    parser.add_argument("--group", metavar="NAME",
                        help="Groupe à traiter (1-6, legacy, all)")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Simule sans toucher aux VMs (défaut)")
    parser.add_argument("--execute", action="store_true",
                        help="Exécute réellement (désactive --dry-run)")
    args = parser.parse_args()

    dry_run = not args.execute

    if args.list or (not args.group):
        print("\nGroupes disponibles :\n")
        total = 0
        for key in sorted(GROUPS, key=lambda k: (k.isdigit(), k)):
            g = GROUPS[key]
            running = sum(1 for _, _, s in g["vms"] if s == "running")
            stopped = sum(1 for _, _, s in g["vms"] if s == "stopped")
            print(f"  {key:8s}  {len(g['vms']):3d} VMs  "
                  f"({running} running, {stopped} stopped)  {g['name']}")
            total += len(g["vms"])
        print(f"\n  {'TOTAL':8s}  {total:3d} VMs\n")
        print("Utilisation :")
        print("  --group 1          # dry-run groupe 1 (défaut)")
        print("  --group 1 --execute # suppression réelle groupe 1")
        print("  --group all --execute  # supprime tout\n")
        return

    if not dry_run:
        print("\n⚠️  MODE EXÉCUTION RÉELLE — les VMs vont être stoppées et détruites.")
        confirm = input("Confirmer ? (tapez 'oui') : ")
        if confirm.strip().lower() != "oui":
            print("Annulé.")
            sys.exit(0)

    groups_to_run = list(GROUPS.keys()) if args.group == "all" else [args.group]

    for gkey in groups_to_run:
        if gkey not in GROUPS:
            print(f"Groupe inconnu : {gkey!r}. Disponibles : {list(GROUPS.keys())}")
            sys.exit(1)
        process_group(gkey, dry_run=dry_run)


if __name__ == "__main__":
    main()
