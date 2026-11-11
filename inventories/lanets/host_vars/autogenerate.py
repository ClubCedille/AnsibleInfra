#!/usr/bin/env python3
"""Generate per-VM Proxmox host variables without game-server credentials."""

import argparse
import re
from pathlib import Path


HOST_VARS_DIR = Path(__file__).resolve().parent
INVENTORY_PATH = HOST_VARS_DIR.parent / "hosts.ini"


def render_host_vars(server_id: int) -> str:
    suffix = f"{server_id:02d}"
    return f"""---
vm_id: "8011{suffix}"
vm_name: "cs{suffix}.event.lanets.ca"
vm_proxmox_node: "pve04"

vm_net:
  bridge: "vmbr1"
  vlan: "66"
  ip: "10.110.0.1{suffix}"
  netmask: "16"
  gateway: "10.110.0.1"
  nameservers: "1.1.1.1"
  search_domain: "localdomain"
"""


def update_cs2_inventory(count: int) -> None:
    contents = INVENTORY_PATH.read_text()
    section = "[cs2]\n" + "".join(
        f"cs{server_id:02d}.staging.lanets.ca  ansible_host=10.110.0.1{server_id:02d}\n"
        for server_id in range(1, count + 1)
    ) + "\n"
    pattern = re.compile(r"(?ms)^\[cs2\]\r?\n.*?(?=^\[|\Z)")
    updated, replacements = pattern.subn(section, contents)
    if replacements != 1:
        raise RuntimeError(f"Expected one [cs2] group in {INVENTORY_PATH}")
    INVENTORY_PATH.write_text(updated)


def remove_excess_host_vars(count: int) -> None:
    generated_name = re.compile(r"cs(\d{2})\.staging\.lanets\.ca\.yaml")
    for path in HOST_VARS_DIR.glob("cs??.staging.lanets.ca.yaml"):
        match = generated_name.fullmatch(path.name)
        if match and int(match.group(1)) > count:
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate CS2 VM host_vars without Steam or server credentials."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=20,
        help="number of sequential VM host_vars files to generate (default: 20)",
    )
    args = parser.parse_args()
    if args.count < 1 or args.count > 99:
        parser.error("--count must be between 1 and 99 for the configured IPv4 range")

    for server_id in range(1, args.count + 1):
        suffix = f"{server_id:02d}"
        path = HOST_VARS_DIR / f"cs{suffix}.staging.lanets.ca.yaml"
        path.write_text(render_host_vars(server_id))

    update_cs2_inventory(args.count)
    remove_excess_host_vars(args.count)

    print(
        f"Generated inventory and VM metadata for {args.count} hosts "
        f"in {INVENTORY_PATH.parent}"
    )


if __name__ == "__main__":
    main()
