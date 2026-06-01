"""
Identity Manager — manages the agent's PQC key pairs, local DID, and device attestation.

Uses liboqs-python for ML-KEM-768 key encapsulation and ML-DSA-65 digital signatures.
Falls back to stub implementations when liboqs is not available.
"""

import json
import os
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import oqs
    _HAS_LIBOQS = True
except ImportError:
    _HAS_LIBOQS = False


DEFAULT_KEY_DIR = Path.home() / ".matrix" / "keys"


@dataclass
class AgentIdentity:
    agent_id: str
    agent_type: str = "child"
    parent_id: str = ""
    kem_public_key: str = ""
    signing_public_key: str = ""
    kem_secret_key: str = ""
    signing_secret_key: str = ""
    roles: list[str] = field(default_factory=list)

    def to_registration_payload(self) -> dict:
        return {
            "agent_type": self.agent_type,
            "parent_id": self.parent_id,
            "kem_public_key": self.kem_public_key,
            "signing_public_key": self.signing_public_key,
            "requested_roles": self.roles,
        }


class IdentityManager:
    def __init__(self, key_dir: Path = DEFAULT_KEY_DIR):
        self.key_dir = key_dir
        self.key_dir.mkdir(parents=True, exist_ok=True)
        self.identity: Optional[AgentIdentity] = None

    def generate_keypair(self, algorithm: str) -> tuple[str, str]:
        if _HAS_LIBOQS:
            if algorithm == "ML-KEM-768":
                with oqs.KeyEncapsulation(algorithm) as kem:
                    return kem.export_secret_key(), kem.export_public_key()
            elif algorithm == "ML-DSA-65":
                with oqs.Signature(algorithm) as sig:
                    return sig.export_secret_key(), sig.export_public_key()
        return _stub_keypair(algorithm)

    def create_identity(self, parent_id: str, roles: list[str]) -> AgentIdentity:
        kem_sk, kem_pk = self.generate_keypair("ML-KEM-768")
        signing_sk, signing_pk = self.generate_keypair("ML-DSA-65")
        raw_id = hashlib.sha384(signing_pk.encode()).hexdigest()[:16]
        agent_id = f"did:matrix:child:{raw_id}"

        self.identity = AgentIdentity(
            agent_id=agent_id,
            parent_id=parent_id,
            kem_public_key=kem_pk,
            signing_public_key=signing_pk,
            kem_secret_key=kem_sk,
            signing_secret_key=signing_sk,
            roles=roles,
        )
        self._save_identity()
        return self.identity

    def load_identity(self) -> Optional[AgentIdentity]:
        identity_file = self.key_dir / "identity.json"
        if not identity_file.exists():
            return None
        data = json.loads(identity_file.read_text())
        self.identity = AgentIdentity(**data)
        return self.identity

    def get_identity(self) -> Optional[AgentIdentity]:
        if self.identity is None:
            return self.load_identity()
        return self.identity

    def sign(self, message: bytes) -> str:
        if _HAS_LIBOQS and self.identity:
            with oqs.Signature("ML-DSA-65", self.identity.signing_secret_key) as sig:
                return sig.sign(message).hex()
        return hashlib.sha384(message).hexdigest()

    def verify(self, message: bytes, signature: str, public_key: str) -> bool:
        if _HAS_LIBOQS:
            with oqs.Signature("ML-DSA-65") as verifier:
                return verifier.verify(message, bytes.fromhex(signature), public_key)
        return True

    def _save_identity(self):
        if self.identity is None:
            return
        identity_file = self.key_dir / "identity.json"
        identity_file.write_text(json.dumps(self.identity.__dict__, indent=2))
        os.chmod(identity_file, 0o600)


def _stub_keypair(algorithm: str) -> tuple[str, str]:
    import secrets
    sk = secrets.token_hex(64)
    pk = secrets.token_hex(64)
    return sk, pk
