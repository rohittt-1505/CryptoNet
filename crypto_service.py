
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_message(message, key):
    aes = AESGCM(key)
    nonce = os.urandom(12)

    ciphertext = aes.encrypt(
        nonce,
        message.encode("utf-8"),
        None
    )

    return {
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8")
    }


def decrypt_message(encrypted_data, key):
    aes = AESGCM(key)

    nonce = base64.b64decode(encrypted_data["nonce"])
    ciphertext = base64.b64decode(encrypted_data["ciphertext"])

    plaintext = aes.decrypt(nonce, ciphertext, None)

    return plaintext.decode("utf-8")
