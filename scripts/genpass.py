#!/usr/bin/env python3
"""
Génère un CSV de mots de passe pour les équipes CTF.
Usage: python genpass.py [--teams 50] [--length 8] [--output data/raw/passwords.csv]
"""

import argparse
import csv
import secrets
import string
import sys


def generate_password(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main():
    parser = argparse.ArgumentParser(description="Génère des mots de passe pour les équipes CTF")
    parser.add_argument("--teams",  type=int, default=50,            help="Nombre d'équipes (défaut: 50)")
    parser.add_argument("--length", type=int, default=8,             help="Longueur du mot de passe (défaut: 8)")
    parser.add_argument("--output", type=str, default="data/raw/passwords.csv", help="Fichier CSV de sortie")
    args = parser.parse_args()

    if args.teams < 1:
        print("Erreur: le nombre d'équipes doit être >= 1", file=sys.stderr)
        sys.exit(1)
    if args.length < 4:
        print("Erreur: longueur minimale de 4 caractères", file=sys.stderr)
        sys.exit(1)

    rows = [
        {"team": team, "vmid": team, "password": generate_password(args.length)}
        for team in range(1, args.teams + 1)
    ]

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["team", "vmid", "password"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] {args.teams} mots de passe générés → {args.output}")


if __name__ == "__main__":
    main()
