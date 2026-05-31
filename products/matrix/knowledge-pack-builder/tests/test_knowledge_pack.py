import hashlib
import json
import os
import tempfile
from pathlib import Path

from knowledge_pack_builder.chunk_encryptor import ChunkEncryptor
from knowledge_pack_builder.dek_manager import DEKManager
from knowledge_pack_builder.merkle_builder import MerkleBuilder
from knowledge_pack_builder.manifest_signer import ManifestSigner, KnowledgeManifest
from knowledge_pack_builder.pack_releaser import PackReleaser


SAMPLE_CHUNKS = [
    {
        "chunk_id": "c001",
        "text": "招生政策要求考生具有高中学历或同等学力。报名时间为每年3月。",
        "source_id": "policies/admission_policy",
        "retrieval_keywords": ["招生", "政策", "报名"],
        "canonical_question": "招生条件是什么？",
        "role_tags": ["campus_edge_assistant"],
    },
    {
        "chunk_id": "c002",
        "text": "食堂提供早餐、午餐和晚餐。早餐7:00-9:00，午餐11:30-13:30，晚餐17:30-21:00。",
        "source_id": "campus/canteen",
        "retrieval_keywords": ["食堂", "餐饮", "时间"],
        "canonical_question": "食堂什么时间开放？",
        "role_tags": ["campus_edge_assistant"],
    },
]


def test_chunk_encryptor_encrypts_and_includes_aad():
    enc = ChunkEncryptor()
    pkg = enc.encrypt_chunks(
        chunks=SAMPLE_CHUNKS,
        package_id="test_pkg",
        role_tags=["campus_edge_assistant"],
        source_version="matrix-kb-2026.06.01.001",
        policy_hash="0xabcdef",
    )
    assert pkg.package_id == "test_pkg"
    assert len(pkg.ciphertext) > 0
    assert len(pkg.nonce) == 12
    assert len(pkg.dek) == 32
    assert b"test_pkg" in pkg.aad


def test_chunk_encryptor_generates_unique_dek():
    enc = ChunkEncryptor()
    d1 = enc.generate_dek()
    d2 = enc.generate_dek()
    assert d1 != d2
    assert len(d1) == 32


def test_dek_manager_encapsulates():
    dm = DEKManager()
    dek = os.urandom(32)
    edek = dm.encapsulate_dek(dek, "test_kem_public_key")
    assert edek.algorithm == "ML-KEM-768"
    assert len(edek.ciphertext) > 0


def test_dek_manager_encapsulates_for_multiple_agents():
    dm = DEKManager()
    dek = os.urandom(32)
    agents = [
        {"agent_id": "agent1", "kem_public_key": "key1"},
        {"agent_id": "agent2", "kem_public_key": "key2"},
    ]
    edeks = dm.encapsulate_for_agents(dek, agents)
    assert len(edeks) == 2
    assert edeks[0].agent_id == "agent1"
    assert edeks[1].agent_id == "agent2"


def test_merkle_builder_single_package():
    mb = MerkleBuilder()
    root, hashes = mb.build_from_packages([
        {"package_id": "pkg1", "hash": "0xabcd1234"}
    ])
    assert root.startswith("0x")
    assert len(hashes) == 1


def test_merkle_builder_multiple_packages():
    mb = MerkleBuilder()
    root, hashes = mb.build_from_packages([
        {"package_id": "pkg1", "hash": "0xaaaa"},
        {"package_id": "pkg2", "hash": "0xbbbb"},
        {"package_id": "pkg3", "hash": "0xcccc"},
    ])
    assert root.startswith("0x")
    assert len(hashes) == 3
    # Root should be same regardless of ordering
    root2, _ = mb.build_from_packages([
        {"package_id": "pkg1", "hash": "0xaaaa"},
        {"package_id": "pkg2", "hash": "0xbbbb"},
        {"package_id": "pkg3", "hash": "0xcccc"},
    ])
    assert root == root2


