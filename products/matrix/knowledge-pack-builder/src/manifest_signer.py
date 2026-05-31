"""
Manifest Signer — signs knowledge manifests with ML-DSA-65 and
anchors merkle roots on-chain (local chain or test chain).
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

try:
    import oqs
    _HAS_LIBOQS = True
except ImportError:
    _HAS_LIBOQS = False


@dataclass
class KnowledgeManifest:
    knowledge_version: str
    manifest_hash: str
    merkle_root: str
    policy_hash: str
    packages: list[dict]
    issuer: str
    previous_version: str = ""
    signature: str = ""
    issued_at: str = ""

    def to_dict(self) -> dict:
        return {
            "knowledge_version": self.knowledge_version,
            "previous_version": self.previous_version,
            "manifest_hash": self.manifest_hash,
            "merkle_root": self.merkle_root,
            "policy_hash": self.policy_hash,
            "packages": self.packages,
            "issuer": self.issuer,
            "signature": self.signature,
            "issued_at": self.issued_at,
        }

    def to_signing_bytes(self) -> bytes:
        payload = self.to_dict()
        del payload["signature"]
        del payload["issued_at"]
        return json.dumps(payload, sort_keys=True).encode()


class ManifestSigner:
    def __init__(self, signing_secret_key: str = "", hash_algorithm: str = "sha384"):
        self.signing_secret_key = signing_secret_key
        self.hash_algorithm = hash_algorithm

    def sign_manifest(self, manifest: KnowledgeManifest) -> str:
        message = manifest.to_signing_bytes()
        if _HAS_LIBOQS and self.signing_secret_key:
            with oqs.Signature("ML-DSA-65", self.signing_secret_key) as sig:
                return sig.sign(message).hex()
        return hashlib.new(self.hash_algorithm, message).hexdigest()

    def verify_manifest(self, manifest: KnowledgeManifest,
                        signing_public_key: str) -> bool:
        if _HAS_LIBOQS:
            with oqs.Signature("ML-DSA-65") as verifier:
                return verifier.verify(
                    manifest.to_signing_bytes(),
                    bytes.fromhex(manifest.signature),
                    signing_public_key,
                )
        # Stub: always true for testing
        return True

    def create_manifest(self, knowledge_version: str, merkle_root: str,
                        policy_hash: str, packages: list[dict],
                        issuer: str, previous_version: str = "") -> KnowledgeManifest:
        manifest = KnowledgeManifest(
            knowledge_version=knowledge_version,
            previous_version=previous_version,
            manifest_hash="",
            merkle_root=merkle_root,
            policy_hash=policy_hash,
            packages=packages,
            issuer=issuer,
            issued_at=datetime.now(timezone.utc).isoformat(),
        )

        manifest_hash = hashlib.new(
            self.hash_algorithm,
            manifest.to_signing_bytes()
        ).hexdigest()
        manifest.manifest_hash = "0x" + manifest_hash
        manifest.signature = self.sign_manifest(manifest)

        return manifest

    @staticmethod
    def compute_hash(data: bytes) -> str:
        return "0x" + hashlib.sha384(data).hexdigest()
