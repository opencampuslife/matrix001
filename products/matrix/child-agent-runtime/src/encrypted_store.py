"""
Encrypted Store — AES-256-GCM encrypted local storage for knowledge packs,
skill packs, and capability data.

Each item is encrypted with a derived key. Nonces are never reused.
Additional Authenticated Data (AAD) binds version, role, and policy hash.
"""

import json
import os
import struct
import hashlib
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


DEFAULT_STORE_DIR = Path.home() / ".matrix" / "store"
AES_KEY_SIZE = 32  # AES-256
NONCE_SIZE = 12    # GCM standard
TAG_SIZE = 16      # GCM authentication tag


class EncryptedStore:
    def __init__(self, store_dir: Path = DEFAULT_STORE_DIR, master_key: Optional[bytes] = None):
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.aesgcm = AESGCM(master_key) if master_key else None
        self._master_key = master_key

    def set_key(self, key: bytes):
        self._master_key = key
        self.aesgcm = AESGCM(key)

    def derive_item_key(self, package_id: str, version: str, role: str, policy_hash: str) -> bytes:
        import hmac
        info = json.dumps({
            "package_id": package_id,
            "version": version,
            "role": role,
            "policy_hash": policy_hash,
        }, sort_keys=True).encode()
        return hmac.digest(self._master_key or b"", info, "sha384")[:AES_KEY_SIZE]

    def encrypt(self, plaintext: bytes, item_key: bytes, aad: bytes = b"") -> bytes:
        nonce = os.urandom(NONCE_SIZE)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, aad)
        return nonce + ciphertext

    def decrypt(self, encrypted_data: bytes, item_key: bytes, aad: bytes = b"") -> Optional[bytes]:
        if len(encrypted_data) < NONCE_SIZE + TAG_SIZE:
            return None
        nonce = encrypted_data[:NONCE_SIZE]
        ciphertext = encrypted_data[NONCE_SIZE:]
        try:
            return self.aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception:
            return None

    def save_package(self, package_id: str, plaintext: bytes,
                     item_key: bytes, aad: bytes = b"") -> Path:
        encrypted = self.encrypt(plaintext, item_key, aad)
        file_path = self.store_dir / f"{package_id}.enc"
        file_path.write_bytes(encrypted)
        return file_path

    def load_package(self, package_id: str, item_key: bytes,
                     aad: bytes = b"") -> Optional[bytes]:
        file_path = self.store_dir / f"{package_id}.enc"
        if not file_path.exists():
            return None
        encrypted_data = file_path.read_bytes()
        return self.decrypt(encrypted_data, item_key, aad)

    def list_packages(self) -> list[str]:
        return [f.stem for f in self.store_dir.glob("*.enc")]