def test_merkle_proof_verify():
    mb = MerkleBuilder()
    root, hashes = mb.build_from_packages([
        {"package_id": "pkg1", "hash": "0xaaaa"},
        {"package_id": "pkg2", "hash": "0xbbbb"},
    ])
    proof = mb.generate_proof(hashes[0], hashes)
    assert mb.verify_proof(hashes[0], root, proof)

    # Wrong root should fail
    assert not mb.verify_proof(hashes[0], "0x" + "f" * 96, proof)


def test_merkle_builder_empty():
    mb = MerkleBuilder()
    root, hashes = mb.build_from_packages([])
    assert root == "0x" + "0" * 96
    assert hashes == []


def test_manifest_signer_creates_signed_manifest():
    signer = ManifestSigner(signing_secret_key="test_secret")
    manifest = signer.create_manifest(
        knowledge_version="matrix-kb-2026.06.01.001",
        merkle_root="0xdeadbeef",
        policy_hash="0xpolicyhash",
        packages=[
            {
                "package_id": "kpkg_test",
                "cid": "bafy_abcdef",
                "hash": "0xabcdef",
                "role_tags": ["campus_edge_assistant"],
                "encrypted_dek": ["enc_dek_base64"],
            }
        ],
        issuer="did:matrix:mother:root",
    )
    assert manifest.knowledge_version == "matrix-kb-2026.06.01.001"
    assert manifest.signature != ""
    assert manifest.manifest_hash.startswith("0x")


def test_manifest_signer_verify():
    signer = ManifestSigner()
    manifest = signer.create_manifest(
        knowledge_version="matrix-kb-2026.06.01.001",
        merkle_root="0xroot",
        policy_hash="0xpolicy",
        packages=[],
        issuer="did:matrix:mother:root",
    )
    assert signer.verify_manifest(manifest, "test_public_key")


def test_pack_releaser_full_pipeline():
    releaser = PackReleaser(
        signing_secret_key="test_mother_key",
        release_dir=Path(tempfile.mkdtemp()),
    )
    result = releaser.release(
        chunks=SAMPLE_CHUNKS,
        role_tags=["campus_edge_assistant"],
        authorized_agents=[
            {"agent_id": "did:matrix:child:abc", "kem_public_key": "key123"},
        ],
        knowledge_version="matrix-kb-2026.06.01.001",
        policy_hash="0xpolicy_v1",
        issuer_did="did:matrix:mother:root",
    )
    assert result.success
    assert result.package_count == 1
    assert result.merkle_root.startswith("0x")
    assert "packages" in result.manifest
    assert result.manifest["issuer"] == "did:matrix:mother:root"


def test_pack_releaser_empty_chunks_errors():
    releaser = PackReleaser(release_dir=Path(tempfile.mkdtemp()))
    result = releaser.release(
        chunks=[],
        role_tags=["test"],
        authorized_agents=[],
        knowledge_version="v1",
        policy_hash="0x1",
        issuer_did="did:matrix:mother:root",
    )
    assert not result.success


def test_pack_releaser_persists_release():
    release_dir = Path(tempfile.mkdtemp())
    releaser = PackReleaser(signing_secret_key="key", release_dir=release_dir)
    releaser.release(
        chunks=SAMPLE_CHUNKS,
        role_tags=["campus_edge_assistant"],
        authorized_agents=[{"agent_id": "a1", "kem_public_key": "k1"}],
        knowledge_version="matrix-kb-2026.06.01.001",
        policy_hash="0x1",
        issuer_did="did:matrix:mother:root",
    )
    releases = releaser.list_releases()
    assert "matrix-kb-2026.06.01.001" in releases

    manifest = releaser.get_release("matrix-kb-2026.06.01.001")
    assert manifest is not None
    assert manifest["knowledge_version"] == "matrix-kb-2026.06.01.001"
