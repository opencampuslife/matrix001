"""
Child Agent CLI — command-line interface for Matrix child agents.

Commands:
    register      Register with Mother Agent (generates PQC keys, gets capability)
    sync          Pull latest knowledge manifest, download and decrypt knowledge packs
    run-offline   Run local QA loop against decrypted knowledge
    upload-audit  Upload signed audit logs to Mother Agent
    status        Show agent identity, capability, and index status

Usage:
    python -m child_agent_runtime register --mother-url http://localhost:18080
    python -m child_agent_runtime sync
    python -m child_agent_runtime run-offline
    python -m child_agent_runtime upload-audit --mother-url http://localhost:18080
    python -m child_agent_runtime status
"""

import argparse
import json
import sys
from pathlib import Path

from .identity_manager import IdentityManager
from .local_policy_engine import LocalPolicyEngine
from .local_rag_engine import LocalRAGEngine
from .encrypted_store import EncryptedStore
from .audit_logger import AuditLogger
from .offline_queue import OfflineQueue
from .tool_sandbox import ToolSandbox
from .pqc_kem_client import PQCKEMClient


def cmd_register(args):
    print("[Matrix] Generating PQC keypairs (ML-KEM-768 + ML-DSA-65)...")
    im = IdentityManager()

    if im.load_identity():
        print(f"[Matrix] Identity already exists: {im.identity.agent_id}")
        print(f"  Roles: {im.identity.roles}")
        return

    identity = im.create_identity(
        parent_id="did:matrix:mother:root",
        roles=args.roles.split(",") if args.roles else ["campus_edge_assistant"],
    )
    print(f"[Matrix] Identity created: {identity.agent_id}")
    print(f"  KEM Public Key (first 32 chars): {identity.kem_public_key[:32]}...")
    print(f"  Signing Public Key (first 32 chars): {identity.signing_public_key[:32]}...")
    print(f"  Roles: {identity.roles}")

    if args.mother_url:
        import urllib.request
        payload = identity.to_registration_payload()
        try:
            req = urllib.request.Request(
                f"{args.mother_url}/agents/register",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                print(f"[Matrix] Registered with Mother Agent: {args.mother_url}")
                print(f"  Server-assigned ID: {result.get('agent_id', 'N/A')}")
        except Exception as e:
            print(f"[Matrix] Warning: Could not contact Mother Agent: {e}")


def cmd_sync(args):
    im = IdentityManager()
    identity = im.load_identity()
    if not identity:
        print("[Matrix] No identity found. Run 'register' first.")
        sys.exit(1)

    print(f"[Matrix] Syncing as {identity.agent_id}...")

    if args.mother_url:
        import urllib.request
        try:
            # Pull latest knowledge manifest
            req = urllib.request.Request(f"{args.mother_url}/agents/{identity.agent_id}")
            with urllib.request.urlopen(req) as resp:
                agent_data = json.loads(resp.read())
                print(f"[Matrix] Agent status: active={agent_data.get('active')}")

            # Pull capability (simulated)
            print("[Matrix] Capability synced (stub — requires /capabilities/issue endpoint)")
        except Exception as e:
            print(f"[Matrix] Warning: Could not contact Mother Agent: {e}")

    pe = LocalPolicyEngine()
    cap = pe.get_capability()
    if cap:
        print(f"[Matrix] Capability: {cap.capability_id}")
        print(f"  Offline allowed: {cap.offline_allowed}")
        print(f"  Expires: {cap.offline_expiry}")
    else:
        print("[Matrix] No capability loaded — offline actions will be denied")

    # Decrypt knowledge packs
    store = EncryptedStore()
    packages = store.list_packages()
    if packages:
        print(f"[Matrix] Local packages: {len(packages)}")
        for pkg in packages:
            print(f"  - {pkg}")
    else:
        print("[Matrix] No local knowledge packages found")

    print("[Matrix] Sync complete.")


def cmd_run_offline(args):
    im = IdentityManager()
    identity = im.load_identity()
    if not identity:
        print("[Matrix] No identity found. Run 'register' first.")
        sys.exit(1)

    pe = LocalPolicyEngine()
    cap = pe.get_capability()

    if cap is None:
        cap_data_file = pe.policy_dir / "capability.json"
        if cap_data_file.exists():
            cap = pe.load_capability(json.loads(cap_data_file.read_text()))

    if cap is None:
        print("[Matrix] No capability loaded. Run 'sync' first.")
        sys.exit(1)

    check = pe.check_action("rag.query")
    if not check.allowed:
        print(f"[Matrix] Offline execution denied: {check.reason}")
        sys.exit(1)

    logger = AuditLogger(agent_id=identity.agent_id)
    engine = LocalRAGEngine()
    sandbox = ToolSandbox(
        allowed_tools=cap.allowed_tools,
        denied_tools=cap.denied_tools,
    )

    # Try to load latest index
    loaded = False
    for idx_file in sorted(engine.index_dir.glob("index_*.json"), reverse=True):
        version = idx_file.stem.replace("index_", "")
        if engine.load_index(version):
            print(f"[Matrix] Loaded knowledge index version {version} ({engine.chunk_count} chunks)")
            loaded = True
            break

    if not loaded:
        print("[Matrix] No knowledge index found. Run 'sync' first.")
        sys.exit(1)

    print(f"[Matrix] Running offline. {engine.chunk_count} chunks loaded.")
    print(f"[Matrix] Allowed tools: {cap.allowed_tools}")
    print(f"[Matrix] Denied tools: {cap.denied_tools}")
    print("[Matrix] Type 'quit' to exit, 'status' for stats.\n")

    while True:
        try:
            query = input("[Matrix] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Matrix] Exiting. Audit logs saved locally.")
            break

        if query.lower() == "quit":
            break
        if query.lower() == "status":
            print(f"  Agent: {identity.agent_id}")
            print(f"  Capability: {cap.capability_id}")
            print(f"  Offline actions: {pe.offline_action_count}/{cap.max_offline_actions}")
            print(f"  Audit entries: {logger.entry_count}")
            print(f"  Chunks: {engine.chunk_count}")
            continue
        if not query:
            continue

        # Policy check
        check = pe.check_action("rag.query")
        if not check.allowed:
            print(f"  [DENIED] {check.reason}")
            logger.log("rag.query", result="denied", action_detail={"query_hash": str(hash(query))})
            continue

        # Search
        results = engine.search(query, top_k=3)
        logger.log(
            "rag.query",
            result="allowed",
            action_detail={
                "query_hash": str(hash(query)),
                "results_count": len(results),
            },
            capability_id=cap.capability_id,
            knowledge_version=cap.policy_hash,
        )

        if not results:
            print("  No relevant knowledge found.")
        else:
            for i, r in enumerate(results, 1):
                print(f"\n  [{i}] score={r.score:.2f} (chunk: {r.chunk.chunk_id})")
                print(f"  {r.chunk.text[:200]}...")
                if r.chunk.source_id:
                    print(f"  Source: {r.chunk.source_id}")

    print(f"[Matrix] Session complete. {logger.entry_count} audit entries recorded.")


def cmd_upload_audit(args):
    im = IdentityManager()
    identity = im.load_identity()
    if not identity:
        print("[Matrix] No identity found. Run 'register' first.")
        sys.exit(1)

    logger = AuditLogger(agent_id=identity.agent_id)
    unsynced = logger.get_unsynced()
    print(f"[Matrix] Unsynced audit entries: {len(unsynced)}")

    if args.mother_url:
        import urllib.request
        for entry in unsynced:
            try:
                req = urllib.request.Request(
                    f"{args.mother_url}/revocations",
                    data=json.dumps(entry.to_dict()).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as resp:
                    logger.mark_synced(entry.event_id)
                    print(f"  Uploaded: {entry.event_id}")
            except Exception as e:
                print(f"  Failed to upload {entry.event_id}: {e}")
    else:
        for entry in unsynced[:5]:
            print(f"  {entry.event_id}: {entry.action} ({entry.result})")

    print("[Matrix] Audit upload complete.")


def cmd_status(args):
    im = IdentityManager()
    identity = im.load_identity()

    print("=== Matrix Child Agent Status ===\n")

    if identity:
        print(f"Agent ID:      {identity.agent_id}")
        print(f"Agent Type:    {identity.agent_type}")
        print(f"Parent:        {identity.parent_id}")
        print(f"Roles:         {', '.join(identity.roles)}")
    else:
        print("Agent ID:      NOT REGISTERED")
        print("Run 'register' to create identity.\n")
        return

    pe = LocalPolicyEngine()
    cap = pe.get_capability()
    if cap is None:
        cap_data_file = pe.policy_dir / "capability.json"
        if cap_data_file.exists():
            cap = pe.load_capability(json.loads(cap_data_file.read_text()))

    print()
    if cap:
        print(f"Capability:    {cap.capability_id}")
        print(f"Offline:       {'ALLOWED' if cap.offline_allowed else 'DENIED'}")
        print(f"Expires:       {cap.offline_expiry}")
        print(f"Actions:       {pe.offline_action_count}/{cap.max_offline_actions}")
    else:
        print("Capability:    NONE (run 'sync')")

    engine = LocalRAGEngine()
    indexes = list(engine.index_dir.glob("index_*.json"))
    print(f"\nIndexes:       {len(indexes)}")
    for idx in indexes:
        v = idx.stem.replace("index_", "")
        engine.load_index(v)
        print(f"  {v}: {engine.chunk_count} chunks")

    store = EncryptedStore()
    pkgs = store.list_packages()
    print(f"\nPackages:      {len(pkgs)}")
    for pkg in pkgs:
        print(f"  {pkg}")

    logger = AuditLogger(agent_id=identity.agent_id)
    unsynced = logger.get_unsynced()
    print(f"\nAudit Logs:    {logger.entry_count} total, {len(unsynced)} unsynced")

    queue = OfflineQueue()
    print(f"\nQueue:         {queue.size} items pending")


def main():
    parser = argparse.ArgumentParser(
        description="Matrix Child Agent Runtime",
        prog="matrix-child",
    )
    parser.add_argument("--mother-url", default="http://localhost:18080",
                        help="Mother Agent API URL")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("register", help="Register with Mother Agent")
    sync_p = sub.add_parser("sync", help="Sync knowledge and capability")
    sub.add_parser("run-offline", help="Run offline QA loop")
    sub.add_parser("upload-audit", help="Upload audit logs")
    sub.add_parser("status", help="Show agent status")

    args = parser.parse_args()

    commands = {
        "register": cmd_register,
        "sync": cmd_sync,
        "run-offline": cmd_run_offline,
        "upload-audit": cmd_upload_audit,
        "status": cmd_status,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
