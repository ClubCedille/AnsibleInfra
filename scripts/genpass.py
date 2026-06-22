#!/usr/bin/env python3
"""
Génère un CSV de mots de passe pour les équipes CTF.
Usage: python genpass.py [--teams 35] [--length 8] [--output data/raw/passwords.csv] [challenge_dir]
"""

import argparse
import csv
import difflib
import io
import secrets
import string
import sys
from pathlib import Path

from challenge_name import format_challenge_name


def generate_password(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_id() -> str:
    return secrets.token_hex(16)


def strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    escaped = False

    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char in ("'", '"'):
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue

        if char == "#" and quote is None:
            return value[:index]

    return value


def unquote_yaml_string(value: str) -> str:
    value = strip_yaml_comment(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_challenge_yml(compose_path: Path) -> dict:
    for name in ("challenge.yml", "challenge.yaml"):
        challenge_yml = compose_path.parent / name
        if challenge_yml.exists():
            break
    else:
        return {}
    try:
        import yaml
        with challenge_yml.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_individual_instance(challenge_data: dict) -> bool:
    try:
        return bool(challenge_data["extra"]["deployment_info"]["individual_instance"])
    except (KeyError, TypeError):
        return False


def load_compose_name(compose_path: Path) -> str | None:
    try:
        import yaml
    except ModuleNotFoundError:
        with compose_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if line[0].isspace() or ":" not in line:
                    continue

                key, value = line.split(":", 1)
                if key.strip() == "name":
                    compose_name = unquote_yaml_string(value)
                    return compose_name or None

        return None

    with compose_path.open("r", encoding="utf-8") as handle:
        compose = yaml.safe_load(handle)

    if not isinstance(compose, dict):
        return None

    compose_name = compose.get("name")
    if not isinstance(compose_name, str):
        return None

    return compose_name


def challenge_fields(challenge_dir: str | None) -> list[str]:
    if challenge_dir is None:
        return []

    root = Path(challenge_dir)
    if not root.is_dir():
        print(
            f"Erreur: le répertoire de challenges n'existe pas: {root}", file=sys.stderr
        )
        sys.exit(1)

    fields: list[str] = []
    seen: set[str] = set()

    compose_paths: set[Path] = set()
    for pattern in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        compose_paths.update(root.rglob(pattern))

    for compose_path in sorted(compose_paths):
        challenge_data = load_challenge_yml(compose_path)
        if not is_individual_instance(challenge_data):
            continue

        raw_name = challenge_data.get("name") if challenge_data else None
        if not raw_name:
            raw_name = compose_path.parent.name
        field_name = format_challenge_name(raw_name)
        if not field_name:
            continue

        if field_name in seen:
            print(
                f"Erreur: champ de challenge dupliqué après nettoyage: {field_name}",
                file=sys.stderr,
            )
            sys.exit(1)

        seen.add(field_name)
        fields.append(field_name)

    return fields


def load_existing(output_path: str) -> tuple[list[str], dict[int, dict]]:
    path = Path(output_path)
    if not path.exists():
        return [], {}

    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = {int(row["team"]): dict(row) for row in reader}

    return fieldnames, rows


def main():
    parser = argparse.ArgumentParser(
        description="Génère des mots de passe pour les équipes CTF"
    )
    parser.add_argument(
        "challenge_dir",
        help="Répertoire contenant les docker-compose.yml des challenges",
    )
    parser.add_argument(
        "--teams", type=int, default=35, help="Nombre d'équipes (défaut: 35)"
    )
    parser.add_argument(
        "--length", type=int, default=8, help="Longueur du mot de passe (défaut: 8)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/passwords.csv",
        help="Fichier CSV de sortie",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Supprimer du CSV les challenges absents du repo externe (ou sans individual_instance)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche le diff du CSV sans écrire le fichier.",
    )
    args = parser.parse_args()

    if args.teams < 1:
        print("Erreur: le nombre d'équipes doit être >= 1", file=sys.stderr)
        sys.exit(1)
    if args.length < 4:
        print("Erreur: longueur minimale de 4 caractères", file=sys.stderr)
        sys.exit(1)

    existing_fieldnames, existing_rows = load_existing(args.output)
    existing_challenge_fields = [
        f for f in existing_fieldnames if f not in ("team", "vmid", "password")
    ]

    all_challenge_fields = challenge_fields(args.challenge_dir)
    current_challenge_set = set(all_challenge_fields)

    pruned_fields: list[str] = []
    if args.prune:
        pruned_fields = [f for f in existing_challenge_fields if f not in current_challenge_set]
        existing_challenge_fields = [f for f in existing_challenge_fields if f in current_challenge_set]
        if pruned_fields:
            print(f"[!] Challenges supprimés (--prune): {', '.join(pruned_fields)}")

    existing_challenge_set = set(existing_challenge_fields)
    new_challenge_fields = [f for f in all_challenge_fields if f not in existing_challenge_set]

    fieldnames = ["team", "vmid", "password", *existing_challenge_fields, *new_challenge_fields]

    rows = []
    new_teams = 0

    for team in range(1, args.teams + 1):
        if team in existing_rows:
            row = existing_rows[team]
            for field in pruned_fields:
                row.pop(field, None)
            for field in new_challenge_fields:
                row[field] = generate_id()
        else:
            row = {
                "team": team,
                "vmid": team,
                "password": generate_password(args.length),
                **{field: generate_id() for field in existing_challenge_fields},
                **{field: generate_id() for field in new_challenge_fields},
            }
            new_teams += 1
        rows.append(row)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    new_content = buf.getvalue()

    output_path = Path(args.output)
    if args.dry_run:
        old_lines = output_path.read_text(encoding="utf-8").splitlines(keepends=True) if output_path.exists() else []
        diff = list(difflib.unified_diff(
            old_lines, new_content.splitlines(keepends=True),
            fromfile=f"{output_path} (current)",
            tofile=f"{output_path} (new)",
        ))
        print(f"[DRY RUN] {output_path}")
        print("".join(diff) if diff else "  (no changes)")
    else:
        output_path.write_text(new_content, newline="", encoding="utf-8")

    summary_parts = []
    if new_teams:
        summary_parts.append(f"{new_teams} nouvelles équipes")
    if new_challenge_fields:
        summary_parts.append(f"{len(new_challenge_fields)} nouveaux challenges ({', '.join(new_challenge_fields)})")
    if pruned_fields:
        summary_parts.append(f"{len(pruned_fields)} challenges purgés ({', '.join(pruned_fields)})")
    if not summary_parts:
        summary_parts.append("aucun changement")

    label = "[DRY RUN] serait mis à jour" if args.dry_run else "mis à jour"
    print(f"[+] {args.output} {label} — {', '.join(summary_parts)}")


if __name__ == "__main__":
    main()
