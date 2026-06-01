"""
Audit Logger — records all agent actions with ML-DSA-65 signatures
for offline verifiable audit trail.

Each audit entry is signed locally and queued for upload when online.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_AUDIT_DIR = Path.home() / ".matrix" / "audit"


@dataclass
class AuditEntry:
    event_id: str
    agent_id: str
    action: str
    timestamp: str
    capability_id: str = ""
    action_detail: dict = field(default_factory=dict)
    offline: bool = True
    knowledge_version: str = ""
    policy_hash: str = ""
    result: str = "allowed"
    signature: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "action": self.action,
            "timestamp": self.timestamp,
            "capability_id": self.capability_id,
            "action_detail": self.action_detail,
            "offline": self.offline,
            "knowledge_version": self.knowledge_version,
            "policy_hash": self.policy_hash,
            "result": self.result,
            "signature": self.signature,
        }

    def to_bytes(self) -> bytes:
        payload = {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "action": self.action,
            "timestamp": self.timestamp,
            "capability_id": self.capability_id,
            "action_detail": self.action_detail,
            "knowledge_version": self.knowledge_version,
            "result": self.result,
        }
        return json.dumps(payload, sort_keys=True).encode()


class AuditLogger:
    VALID_ACTIONS = {
        "knowledge.search",
        "knowledge.decrypt",
        "rag.query",
        "summary.generate",
        "tool.invoke",
        "sync.upload",
        "sync.download",
        "identity.register",
        "identity.revoke",
        "audit.upload",
    }

    def __init__(self, agent_id: str, audit_dir: Path = DEFAULT_AUDIT_DIR,
                 sign_func: Optional[callable] = None):
        self.agent_id = agent_id
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.sign_func = sign_func
        self.entries: list[AuditEntry] = []

    def log(self, action: str, result: str = "allowed",
            action_detail: dict | None = None,
            capability_id: str = "",
            knowledge_version: str = "",
            policy_hash: str = "") -> AuditEntry:
        if action not in self.VALID_ACTIONS:
            raise ValueError(f"invalid audit action: {action}")

        entry = AuditEntry(
            event_id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            action=action,
            timestamp=datetime.now(timezone.utc).isoformat(),
            capability_id=capability_id,
            action_detail=action_detail or {},
            offline=True,
            knowledge_version=knowledge_version,
            policy_hash=policy_hash,
            result=result,
        )

        if self.sign_func:
            entry.signature = self.sign_func(entry.to_bytes())
        else:
            import hashlib
            entry.signature = hashlib.sha384(entry.to_bytes()).hexdigest()

        self.entries.append(entry)
        self._persist_entry(entry)
        return entry

    def _persist_entry(self, entry: AuditEntry):
        audit_file = self.audit_dir / f"{entry.event_id}.json"
        audit_file.write_text(json.dumps(entry.to_dict(), indent=2))

    def get_entries(self, limit: int = 100) -> list[AuditEntry]:
        entries = []
        for f in sorted(self.audit_dir.glob("*.json"), reverse=True)[:limit]:
            data = json.loads(f.read_text())
            entries.append(AuditEntry(**data))
        return entries

    def get_unsynced(self) -> list[AuditEntry]:
        synced_file = self.audit_dir / ".synced_marker"
        last_synced = ""
        if synced_file.exists():
            last_synced = synced_file.read_text().strip()

        unsynced = []
        for f in sorted(self.audit_dir.glob("*.json")):
            if f.name > last_synced:
                data = json.loads(f.read_text())
                unsynced.append(AuditEntry(**data))
        return unsynced

    def mark_synced(self, event_id: str):
        synced_file = self.audit_dir / ".synced_marker"
        synced_file.write_text(event_id)

    @property
    def entry_count(self) -> int:
        return len(list(self.audit_dir.glob("*.json")))
