"""
Pack Releaser — orchestrates the full knowledge pack build and release pipeline.

Pipeline flow:
    Source chunks → encrypt (AES-256-GCM) → wrap DEK (ML-KEM) →
    build Merkle tree → sign manifest → publish
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .chunk_encryptor import ChunkEncryptor
from .dek_manager import DEKManager
from .merkle_builder import MerkleBuilder
from .manifest_signer import ManifestSigner, KnowledgeManifest


DEFAULT_RELEASE_DIR = Path.home() / ".matrix" / "releases"


@dataclass
class ReleaseResult:
    knowledge_version: str
    merkle_root: str
    manifest: dict
    package_count: int
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class PackReleaser:
    def __init__(self, signing_secret_key: str = "",
                 release_dir: Path = DEFAULT_RELEASE_DIR):
        self.encryptor = ChunkEncryptor()
        self.dek_manager = DEKManager()
        self.merkle = MerkleBuilder()
        self.signer = ManifestSigner(signing_secret_key=signing_secret_key)
        self.release_dir = release_dir
        self.release_dir.mkdir(parents=True, exist_ok=True)

    def release(self, chunks: list[dict], role_tags: list[str],
                authorized_agents: list[dict],
                knowledge_version: str,
                policy_hash: str,
                issuer_did: str,
                previous_version: str = "") -> ReleaseResult:
        errors: list[str] = []

        if not chunks:
            errors.append("no chunks provided")
            return ReleaseResult("", "", {}, 0, errors)

        package_id = f"kpkg_{knowledge_version.replace('.', '_')}"
        source_version = knowledge_version

        # Step 1: Encrypt chunks
        pkg = self.encryptor.encrypt_chunks(
            chunks=chunks,
            package_id=package_id,
            role_tags=role_tags,
            source_version=source_version,
            policy_hash=policy_hash,
        )
        encrypted_blob = self.encryptor.get_encrypted_blob(pkg)
        pkg_hash = ManifestSigner.compute_hash(encrypted_blob)

        # Step 2: Wrap DEK for each authorized agent
        encrypted_deks = self.dek_manager.encapsulate_for_agents(
            dek=pkg.dek,
            agents=authorized_agents,
        )

        # Step 3: Build Merkle tree
        merkle_root, leaf_hashes = self.merkle.build_from_packages([
            {
                "package_id": package_id,
                "hash": pkg_hash,
            }
        ])

        # Step 4: Build manifest
        manifest_packages = [
            {
                "package_id": package_id,
                "cid": f"bafy_{pkg_hash[:16]}",
                "hash": pkg_hash,
                "role_tags": role_tags,
                "encrypted_dek": [edek.ciphertext for edek in encrypted_deks],
            }
        ]

        manifest = self.signer.create_manifest(
            knowledge_version=knowledge_version,
            merkle_root=merkle_root,
            policy_hash=policy_hash,
            packages=manifest_packages,
            issuer=issuer_did,
            previous_version=previous_version,
        )

        # Step 5: Save release artifacts
        self._save_release(knowledge_version, manifest, encrypted_blob)

        return ReleaseResult(
            knowledge_version=knowledge_version,
            merkle_root=merkle_root,
            manifest=manifest.to_dict(),
            package_count=len(manifest_packages),
        )

    def _save_release(self, version: str, manifest: KnowledgeManifest,
                      encrypted_blob: bytes):
        version_dir = self.release_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)

        (version_dir / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2))
        (version_dir / "packages").mkdir(exist_ok=True)
        (version_dir / "packages" / "knowledge.enc").write_bytes(encrypted_blob)

    def list_releases(self) -> list[str]:
        return sorted(
            [d.name for d in self.release_dir.iterdir() if d.is_dir()],
            reverse=True,
        )

    def get_release(self, version: str) -> Optional[dict]:
        manifest_file = self.release_dir / version / "manifest.json"
        if not manifest_file.exists():
            return None
        return json.loads(manifest_file.read_text())
