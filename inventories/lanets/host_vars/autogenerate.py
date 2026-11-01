import argparse
import getpass
from pathlib import Path

KEYS = [
    "6E1DFF18C7A7F6177A853DFC8695D1A2",
    "81533FF751AECCFBFE4625CE3480EC26",
    "3A5A3077B854EEA69B615A0DCA77D07E",
    "B152ABB19614F1F939FFECBB8DBB7E73",
    "BCE6A1FCD5E6322D20AC856C58FB333D",
    "02BFCC4CE3DDE55722B221AF10FB9D72",
    "D90C4782505F4585D5093E42F7BDC503",
    "AD3EBEEB05F0AC267609F8535249947A",
    "0EAC25EF233A72C2F5B4439C19B8F9AA",
    "CC79C0797B6B0F9D6781B7CA99CB873C",
    "6C9AA295B11806451BA27EAC938AE870",
    "45A0524B9347687020A5917C233CB998",
    "96D373F0A84D8331959FD08729503FE9",
    "89E056422F127674EE2ECEA4784B665A",
    "08566CF65E8BCB46D1341AB696739272",
    "EC72AEEFC6BEB12D16E61C1A4EC5D713",
    "406F946001D608BF2CF3BE04EE6161F6",
    "F732F304354EA52E20A97794CEE26CB6",
    "D7941B3A2CD6FBC0B8EA79CF6A579433",
    "E09B6A62B3B8989A67480CE49B2C5A79",
]

MACS = [
    "BC:24:11:FE:6D:A3",
    "BC:24:11:2B:C5:27",
    "BC:24:11:ED:A7:BC",
    "BC:24:11:03:44:6B",
]


def encrypt_string(plaintext: str, password: str) -> str:
    """Encrypts a string using Ansible Vault.

    Returns the formatted vault text.
    """
    from ansible.constants import DEFAULT_VAULT_IDENTITY_LIST
    from ansible.parsing.vault import VaultLib, VaultSecret

    # 1. Prepare the vault secret and configure the VaultLib engine
    secret = VaultSecret(password.encode("utf-8"))
    vault = VaultLib([(DEFAULT_VAULT_IDENTITY_LIST, secret)])

    # 2. Encrypt the plaintext string (must be passed as bytes)
    encrypted_bytes = vault.encrypt(plaintext.encode("utf-8"))

    # 3. Decode the result back to a standard python string
    return encrypted_bytes.decode("utf-8")


def write_to_file(serverid, content):
    output_path = Path(__file__).resolve().parent / f"cs{serverid}.staging.lanets.ca.yaml"
    output_path.write_text(content, encoding="utf-8")


def read_existing_vault_token(serverid):
    source_path = Path(__file__).resolve().parent / f"cs{serverid}.staging.lanets.ca.yaml"
    token_lines = []
    in_token_block = False
    for line in source_path.read_text(encoding="utf-8").splitlines():
        if line == "cs2_steam_token: !vault |":
            in_token_block = True
            continue
        if in_token_block:
            if line.startswith(" ") and line.strip():
                token_lines.append(line.strip())
            else:
                break
    if not token_lines:
        raise ValueError(f"No vaulted Steam token found in {source_path.name}")
    return "\n".join(token_lines)


def generate_yaml(serverid, encrypted_key, mac):
    ansible_vault_encoded_key = encrypted_key.replace('\n', '\n          ')

    yaml_content = f"""---
cs2_steam_token: !vault |
          {ansible_vault_encoded_key}
cs2_hostname: "cs{serverid}.lanets.ca"

vm_id: "8011{serverid}"
vm_name: "cs{serverid}.event.lanets.ca"
vm_proxmox_node: "pve04"

vm_net:
  mac: "{mac}"
  bridge: "vmbr1" # Management bridge is vmbr0; trunk bridge is vmbr1
  vlan: "66"
  ip: "10.110.0.1{serverid}"
  netmask: "16"
  gateway: "10.110.0.1"
  nameservers: "1.1.1.1"
  search_domain: "localdomain"
"""
    return yaml_content


def main():
    parser = argparse.ArgumentParser(description="Generate CS2 VM host-vars files.")
    parser.add_argument(
        "--count",
        type=int,
        default=4,
        help="number of VMs to generate (default: 4)",
    )
    parser.add_argument(
        "--reuse-existing-vault",
        action="store_true",
        help="reuse each existing encrypted Steam token without decrypting it",
    )
    args = parser.parse_args()
    maximum_count = min(len(KEYS), len(MACS))
    if args.count < 1 or args.count > maximum_count:
        parser.error(f"--count must be between 1 and {maximum_count}")

    vault_password = None
    if not args.reuse_existing_vault:
        vault_password = getpass.getpass("Enter vault password: ")

    for index in range(args.count):
        server_id = f"{index + 1:02d}"
        encrypted_key = (
            read_existing_vault_token(server_id)
            if args.reuse_existing_vault
            else encrypt_string(KEYS[index], vault_password)
        )
        yaml_content = generate_yaml(server_id, encrypted_key, MACS[index])
        write_to_file(server_id, yaml_content)


if __name__ == "__main__":
    main()
