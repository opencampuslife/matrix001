"""Build the Open Campus Matrix USB Edition distribution bundle.

The bundle is intentionally independent from the original Open Campus runtime:
it carries a local Python runtime, signed policy/config manifests, ML-KEM-768
wrapped DEKs, AES-256-GCM encrypted knowledge, an offline audit queue, and a
simulated online sync endpoint.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pqcrypto.kem import ml_kem_768
from pqcrypto.sign import ml_dsa_65


USB_DIR_NAME = "OPEN_CAMPUS_MATRIX_USB"
RELEASE_ID = "matrix-usb-0.1.0-20260601"
RUNTIME_VERSION = "0.1.0"
KNOWLEDGE_VERSION = "matrix-kb-2026.06.01.001"
POLICY_ID = "matrix-policy-usb-v1"
MOTHER_DID = "did:matrix:mother:root"
CHILD_DID = "did:matrix:child:usb-demo-001"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha384_hex(raw: bytes) -> str:
    return "0x" + hashlib.sha384(raw).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def matrix_chunks() -> list[dict]:
    return [
        {
            "chunk_id": "admission-public-001",
            "knowledge_id": "kb.admission.public",
            "text": "招生政策要求考生具有高中学历或同等学力，报名窗口以当年学校公告为准。",
            "source_id": "metacampus/admission/public-policy",
            "retrieval_keywords": ["招生", "报名", "高中学历", "同等学力"],
            "canonical_question": "招生报名条件是什么？",
            "role_tags": ["admission_agent", "campus_edge_assistant"],
        },
        {
            "chunk_id": "campus-faq-001",
            "knowledge_id": "kb.campus.faq",
            "text": "校园公共 FAQ 可离线查询。涉及个人档案、缴费、生产数据库写入的问题必须联网并重新授权。",
            "source_id": "metacampus/campus/public-faq",
            "retrieval_keywords": ["校园", "FAQ", "离线", "授权"],
            "canonical_question": "离线时能查询哪些校园信息？",
            "role_tags": ["admission_agent", "campus_edge_assistant"],
        },
        {
            "chunk_id": "security-boundary-001",
            "knowledge_id": "kb.policy.public",
            "text": "Matrix USB Edition 不携带 Root 私钥、生产数据库凭证、长期远程 API Key 或未加密用户隐私数据。",
            "source_id": "matrix/security/model",
            "retrieval_keywords": ["Root 私钥", "生产凭证", "隐私", "安全边界"],
            "canonical_question": "U盘分发包里不能放什么？",
            "role_tags": ["admission_agent", "campus_edge_assistant"],
        },
    ]


def runtime_script() -> str:
    return dedent(
        r'''
        #!/usr/bin/env python3
        """Local runtime for Open Campus Matrix USB Edition."""

        from __future__ import annotations

        import argparse
        import base64
        import hashlib
        import json
        import sys
        import urllib.parse
        from datetime import datetime, timezone
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from pqcrypto.kem import ml_kem_768
        from pqcrypto.sign import ml_dsa_65


        def root_dir() -> Path:
            return Path(__file__).resolve().parents[1]


        def b64d(value: str) -> bytes:
            return base64.b64decode(value.encode("ascii"))


        def canonical_bytes(value: object) -> bytes:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


        def load_json(path: Path) -> object:
            return json.loads(path.read_text(encoding="utf-8"))


        def sha256_file(path: Path) -> str:
            h = hashlib.sha256()
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()


        def verify_checksums(root: Path) -> list[str]:
            errors: list[str] = []
            manifest = root / "checks" / "manifest.sha256"
            if not manifest.exists():
                return ["checks/manifest.sha256 missing"]
            for line in manifest.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                expected, rel = line.split("  ", 1)
                target = root / rel
                if not target.exists():
                    errors.append(f"{rel} missing")
                    continue
                actual = sha256_file(target)
                if actual != expected:
                    errors.append(f"{rel} checksum mismatch")
            return errors


        def verify_ml_dsa(public_key: bytes, payload: dict, signature_b64: str) -> bool:
            try:
                return bool(ml_dsa_65.verify(public_key, canonical_bytes(payload), b64d(signature_b64)))
            except Exception:
                return False


        def verify_release(root: Path) -> list[str]:
            errors = verify_checksums(root)
            release = load_json(root / "checks" / "release-manifest.json")
            public_keys = load_json(root / "keys" / "matrix-release-public.json")
            release_payload = dict(release)
            release_sig = release_payload.pop("signature", "")
            if not verify_ml_dsa(b64d(public_keys["ml_dsa_65_public_key"]), release_payload, release_sig):
                errors.append("release manifest ML-DSA-65 signature invalid")

            knowledge = load_json(root / "data" / "knowledge" / "manifest.json")
            knowledge_payload = dict(knowledge)
            knowledge_sig = knowledge_payload.pop("signature", "")
            if not verify_ml_dsa(b64d(public_keys["ml_dsa_65_public_key"]), knowledge_payload, knowledge_sig):
                errors.append("knowledge manifest ML-DSA-65 signature invalid")
            return errors


        def derive_wrap_key(shared_secret: bytes) -> bytes:
            return hashlib.sha256(shared_secret + b"matrix-dek-wrap-v1").digest()


        def load_chunks(root: Path) -> list[dict]:
            errors = verify_release(root)
            if errors:
                raise RuntimeError("; ".join(errors))

            manifest = load_json(root / "data" / "knowledge" / "manifest.json")
            package = manifest["packages"][0]
            private_key = load_json(root / "keys" / "local-child-kem-secret.demo.json")
            secret = b64d(private_key["ml_kem_768_secret_key"])
            envelope = package["encrypted_deks"][0]
            shared_secret = ml_kem_768.decrypt(secret, b64d(envelope["kem_ciphertext"]))
            wrap_key = derive_wrap_key(shared_secret)
            dek = AESGCM(wrap_key).decrypt(
                b64d(envelope["wrap_nonce"]),
                b64d(envelope["wrapped_dek"]),
                b64d(envelope["wrap_aad"]),
            )

            encrypted_package = load_json(root / "data" / "knowledge" / "packages" / package["file"])
            plaintext = AESGCM(dek).decrypt(
                b64d(encrypted_package["nonce"]),
                b64d(encrypted_package["ciphertext"]),
                b64d(encrypted_package["aad"]),
            )
            return json.loads(plaintext.decode("utf-8"))


        def policy(root: Path) -> dict:
            return load_json(root / "config" / "capability.policy.json")


        def audit(root: Path, action: str, result: str, detail: dict) -> dict:
            audit_dir = root / "data" / "audit"
            audit_dir.mkdir(parents=True, exist_ok=True)
            log_path = audit_dir / "audit.jsonl"
            previous_hash = ""
            if log_path.exists():
                for line in log_path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        previous_hash = json.loads(line).get("chain_hash", "")
            event = {
                "event_id": hashlib.sha256(f"{datetime.now(timezone.utc).isoformat()}:{action}".encode()).hexdigest()[:24],
                "agent_id": "did:matrix:child:usb-demo-001",
                "action": action,
                "result": result,
                "detail": detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "previous_hash": previous_hash,
            }
            event["chain_hash"] = hashlib.sha384((previous_hash + json.dumps(event, sort_keys=True)).encode()).hexdigest()
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            queue = root / "data" / "pending-sync" / "queue.jsonl"
            queue.parent.mkdir(parents=True, exist_ok=True)
            with queue.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"type": "audit", "payload": event}, ensure_ascii=False, sort_keys=True) + "\n")
            return event


        def query(root: Path, text: str) -> dict:
            cap = policy(root)["roles"]["admission_agent"]
            if "local_rag.search" not in cap["allow_tools"]:
                audit(root, "rag.query", "denied", {"reason": "local_rag.search not allowed"})
                return {"allowed": False, "answer": "DENIED", "results": []}

            chunks = load_chunks(root)
            allowed_knowledge = set(cap["allow_knowledge"])
            terms = [t for t in text.lower().replace("？", " ").replace("?", " ").split() if t]
            results = []
            for chunk in chunks:
                if chunk.get("knowledge_id") not in allowed_knowledge:
                    continue
                haystack = " ".join([
                    chunk.get("text", ""),
                    chunk.get("canonical_question", ""),
                    " ".join(chunk.get("retrieval_keywords", [])),
                ]).lower()
                keyword_hit = any(kw.lower() in text.lower() for kw in chunk.get("retrieval_keywords", []))
                text_hit = any(term in haystack for term in terms)
                if keyword_hit or text_hit:
                    score = (2 if keyword_hit else 0) + (1 if text_hit else 0)
                    results.append({"chunk_id": chunk["chunk_id"], "score": score, "text": chunk["text"]})
            results.sort(key=lambda item: item["score"], reverse=True)
            answer = results[0]["text"] if results else "No authorized local knowledge matched the query."
            audit(root, "rag.query", "allowed", {"query_hash": hashlib.sha256(text.encode()).hexdigest(), "results": len(results)})
            return {"allowed": True, "answer": answer, "results": results[:3]}


        def sync(root: Path) -> dict:
            queue = root / "data" / "pending-sync" / "queue.jsonl"
            items = []
            if queue.exists():
                items = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines() if line.strip()]
            audit_root = hashlib.sha384(canonical_bytes(items)).hexdigest()
            report = {
                "mode": "simulated-online-sync",
                "uploaded_items": len(items),
                "audit_batch_root": "0x" + audit_root,
                "synced_at": datetime.now(timezone.utc).isoformat(),
                "remote_endpoint": load_json(root / "config" / "sync.policy.json")["remote_endpoint"],
            }
            write_path = root / "data" / "pending-sync" / "last-sync.json"
            write_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            queue.write_text("", encoding="utf-8")
            return report


        class Handler(BaseHTTPRequestHandler):
            def _json(self, payload: object, status: int = 200) -> None:
                raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                parsed = urllib.parse.urlparse(self.path)
                root = root_dir()
                if parsed.path == "/healthz":
                    self._json({"status": "ok", "product": "Open Campus Matrix USB Edition"})
                    return
                if parsed.path == "/matrix/status":
                    errors = verify_release(root)
                    self._json({"ready": not errors, "errors": errors, "root": str(root)})
                    return
                if parsed.path == "/matrix/query":
                    params = urllib.parse.parse_qs(parsed.query)
                    self._json(query(root, params.get("q", [""])[0]))
                    return
                if parsed.path == "/matrix/sync":
                    self._json(sync(root))
                    return
                self._json({"error": "not found"}, status=404)

            def log_message(self, format: str, *args: object) -> None:
                log_path = root_dir() / "logs" / "local-gateway.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(format % args + "\n")


        def serve(root: Path, host: str, port: int) -> None:
            errors = verify_release(root)
            if errors:
                raise SystemExit("release verification failed: " + "; ".join(errors))
            server = ThreadingHTTPServer((host, port), Handler)
            print(f"Matrix USB local gateway listening at http://{host}:{port}")
            server.serve_forever()


        def main() -> None:
            parser = argparse.ArgumentParser(description="Open Campus Matrix USB runtime")
            sub = parser.add_subparsers(dest="command", required=True)
            sub.add_parser("verify")
            q = sub.add_parser("query")
            q.add_argument("text")
            s = sub.add_parser("serve")
            s.add_argument("--host", default="127.0.0.1")
            s.add_argument("--port", type=int, default=8787)
            sub.add_parser("sync")
            args = parser.parse_args()
            root = root_dir()
            if args.command == "verify":
                errors = verify_release(root)
                print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
                sys.exit(0 if not errors else 1)
            if args.command == "query":
                print(json.dumps(query(root, args.text), ensure_ascii=False, indent=2))
            if args.command == "sync":
                print(json.dumps(sync(root), ensure_ascii=False, indent=2))
            if args.command == "serve":
                serve(root, args.host, args.port)


        if __name__ == "__main__":
            main()
        '''
    ).lstrip()


def immutable_files(root: Path) -> list[Path]:
    excluded_prefixes = {
        "data/audit",
        "data/pending-sync",
        "logs",
    }
    excluded_files = {
        "checks/manifest.sha256",
        "checks/smoke-report.json",
    }
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excluded_files:
            continue
        if any(rel == prefix or rel.startswith(prefix + "/") for prefix in excluded_prefixes):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def build_bundle(out_dir: Path, clean: bool = True) -> Path:
    root = out_dir / USB_DIR_NAME
    if clean and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    release_public, release_secret = ml_dsa_65.generate_keypair()
    child_public, child_secret = ml_kem_768.generate_keypair()

    profile = {
        "product": "Open Campus Matrix",
        "edition": "USB Edition",
        "version": RUNTIME_VERSION,
        "mode": "offline-first",
        "local_gateway": {"host": "127.0.0.1", "port": 8787},
        "features": {
            "offline_rag": True,
            "online_sync": True,
            "pqc_kem": "ML-KEM-768",
            "pqc_signature": "ML-DSA-65",
            "symmetric_encryption": "AES-256-GCM",
            "blockchain_anchor": False,
        },
    }
    registry = {
        "mother": {"agent_id": MOTHER_DID, "role": "local_controller"},
        "children": [
            {
                "agent_id": CHILD_DID,
                "roles": ["admission_agent", "campus_edge_assistant"],
                "kem_public_key": b64e(child_public),
                "status": "active",
            }
        ],
    }
    capability = {
        "default": "deny",
        "offline_max_actions": 500,
        "roles": {
            "admission_agent": {
                "allow_knowledge": ["kb.admission.public", "kb.campus.faq", "kb.policy.public"],
                "allow_tools": ["local_rag.search", "local_answer.generate", "audit.append"],
                "deny_tools": ["remote_db.write", "payment.execute", "policy.modify", "production.delete"],
                "offline_expiry": "2026-06-08T00:00:00Z",
            }
        },
    }
    policy_hash = sha384_hex(canonical_bytes(capability))
    crypto_policy = {
        "pqc_kem": "ML-KEM-768",
        "pqc_signature": "ML-DSA-65",
        "symmetric_encryption": "AES-256-GCM",
        "dek_policy": "one DEK per knowledge package; DEK wrapped per authorized child agent",
        "root_private_key_policy": "never store root signing secret in USB bundle",
    }
    sync_policy = {
        "mode": "offline-first",
        "remote_endpoint": "https://matrix-sync.example.invalid/v1/sync",
        "upload": ["audit_summary", "status_report"],
        "download": ["knowledge_manifest", "revocation_manifest", "policy_update"],
        "retry": {"max_retries": 5, "backoff_seconds": [5, 30, 120]},
    }
    chain_anchor = {
        "enabled": False,
        "mode": "off-chain-first",
        "anchored_fields": ["manifest_hash", "merkle_root", "policy_hash", "audit_batch_root"],
    }

    write_json(root / "config" / "matrix.profile.json", profile)
    write_json(root / "config" / "agent.registry.json", registry)
    write_json(root / "config" / "capability.policy.json", capability)
    write_json(root / "config" / "crypto.policy.json", crypto_policy)
    write_json(root / "config" / "sync.policy.json", sync_policy)
    write_json(root / "config" / "chain.anchor.json", chain_anchor)

    write_json(
        root / "keys" / "matrix-release-public.json",
        {
            "issuer": MOTHER_DID,
            "signature_algorithm": "ML-DSA-65",
            "ml_dsa_65_public_key": b64e(release_public),
        },
    )
    write_json(
        root / "keys" / "agent-local-public.json",
        {
            "agent_id": CHILD_DID,
            "kem_algorithm": "ML-KEM-768",
            "ml_kem_768_public_key": b64e(child_public),
        },
    )
    write_json(
        root / "keys" / "local-child-kem-secret.demo.json",
        {
            "agent_id": CHILD_DID,
            "usage": "demo local child private key for offline decryption; replace with device-bound sealed key in production",
            "kem_algorithm": "ML-KEM-768",
            "ml_kem_768_secret_key": b64e(child_secret),
        },
    )
    write_text(
        root / "keys" / "DO_NOT_PUT_ROOT_PRIVATE_KEY.txt",
        "Root signing private keys are intentionally absent. Production packages must keep them in an HSM or release signer.\n",
    )

    chunks = matrix_chunks()
    package_id = "kpkg_admission_public_001"
    package_file = f"{package_id}.enc.json"
    dek = os.urandom(32)
    aad = canonical_bytes(
        {
            "package_id": package_id,
            "knowledge_version": KNOWLEDGE_VERSION,
            "roles": ["admission_agent", "campus_edge_assistant"],
            "policy_hash": policy_hash,
        }
    )
    nonce = os.urandom(12)
    ciphertext = AESGCM(dek).encrypt(nonce, canonical_bytes(chunks), aad)
    encrypted_package = {
        "package_id": package_id,
        "algorithm": "AES-256-GCM",
        "knowledge_version": KNOWLEDGE_VERSION,
        "nonce": b64e(nonce),
        "aad": b64e(aad),
        "ciphertext": b64e(ciphertext),
    }
    write_json(root / "data" / "knowledge" / "packages" / package_file, encrypted_package)
    package_hash = sha384_hex(canonical_bytes(encrypted_package))

    kem_ciphertext, shared_secret = ml_kem_768.encrypt(child_public)
    wrap_key = hashlib.sha256(shared_secret + b"matrix-dek-wrap-v1").digest()
    wrap_nonce = os.urandom(12)
    wrap_aad = canonical_bytes({"agent_id": CHILD_DID, "package_id": package_id})
    wrapped_dek = AESGCM(wrap_key).encrypt(wrap_nonce, dek, wrap_aad)

    leaf_hashes = [package_hash]
    merkle_root = sha384_hex(canonical_bytes(leaf_hashes))
    knowledge_manifest_payload = {
        "knowledge_version": KNOWLEDGE_VERSION,
        "previous_version": "",
        "manifest_hash": "",
        "merkle_root": merkle_root,
        "policy_hash": policy_hash,
        "issuer": MOTHER_DID,
        "signature_algorithm": "ML-DSA-65",
        "packages": [
            {
                "package_id": package_id,
                "file": package_file,
                "hash": package_hash,
                "role_tags": ["admission_agent", "campus_edge_assistant"],
                "encrypted_deks": [
                    {
                        "agent_id": CHILD_DID,
                        "kem_algorithm": "ML-KEM-768",
                        "kem_ciphertext": b64e(kem_ciphertext),
                        "wrap_algorithm": "AES-256-GCM",
                        "wrap_nonce": b64e(wrap_nonce),
                        "wrap_aad": b64e(wrap_aad),
                        "wrapped_dek": b64e(wrapped_dek),
                    }
                ],
            }
        ],
    }
    knowledge_manifest_payload["manifest_hash"] = sha384_hex(canonical_bytes(knowledge_manifest_payload))
    knowledge_manifest = dict(knowledge_manifest_payload)
    knowledge_manifest["signature"] = b64e(ml_dsa_65.sign(release_secret, canonical_bytes(knowledge_manifest_payload)))
    write_json(root / "data" / "knowledge" / "manifest.json", knowledge_manifest)

    index = {
        "knowledge_version": KNOWLEDGE_VERSION,
        "chunks": [
            {
                "chunk_id": chunk["chunk_id"],
                "knowledge_id": chunk["knowledge_id"],
                "retrieval_keywords": chunk["retrieval_keywords"],
                "role_tags": chunk["role_tags"],
                "source_id": chunk["source_id"],
            }
            for chunk in chunks
        ],
    }
    write_json(root / "data" / "knowledge" / "index" / f"index_{KNOWLEDGE_VERSION}.json", index)
    write_text(root / "data" / "pending-sync" / "queue.jsonl", "")
    write_text(root / "data" / "audit" / ".gitkeep", "")
    write_text(root / "logs" / ".gitkeep", "")

    write_text(root / "runtime" / "matrix_usb_runtime.py", runtime_script())
    os.chmod(root / "runtime" / "matrix_usb_runtime.py", 0o755)
    write_json(
        root / "runtime" / "offline_agents" / "mother_agent.json",
        {"agent_id": MOTHER_DID, "runtime": "local-controller", "status": "enabled"},
    )
    write_json(
        root / "runtime" / "offline_agents" / "child_agents.json",
        {"agents": registry["children"], "startup_policy": "capability-first"},
    )
    write_text(
        root / "runtime" / "requirements.txt",
        "cryptography>=48.0.0\npqcrypto>=0.3.4\n",
    )

    write_text(
        root / "launcher" / "start-matrix-linux.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\ncd \"$(dirname \"$0\")/..\"\npython3 runtime/matrix_usb_runtime.py verify\npython3 runtime/matrix_usb_runtime.py serve\n",
    )
    write_text(
        root / "launcher" / "start-matrix-macos.command",
        "#!/usr/bin/env bash\nset -euo pipefail\ncd \"$(dirname \"$0\")/..\"\npython3 runtime/matrix_usb_runtime.py verify\npython3 runtime/matrix_usb_runtime.py serve\n",
    )
    write_text(
        root / "launcher" / "start-matrix-windows.ps1",
        "Set-Location (Split-Path $PSScriptRoot -Parent)\npython runtime/matrix_usb_runtime.py verify\npython runtime/matrix_usb_runtime.py serve\n",
    )
    for script in ["start-matrix-linux.sh", "start-matrix-macos.command"]:
        os.chmod(root / "launcher" / script, 0o755)

    write_text(
        root / "README_FIRST.txt",
        dedent(
            f"""
            Open Campus Matrix USB Edition v{RUNTIME_VERSION}

            1. Install bundled runtime dependencies once if this machine has no Matrix runtime:
               python3 -m pip install -r runtime/requirements.txt
            2. Verify the package:
               python3 runtime/matrix_usb_runtime.py verify
            3. Start local gateway:
               python3 runtime/matrix_usb_runtime.py serve
            4. Open http://127.0.0.1:8787/matrix/status
            """
        ).strip()
        + "\n",
    )
    write_text(
        root / "usb-layout.txt",
        dedent(
            """
            OPEN_CAMPUS_MATRIX_USB/
              launcher/   platform start scripts
              runtime/    local gateway + offline mother/child runtime
              data/       encrypted knowledge, local audit, pending sync queue
              config/     capability, crypto, sync, chain anchor policies
              keys/       public keys and demo device child key only
              checks/     signed release manifest and checksums
            """
        ).strip()
        + "\n",
    )
    write_text(
        root / "START_HERE.html",
        dedent(
            f"""
            <!doctype html>
            <html lang="zh-CN">
            <meta charset="utf-8">
            <title>Open Campus Matrix USB Edition</title>
            <style>
            body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:40px;line-height:1.65;color:#172033;background:#f7f8fb}}
            main{{max-width:920px;margin:auto;background:white;border:1px solid #d8dee9;border-radius:10px;padding:28px}}
            code{{background:#eef2ff;padding:2px 6px;border-radius:5px}}
            </style>
            <main>
            <h1>Open Campus Matrix USB Edition v{RUNTIME_VERSION}</h1>
            <p>本包可离线启动本地 Matrix Gateway、Mother Agent 控制器和 Child Agent RAG Runtime。</p>
            <ol>
            <li>运行 <code>python3 runtime/matrix_usb_runtime.py verify</code> 校验签名与完整性。</li>
            <li>运行 <code>python3 runtime/matrix_usb_runtime.py serve</code> 启动本地服务。</li>
            <li>打开 <code>http://127.0.0.1:8787/matrix/status</code> 查看状态。</li>
            <li>访问 <code>http://127.0.0.1:8787/matrix/query?q=招生报名条件是什么</code> 测试离线知识检索。</li>
            </ol>
            <p>Root 私钥、生产数据库凭证、长期远程 API Key 与未加密隐私数据均未放入 U 盘包。</p>
            </main>
            </html>
            """
        ).strip()
        + "\n",
    )
    write_text(
        root / "docs" / "operator-checklist.md",
        dedent(
            """
            # Operator Checklist

            - Run `python3 runtime/matrix_usb_runtime.py verify` before first use.
            - Confirm `keys/DO_NOT_PUT_ROOT_PRIVATE_KEY.txt` exists and no root signing secret is present.
            - Confirm `config/capability.policy.json` has deny-by-default policy.
            - Test offline query with `python3 runtime/matrix_usb_runtime.py query 招生报名条件是什么`.
            - Test simulated sync with `python3 runtime/matrix_usb_runtime.py sync`.
            """
        ).strip()
        + "\n",
    )
    write_text(
        root / "docs" / "security-model.md",
        dedent(
            """
            # Security Model

            Matrix USB Edition uses ML-KEM-768 to establish a per-agent wrapping
            key for the package DEK, AES-256-GCM to encrypt the knowledge package,
            and ML-DSA-65 to sign the release and knowledge manifests.

            The demo bundle includes a local child KEM secret so the package can
            run offline on a fresh machine. Production distribution should replace
            that file with a device-bound sealed key generated during enrollment.
            The root release signing secret is never written to the USB bundle.
            """
        ).strip()
        + "\n",
    )

    file_hashes = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in immutable_files(root)
        if path.relative_to(root).as_posix() != "checks/release-manifest.json"
    }
    release_payload = {
        "release_id": RELEASE_ID,
        "product": "Open Campus Matrix",
        "edition": "USB Edition",
        "runtime_version": RUNTIME_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "policy_id": POLICY_ID,
        "policy_hash": policy_hash,
        "merkle_root": merkle_root,
        "signature_alg": "ML-DSA-65",
        "kem_alg": "ML-KEM-768",
        "symmetric_alg": "AES-256-GCM",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file_hashes": file_hashes,
    }
    release_manifest = dict(release_payload)
    release_manifest["signature"] = b64e(ml_dsa_65.sign(release_secret, canonical_bytes(release_payload)))
    write_json(root / "checks" / "release-manifest.json", release_manifest)

    checksum_lines = []
    for path in immutable_files(root):
        rel = path.relative_to(root).as_posix()
        checksum_lines.append(f"{sha256_file(path)}  {rel}")
    write_text(root / "checks" / "manifest.sha256", "\n".join(checksum_lines) + "\n")
    return root


def smoke_bundle(bundle_root: Path) -> dict:
    runtime = bundle_root / "runtime" / "matrix_usb_runtime.py"
    checks = [
        [sys.executable, str(runtime), "verify"],
        [sys.executable, str(runtime), "query", "招生报名条件是什么"],
        [sys.executable, str(runtime), "sync"],
    ]
    results = []
    for cmd in checks:
        proc = subprocess.run(cmd, cwd=bundle_root, text=True, capture_output=True, check=False)
        results.append(
            {
                "command": " ".join(cmd),
                "returncode": proc.returncode,
                "stdout": proc.stdout[-2000:],
                "stderr": proc.stderr[-2000:],
            }
        )
    report = {
        "status": "passed" if all(item["returncode"] == 0 for item in results) else "failed",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    write_json(bundle_root / "checks" / "smoke-report.json", report)
    return report


def zip_bundle(bundle_root: Path) -> Path:
    zip_base = bundle_root.parent / "open_campus_matrix_usb_edition_v0.1"
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", bundle_root.parent, bundle_root.name))
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Open Campus Matrix USB Edition bundle")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "dist")
    parser.add_argument("--no-clean", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--zip", action="store_true")
    args = parser.parse_args()

    bundle = build_bundle(args.out, clean=not args.no_clean)
    print(f"built {bundle}")
    if args.smoke:
        report = smoke_bundle(bundle)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["status"] != "passed":
            raise SystemExit(1)
    if args.zip:
        print(f"zip {zip_bundle(bundle)}")


if __name__ == "__main__":
    main()

