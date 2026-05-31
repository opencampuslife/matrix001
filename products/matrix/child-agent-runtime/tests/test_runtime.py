import json
import tempfile
from pathlib import Path

from child_agent_runtime.identity_manager import IdentityManager
from child_agent_runtime.local_policy_engine import LocalPolicyEngine
from child_agent_runtime.encrypted_store import EncryptedStore
from child_agent_runtime.audit_logger import AuditLogger
from child_agent_runtime.offline_queue import OfflineQueue
from child_agent_runtime.tool_sandbox import ToolSandbox
from child_agent_runtime.local_rag_engine import LocalRAGEngine, Chunk


def test_identity_manager_generates_keys():
    im = IdentityManager(key_dir=Path(tempfile.mkdtemp()))
    identity = im.create_identity("did:matrix:mother:root", ["campus_edge_assistant"])
    assert identity.agent_id.startswith("did:matrix:child:")
    assert len(identity.kem_public_key) > 0
    assert len(identity.signing_public_key) > 0
    assert identity.roles == ["campus_edge_assistant"]


def test_identity_persistence():
    d = Path(tempfile.mkdtemp())
    im = IdentityManager(key_dir=d)
    im.create_identity("did:matrix:mother:root", ["test_role"])
    im2 = IdentityManager(key_dir=d)
    loaded = im2.load_identity()
    assert loaded is not None
    assert loaded.agent_id == im.identity.agent_id


def test_policy_engine_denies_without_capability():
    pe = LocalPolicyEngine(policy_dir=Path(tempfile.mkdtemp()))
    result = pe.check_action("rag.query")
    assert not result.allowed
    assert "no capability" in result.reason


def test_policy_engine_allows_with_capability():
    pe = LocalPolicyEngine(policy_dir=Path(tempfile.mkdtemp()))
    pe.load_capability({
        "capability_id": "cap_test",
        "agent_id": "test_agent",
        "roles": ["test"],
        "allowed_knowledge": ["kb_public"],
        "allowed_tools": ["local_rag.search"],
        "denied_tools": [],
        "offline_allowed": True,
        "offline_expiry": "2099-01-01T00:00:00Z",
        "max_offline_actions": 10,
    })
    result = pe.check_action("rag.query", knowledge_id="kb_public")
    assert result.allowed


def test_policy_engine_denies_denied_tool():
    pe = LocalPolicyEngine(policy_dir=Path(tempfile.mkdtemp()))
    pe.load_capability({
        "capability_id": "cap_test",
        "agent_id": "test_agent",
        "roles": ["test"],
        "allowed_knowledge": ["kb_public"],
        "allowed_tools": ["local_rag.search"],
        "denied_tools": ["remote_write"],
        "offline_allowed": True,
        "offline_expiry": "2099-01-01T00:00:00Z",
        "max_offline_actions": 10,
    })
    result = pe.check_action("tool.invoke", tool_name="remote_write")
    assert not result.allowed


def test_encrypted_store_roundtrip():
    import os
    key = os.urandom(32)
    store = EncryptedStore(store_dir=Path(tempfile.mkdtemp()), master_key=key)
    plaintext = b"hello matrix knowledge pack"
    aad = b"v1:kb_public:sha256:abc123"
    item_key = store.derive_item_key("pkg_001", "1.0.0", "campus_edge", "0xdeadbeef")

    path = store.save_package("pkg_001", plaintext, item_key, aad)
    assert path.exists()

    decrypted = store.load_package("pkg_001", item_key, aad)
    assert decrypted == plaintext


def test_encrypted_store_wrong_aad_fails():
    import os
    key = os.urandom(32)
    store = EncryptedStore(store_dir=Path(tempfile.mkdtemp()), master_key=key)
    item_key = store.derive_item_key("pkg_001", "1.0.0", "test", "0xdead")
    store.save_package("pkg_001", b"secret", item_key, b"correct_aad")
    result = store.load_package("pkg_001", item_key, b"wrong_aad")
    assert result is None


def test_audit_logger_creates_signed_entries():
    logger = AuditLogger(agent_id="did:matrix:child:test", audit_dir=Path(tempfile.mkdtemp()))
    entry = logger.log("rag.query", result="allowed", action_detail={"query": "hello"})
    assert entry.agent_id == "did:matrix:child:test"
    assert entry.action == "rag.query"
    assert len(entry.signature) > 0


def test_audit_logger_rejects_invalid_action():
    logger = AuditLogger(agent_id="test", audit_dir=Path(tempfile.mkdtemp()))
    try:
        logger.log("invalid.action")
        assert False, "should have raised"
    except ValueError:
        pass


def test_offline_queue_enqueue_dequeue():
    q = OfflineQueue(queue_dir=Path(tempfile.mkdtemp()))
    q.enqueue("audit_log", {"event": "test1"})
    q.enqueue("audit_log", {"event": "test2"})
    items = q.dequeue()
    assert len(items) == 2
    q.remove(items[0].item_id)
    assert q.size == 1


def test_tool_sandbox_denies_critical_tool():
    sandbox = ToolSandbox(allowed_tools=["local_rag.search"], denied_tools=[])
    can, reason = sandbox.can_invoke("remote_write")
    assert not can
    assert "explicit allow" in reason or "allowed list" in reason


def test_tool_sandbox_allows_registered_tool():
    sandbox = ToolSandbox(allowed_tools=["local_rag.search"], denied_tools=[])
    can, reason = sandbox.can_invoke("local_rag.search")
    assert can


def test_local_rag_search():
    chunks = [
        Chunk(chunk_id="c1", text="招生政策要求考生具有高中学历",
              retrieval_keywords=["招生", "政策"], role_tags=["campus_edge_assistant"]),
        Chunk(chunk_id="c2", text="食堂营业时间为早上7点到晚上9点",
              retrieval_keywords=["食堂", "时间"], role_tags=["campus_edge_assistant"]),
    ]
    engine = LocalRAGEngine(index_dir=Path(tempfile.mkdtemp()))
    engine.load_knowledge_pack([c.to_dict() for c in chunks], roles=["campus_edge_assistant"])

    results = engine.search("招生条件是什么", top_k=3)
    assert len(results) > 0
    assert "招生" in results[0].chunk.text
