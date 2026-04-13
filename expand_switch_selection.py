#!/usr/bin/env python3
"""Generate extra pnp_server_day0.devices entries from switch inventory CSV.

This script reads:
- the existing host_vars YAML file to reuse one device as template
- the CSV inventory file to build device entries (name/mac/serial/hostname/description)

It prints only missing devices as a YAML snippet to stdout.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_CSV = "LanETS - Inventaire Switch.csv"
DEFAULT_HOST_VARS = "inventory/infra/host_vars/pnp01.mgmt.etsmtl.club.yaml"


@dataclass
class TemplateDevice:
    admin_password_block: list[str]
    mgmt_mask: str | None
    mgmt_gateway: str | None


@dataclass
class TemplateProfile:
    admin_password_block: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate YAML devices entries from LanETS switch inventory",
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help=f"Path to CSV inventory (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--host-vars",
        default=DEFAULT_HOST_VARS,
        help=f"Path to host_vars YAML (default: {DEFAULT_HOST_VARS})",
    )
    parser.add_argument(
        "--template-name",
        default="sw061",
        help="Existing device name used as template in YAML (default: sw061)",
    )
    parser.add_argument(
        "--template-profile-name",
        default="sw01",
        help="Existing profile name used as template in YAML (default: sw01)",
    )
    parser.add_argument(
        "--domain",
        default="etsmtl.club",
        help="Domain used to build hostnames (default: etsmtl.club)",
    )
    parser.add_argument(
        "--include-prefix",
        default="SW",
        help=(
            "Identifier prefix to include (case-insensitive). "
            "Use empty string to include all rows. Default: SW"
        ),
    )
    parser.add_argument(
        "--ip-offset",
        type=int,
        default=None,
        help=(
            "If Addresse IP is empty, infer management IP as 10.0.21.(N + offset) "
            "using digits from identifier. Example: SW061 + offset 20 => 10.0.21.81"
        ),
    )
    parser.add_argument(
        "--dry-run-existing",
        action="store_true",
        help="Also print devices already present in YAML (normally filtered out)",
    )
    parser.add_argument(
        "--emit",
        choices=["devices", "profiles", "both"],
        default="both",
        help="Which sections to emit (default: both)",
    )
    parser.add_argument(
        "--device-profile",
        default=None,
        help=(
            "Force the same profile value for all generated devices "
            "(example: default)."
        ),
    )
    return parser.parse_args()


def read_text(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SystemExit(f"Cannot read {path}: {exc}") from exc


def parse_section_blocks(yaml_lines: list[str], section_name: str) -> list[list[str]]:
    devices_index = None
    for i, line in enumerate(yaml_lines):
        if re.match(rf"^\s{{2}}{re.escape(section_name)}:\s*$", line):
            devices_index = i
            break
    if devices_index is None:
        raise SystemExit(f"Could not find '  {section_name}:' section in host_vars file")

    blocks: list[list[str]] = []
    current: list[str] = []
    in_devices = False

    for line in yaml_lines[devices_index + 1 :]:
        if re.match(r"^\s{2}\S", line):
            break

        if re.match(r"^\s{4}-\s", line):
            in_devices = True
            if current:
                blocks.append(current)
            current = [line]
            continue

        if in_devices:
            if line.strip() == "" and not current:
                continue
            current.append(line)

    if current:
        blocks.append(current)

    return blocks


def extract_name(block: list[str]) -> str | None:
    for line in block:
        match = re.match(r"^\s{6}name:\s*(\S+)\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def extract_field(block: list[str], field_name: str) -> str | None:
    for line in block:
        match = re.match(rf"^\s{{6}}{re.escape(field_name)}:\s*(\S+)\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def extract_template(block: list[str]) -> TemplateDevice:
    admin_start = None
    admin_end = None

    for i, line in enumerate(block):
        if re.match(r"^\s{6}admin_password:\s*!vault\s*\|\s*$", line):
            admin_start = i
            j = i + 1
            while j < len(block) and re.match(r"^\s{10,}\S", block[j]):
                j += 1
            admin_end = j
            break

    if admin_start is None or admin_end is None:
        raise SystemExit("Template device does not contain a valid admin_password vault block")

    mgmt_mask = None
    mgmt_gateway = None

    for line in block:
        mask_match = re.match(r"^\s{6}mgmt_svi_ip_mask:\s*(\S+)\s*$", line)
        if mask_match:
            mgmt_mask = mask_match.group(1)
        gw_match = re.match(r"^\s{6}mgmt_default_gateway:\s*(\S+)\s*$", line)
        if gw_match:
            mgmt_gateway = gw_match.group(1)

    return TemplateDevice(
        admin_password_block=block[admin_start:admin_end],
        mgmt_mask=mgmt_mask,
        mgmt_gateway=mgmt_gateway,
    )


def extract_profile_template(block: list[str]) -> TemplateProfile:
    admin_start = None
    admin_end = None

    for i, line in enumerate(block):
        if re.match(r"^\s{6}admin_password:\s*!vault\s*\|\s*$", line):
            admin_start = i
            j = i + 1
            while j < len(block) and re.match(r"^\s{10,}\S", block[j]):
                j += 1
            admin_end = j
            break

    if admin_start is None or admin_end is None:
        raise SystemExit("Template profile does not contain a valid admin_password vault block")

    return TemplateProfile(admin_password_block=block[admin_start:admin_end])


def normalize_identifier(raw_id: str) -> str:
    return raw_id.strip().lower()


def build_description(identifier: str) -> str:
    upper = identifier.upper()
    if upper.startswith("SWM"):
        suffix = upper[3:]
        return f"Switch M{suffix}"
    if upper.startswith("SW"):
        suffix = upper[2:]
        return f"Switch {suffix}"
    return f"Switch {upper}"


def infer_ip(identifier: str, offset: int | None) -> str | None:
    if offset is None:
        return None
    digits = "".join(ch for ch in identifier if ch.isdigit())
    if not digits:
        return None
    return f"10.0.21.{int(digits) + offset}"


def read_inventory_rows(csv_path: Path) -> Iterable[dict[str, str]]:
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            for row in reader:
                if not row:
                    continue
                yield {k: (v or "").strip() for k, v in row.items() if k is not None}
    except OSError as exc:
        raise SystemExit(f"Cannot read CSV {csv_path}: {exc}") from exc


def generate_block(
    identifier: str,
    mac: str,
    serial: str,
    domain: str,
    template: TemplateDevice,
    ip_value: str | None,
    device_profile: str | None,
) -> list[str]:
    host = normalize_identifier(identifier)
    profile = (device_profile or host).strip().lower()
    lines = [
        f"    - profile: {profile}",
        f"      name: {host}",
        f"      hostname: {host}.{domain}",
    ]
    lines.extend(template.admin_password_block)
    lines.extend(
        [
            f"      description: {build_description(identifier)}",
            f"      mac: {mac.upper()}",
            f"      serial: {serial.upper()}",
        ]
    )

    if ip_value:
        lines.append(f"      mgmt_svi_ip_address: {ip_value}")
        if template.mgmt_mask:
            lines.append(f"      mgmt_svi_ip_mask: {template.mgmt_mask}")
        if template.mgmt_gateway:
            lines.append(f"      mgmt_default_gateway: {template.mgmt_gateway}")

    return lines


def generate_profile_block(
    identifier: str,
    domain: str,
    template: TemplateProfile,
) -> list[str]:
    name = normalize_identifier(identifier)
    lines = [
        f"    - name: {name}",
        f"      hostname: {name}.{domain}",
    ]
    lines.extend(template.admin_password_block)
    lines.append(f"      description: {build_description(identifier)}")
    return lines


def main() -> int:
    args = parse_args()

    csv_path = Path(args.csv)
    host_vars_path = Path(args.host_vars)

    yaml_lines = read_text(host_vars_path)
    profile_blocks = parse_section_blocks(yaml_lines, "profiles")
    device_blocks = parse_section_blocks(yaml_lines, "devices")

    existing_profile_names = set()
    existing_device_names = set()
    template_device_block = None
    template_profile_block = None

    for block in profile_blocks:
        name = extract_name(block)
        if name:
            existing_profile_names.add(name)
        if name == args.template_profile_name:
            template_profile_block = block

    for block in device_blocks:
        name = extract_name(block)
        if name:
            existing_device_names.add(name)
        if name == args.template_name:
            template_device_block = block

    if template_device_block is None:
        raise SystemExit(
            f"Template device '{args.template_name}' not found in {host_vars_path}"
        )

    if template_profile_block is None:
        if profile_blocks:
            template_profile_block = profile_blocks[0]
            fallback_name = extract_name(template_profile_block) or "<unknown>"
            print(
                (
                    "# Warning: template profile "
                    f"'{args.template_profile_name}' not found, using '{fallback_name}'"
                ),
                file=sys.stderr,
            )
        else:
            raise SystemExit(
                f"Template profile '{args.template_profile_name}' not found in {host_vars_path}"
            )

    device_template = extract_template(template_device_block)
    profile_template = extract_profile_template(template_profile_block)

    include_prefix = args.include_prefix.strip().upper()
    emit_profiles = args.emit in ("profiles", "both")
    emit_devices = args.emit in ("devices", "both")

    generated_profiles: list[list[str]] = []
    generated_devices: list[list[str]] = []

    for row in read_inventory_rows(csv_path):
        identifier = row.get("Identifiant", "")
        if not identifier:
            continue

        if include_prefix and not identifier.upper().startswith(include_prefix):
            continue

        name = normalize_identifier(identifier)
        mac = row.get("Formatted MAC", "")
        serial = row.get("No Série", "")
        ip_from_csv = row.get("Addresse IP", "")

        if emit_profiles and (args.dry_run_existing or name not in existing_profile_names):
            generated_profiles.append(
                generate_profile_block(
                    identifier=identifier,
                    domain=args.domain,
                    template=profile_template,
                )
            )

        if emit_devices:
            if not args.dry_run_existing and name in existing_device_names:
                continue

            if not mac or not serial:
                print(f"# Skipped {identifier}: missing MAC or serial", file=sys.stderr)
                continue

            ip_value = ip_from_csv or infer_ip(identifier, args.ip_offset)

            generated_devices.append(
                generate_block(
                    identifier=identifier,
                    mac=mac,
                    serial=serial,
                    domain=args.domain,
                    template=device_template,
                    ip_value=ip_value,
                    device_profile=args.device_profile,
                )
            )

    emitted = 0

    if emit_profiles and generated_profiles:
        print("  profiles:")
        for block_lines in generated_profiles:
            print("\n".join(block_lines))
            print()
            emitted += 1

    if emit_devices and generated_devices:
        print("  devices:")
        for block_lines in generated_devices:
            print("\n".join(block_lines))
            print()
            emitted += 1

    if emitted == 0:
        print("# No new entries generated", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
