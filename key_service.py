
import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_FILE = Path(__file__).resolve().parent / "crypto.key"


def load_or_create_key():
    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()

        if len(key) != 32:
            raise ValueError("Invalid AES key file.")

        return key

    key = AESGCM.generate_key(bit_length=256)

    with open(KEY_FILE, "xb") as file:
        file.write(key)

    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass

    return key
