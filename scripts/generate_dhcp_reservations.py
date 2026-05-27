#!/usr/bin/env python3
"""Generate Kea DHCP reservations from the switch inventory CSV.

The script reads the repository CSV inventory and emits a YAML list of
reservations suitable for Ansible variable loading.
"""

from __future__ import annotations

import csv
from pathlib import Path


CSV_PATH = Path(__file__).resolve().parents[1] / "data/raw/lanets-inventaire-switch.csv"
IP_PREFIX = "10.120.67."
IP_START = 100


def normalize_mac(raw_value: str) -> str:
    compact = raw_value.strip().replace(":", "").replace("-", "")
    compact = compact.upper()
    if len(compact) != 12:
        raise ValueError(f"Invalid MAC address: {raw_value!r}")
    return ":".join(compact[index : index + 2] for index in range(0, 12, 2))


def main() -> None:
    if not CSV_PATH.exists():
        raise SystemExit(f"Missing CSV inventory: {CSV_PATH}")

    entries = []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for index, row in enumerate(reader):
            identifier = (row.get("Identifiant") or "").strip()
            if not identifier:
                continue
            formatted_mac = (row.get("Formatted MAC") or "").strip()
            raw_mac = (row.get("Addresse MAC") or "").strip()
            mac = formatted_mac or raw_mac
            if not mac:
                continue
            normalized_mac = normalize_mac(mac)
            hostname = identifier.lower()
            ip_address = f"{IP_PREFIX}{IP_START + index}"
            entries.append((hostname, normalized_mac, ip_address))

    for hostname, normalized_mac, ip_address in entries:
        print(f"- hostname: {hostname}")
        print(f'  hw-address: "{normalized_mac}"')
        print(f'  ip-address: "{ip_address}"')


if __name__ == "__main__":
    main()
