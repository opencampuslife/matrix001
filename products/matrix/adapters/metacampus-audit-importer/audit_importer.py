"""
Metacampus Audit Importer — receives Matrix offline audit summaries
and displays them in the original product's admin reports.

This adapter performs READ-ONLY import. It does not give Matrix
write access to the original product's core data.

The original product only displays summaries and does not take
responsibility for Matrix execution correctness.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DEFAULT_IMPORT_DIR = Path.home() / ".matrix" / "audit_imports"


@dataclass
class AuditSummary:
    matrix_agent_id: str
    agent_roles: list[str]
    online_actions: int = 0
    offline_actions: int = 0
    denied_actions: int = 0
    allowed_actions: int = 0
    knowledge_versions: list[str] = field(default_factory=list)
    last_sync_time: str = ""
    report_generated_at: str = ""
    raw_entries: list[dict] = field(default_factory=list)

    @property
    def total_actions(self) -> int:
        return self.online_actions + self.offline_actions

    @property
    def deny_rate(self) -> float:
        if self.total_actions == 0:
            return 0.0
        return self.denied_actions / self.total_actions


class AuditImporter:
    """Receives Matrix audit summaries for display in admin reports."""

    def __init__(self, import_dir: Path = DEFAULT_IMPORT_DIR):
        self.import_dir = import_dir
        self.import_dir.mkdir(parents=True, exist_ok=True)
        self._summaries: dict[str, AuditSummary] = {}

    def import_audit_summary(self, agent_id: str, audit_data: dict) -> AuditSummary:
        entries = audit_data.get("entries", [])
        actions = [e for e in entries if e.get("action")]

        online = sum(1 for e in actions if not e.get("offline", True))
        offline = sum(1 for e in actions if e.get("offline", True))
        denied = sum(1 for e in actions if e.get("result") == "denied")
        allowed = sum(1 for e in actions if e.get("result") == "allowed")

        versions = list(set(
            e.get("knowledge_version", "") for e in actions
            if e.get("knowledge_version")
        ))

        summary = AuditSummary(
            matrix_agent_id=agent_id,
            agent_roles=audit_data.get("roles", []),
            online_actions=online,
            offline_actions=offline,
            denied_actions=denied,
            allowed_actions=allowed,
            knowledge_versions=versions,
            last_sync_time=audit_data.get("last_sync", ""),
            report_generated_at=datetime.now(timezone.utc).isoformat(),
            raw_entries=actions,
        )

        self._summaries[agent_id] = summary
        self._save_summary(agent_id, summary)
        return summary

    def get_summary(self, agent_id: str) -> Optional[AuditSummary]:
        if agent_id in self._summaries:
            return self._summaries[agent_id]

        summary_file = self.import_dir / f"{agent_id}_summary.json"
        if summary_file.exists():
            data = json.loads(summary_file.read_text())
            return AuditSummary(**data)
        return None

    def get_all_summaries(self) -> list[AuditSummary]:
        summaries = []
        for f in self.import_dir.glob("*_summary.json"):
            data = json.loads(f.read_text())
            summaries.append(AuditSummary(**data))
        return summaries

    def generate_report(self, agent_id: str) -> dict:
        summary = self.get_summary(agent_id)
        if summary is None:
            return {"error": "no data for agent", "agent_id": agent_id}

        alerts = []
        if summary.deny_rate > 0.1:
            alerts.append({
                "level": "warning",
                "message": f"High deny rate: {summary.deny_rate:.1%}",
            })
        if summary.total_actions > 10000:
            alerts.append({
                "level": "info",
                "message": "High activity volume",
            })

        return {
            "agent_id": summary.matrix_agent_id,
            "report_type": "audit_summary",
            "total_actions": summary.total_actions,
            "online_actions": summary.online_actions,
            "offline_actions": summary.offline_actions,
            "denied_actions": summary.denied_actions,
            "allowed_actions": summary.allowed_actions,
            "deny_rate": summary.deny_rate,
            "knowledge_versions": summary.knowledge_versions,
            "last_sync": summary.last_sync_time,
            "alerts": alerts,
            "disclaimer": "Summary only. Metacampus does not assume execution responsibility for Matrix actions.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _save_summary(self, agent_id: str, summary: AuditSummary):
        summary_file = self.import_dir / f"{agent_id}_summary.json"
        summary_file.write_text(json.dumps(summary.__dict__, indent=2))
