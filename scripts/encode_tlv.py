#!/usr/bin/env python3
"""
encode_tlv.py — Encode un flag en TLV hex pour l'option 43 DHCP (Kea)

Usage:
    python3 encode_tlv.py "FLAG{leflag}"
    python3 encode_tlv.py "FLAG{leflag}" --sub-option 1

Format TLV :
    sub-option type  : 1 byte
    length           : 1 byte
    value            : N bytes (ASCII)
    end marker       : 0xFF

Sortie : hex string à coller dans flags.yml (flag_03_tlv_hex ou flag_06_bonus_tlv_hex)
"""

import sys
import argparse


def encode_tlv(flag: str, sub_option: int = 1) -> str:
    value = flag.encode("ascii")
    length = len(value)

    if length > 255:
        raise ValueError(f"Flag trop long ({length} bytes, max 255)")

    tlv = bytes([sub_option, length]) + value + bytes([0xFF])
    return tlv.hex()


def main():
    parser = argparse.ArgumentParser(description="Encode un flag en TLV hex pour l'option 43 DHCP")
    parser.add_argument("flag", help="Le flag à encoder, ex: FLAG{leflag}")
    parser.add_argument("--sub-option", type=int, default=1,
                        help="Numéro de sub-option TLV (défaut: 1)")
    args = parser.parse_args()

    hex_output = encode_tlv(args.flag, args.sub_option)

    print(f"Flag      : {args.flag}")
    print(f"Sub-option: {args.sub_option}")
    print(f"Longueur  : {len(args.flag.encode('ascii'))} bytes")
    print(f"TLV hex   : {hex_output}")
    print()
    print("À coller dans flags.yml :")
    print(f'  flag_03_tlv_hex: "{hex_output}"')


if __name__ == "__main__":
    main()