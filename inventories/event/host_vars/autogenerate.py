from ansible.constants import DEFAULT_VAULT_IDENTITY_LIST
from ansible.parsing.vault import VaultLib, VaultSecret

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


def encrypt_string(plaintext: str, password: str) -> str:
    """Encrypts a string using Ansible Vault.

    Returns the formatted vault text.
    """
    # 1. Prepare the vault secret and configure the VaultLib engine
    secret = VaultSecret(password.encode("utf-8"))
    vault = VaultLib([(DEFAULT_VAULT_IDENTITY_LIST, secret)])

    # 2. Encrypt the plaintext string (must be passed as bytes)
    encrypted_bytes = vault.encrypt(plaintext.encode("utf-8"))

    # 3. Decode the result back to a standard python string
    return encrypted_bytes.decode("utf-8")


def write_to_file(serverid, content):
    with open(f"./cs{serverid}.staging.lanets.ca.yaml", "w") as file:
        file.write(content)


def generate_yaml(serverid, key):
    ansible_vault_encoded_key = encrypt_string(
        key, vault_key
    ).replace('\n', '\n          ')  # Indent the vault content for YAML formatting

    yaml_content = f"""---
cs2_steam_token: !vault |
          {ansible_vault_encoded_key}
cs2_hostname: "cs{serverid}.lanets.ca"

vm_id: "8011{serverid}"
vm_name: "cs{serverid}.event.lanets.ca"
vm_proxmox_node: "pve04"

vm_net:
  bridge: "vmbr1" # Management bridge is vmbr0; trunk bridge is vmbr1
  vlan: "310"
  ip: "10.110.0.1{serverid}"
  netmask: "16"
  gateway: "10.110.0.1"
  nameservers: "1.1.1.1"
  search_domain: "localdomain"
"""
    return yaml_content


vault_key = input("Enter vault password: ")
for i, key in enumerate(KEYS, start=1):
    server_id = f"{i:02d}"  # Format server ID with leading zero if less than 10
    yaml_content = generate_yaml(server_id, key)
    write_to_file(server_id, yaml_content)
