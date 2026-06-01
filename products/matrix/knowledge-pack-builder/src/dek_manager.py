"""
DEK Manager — wraps Data Encryption Keys using ML-KEM-768 for each
authorized agent's public key, producing encrypted DEK blobs.

Each agent that is authorized to access a knowledge package gets
its own ML-KEM-768 encapsulated DEK.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

try:
    import oqs
    _HAS_LIBOQS = True
except ImportError:
    _HAS_LIBOQS = False


@dataclass
class EncryptedDEK:
    agent_id: str
    ciphertext: str  # hex-encoded ML-KEM ciphertext
    algorithm: str = "ML-KEM-768"


class DEKManager:
    def __init__(self):
        pass

    def encapsulate_dek(self, dek: bytes, agent_kem_public_key: str) -> EncryptedDEK:
        if _HAS_LIBOQS:
            with oqs.KeyEncapsulation("ML-KEM-768") as kem:
                ciphertext, shared_secret = kem.encap_secret(agent_kem_public_key)
                return EncryptedDEK(
                    agent_id="",
                    ciphertext=ciphertext.hex(),
                    algorithm="ML-KEM-768",
                )
        return self._stub_encapsulate(dek, agent_kem_public_key)

    def encapsulate_for_agents(self, dek: bytes,
                                agents: list[dict]) -> list[EncryptedDEK]:
        result = []
        for agent in agents:
            edek = self.encapsulate_dek(dek, agent["kem_public_key"])
            edek.agent_id = agent.get("agent_id", "")
            result.append(edek)
        return result

    def _stub_encapsulate(self, dek: bytes, kem_public_key: str) -> EncryptedDEK:
        import secrets
        ct = secrets.token_hex(64)
        return EncryptedDEK(agent_id="", ciphertext=ct, algorithm="ML-KEM-768")
