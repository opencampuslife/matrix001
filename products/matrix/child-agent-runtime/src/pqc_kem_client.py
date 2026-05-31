"""
PQC KEM Client — handles ML-KEM-768 key encapsulation for decrypting
knowledge pack Data Encryption Keys (DEK) from the Mother Agent.

Each knowledge package has a DEK encrypted with the child agent's ML-KEM public key.
"""

import hashlib
import json
from typing import Optional

try:
    import oqs
    _HAS_LIBOQS = True
except ImportError:
    _HAS_LIBOQS = False


class PQCKEMClient:
    def __init__(self, kem_secret_key: str):
        self.kem_secret_key = kem_secret_key

    def decapsulate_dek(self, encrypted_dek: str) -> Optional[bytes]:
        if _HAS_LIBOQS:
            try:
                ciphertext = bytes.fromhex(encrypted_dek)
                with oqs.KeyEncapsulation("ML-KEM-768", self.kem_secret_key) as kem:
                    shared_secret = kem.decap_secret(ciphertext)
                    return shared_secret[:32]
            except Exception:
                return None
        return _stub_decapsulate(encrypted_dek)

    def derive_package_key(self, shared_secret: bytes, package_id: str, version: str) -> bytes:
        import hmac
        info = json.dumps({"package_id": package_id, "version": version}).encode()
        return hmac.digest(shared_secret, info, "sha384")[:32]

    @staticmethod
    def encapsulate_for_agent(kem_public_key: str) -> tuple[str, str]:
        if _HAS_LIBOQS:
            with oqs.KeyEncapsulation("ML-KEM-768") as kem:
                ciphertext, shared_secret = kem.encap_secret(kem_public_key)
                return ciphertext.hex(), shared_secret[:32].hex()
        return _stub_encapsulate(kem_public_key)


def _stub_decapsulate(encrypted_dek: str) -> bytes:
    return hashlib.sha384(encrypted_dek.encode()).digest()[:32]


def _stub_encapsulate(kem_public_key: str) -> tuple[str, str]:
    import secrets
    ct = secrets.token_hex(64)
    ss = secrets.token_hex(32)
    return ct, ss
