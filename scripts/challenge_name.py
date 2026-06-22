"""Shared utility: format raw challenge names into valid Ansible group identifiers.

Rules applied in order:
  1. x/y fractions → keep only x  (e.g. "(1/6)" → "1", "3/8" → "3")
  2. Spaces and hyphens → underscore
  3. Strip remaining invalid chars  (keep [A-Za-z0-9_])
  4. Collapse consecutive underscores
  5. Strip leading/trailing underscores
  6. Prefix with "c" if the result starts with a digit (Ansible requires [A-Za-z_])
"""

import re
import unicodedata


def format_challenge_name(name: str) -> str:
    # Transliterate accented chars (é→e, ü→u, etc.) before stripping
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')
    # x/y → x  (handles "(1/6)", "1/6", "3 / 8", etc.)
    name = re.sub(r'(\d+)\s*/\s*\d+', r'\1', name)
    # Spaces and hyphens → underscore
    name = re.sub(r'[\s\-]+', '_', name)
    # Remove anything not alphanumeric or underscore
    name = re.sub(r'[^A-Za-z0-9_]', '', name)
    # Collapse runs of underscores
    name = re.sub(r'_+', '_', name)
    # Strip leading/trailing underscores
    name = name.strip('_')
    # Ansible group names must not start with a digit
    if name and name[0].isdigit():
        name = 'c' + name
    return name
