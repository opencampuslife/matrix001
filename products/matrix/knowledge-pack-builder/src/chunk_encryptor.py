"""
Chunk Encryptor — receives plaintext knowledge chunks and encrypts them
with AES-256-GCM. Each package gets a unique DEK and nonce.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


NONCE_SIZE = 12
TAG_SIZE = 16


@dataclass
class EncryptedPackage:
    package_id: str
    ciphertext: bytes
    nonce: bytes
    dek: bytes
    aad: bytes
    role_tags: list[str]
    source_version: str = ""


class ChunkEncryptor:
    def __init__(self):
        self.aesgcm = AESGCM

    def generate_dek(self) -> bytes:
        return os.urandom(32)

    def build_aad(self, package_id: str, source_version: str,
                  roles: list[str], policy_hash: str) -> bytes:
        aad_data = json.dumps({
            "package_id": package_id,
            "source_version": source_version,
            "roles": sorted(roles),
            "policy_hash": policy_hash,
        }, sort_keys=True)
        return aad_data.encode()

    def encrypt_chunks(self, chunks: list[dict], package_id: str,
                       role_tags: list[str],
                       source_version: str = "",
                       policy_hash: str = "",
                       dek: Optional[bytes] = None) -> EncryptedPackage:
        if dek is None:
            dek = self.generate_dek()

        aad = self.build_aad(package_id, source_version, role_tags, policy_hash)
        aes = self.aesgcm(dek)
        nonce = os.urandom(NONCE_SIZE)

        plaintext = json.dumps(chunks, ensure_ascii=False).encode()
        ciphertext = aes.encrypt(nonce, plaintext, aad)

        return EncryptedPackage(
            package_id=package_id,
            ciphertext=ciphertext,
            nonce=nonce,
            dek=dek,
            aad=aad,
            role_tags=role_tags,
            source_version=source_version,
        )

    def get_encrypted_blob(self, pkg: EncryptedPackage) -> bytes:
        return pkg.nonce + pkg.ciphertext
