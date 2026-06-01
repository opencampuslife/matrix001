"""
Offline Queue — buffers audit logs and sync operations when the agent is offline.
When connectivity is restored, queued items are uploaded to the Mother Agent.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_QUEUE_DIR = Path.home() / ".matrix" / "queue"


@dataclass
class QueueItem:
    item_id: str
    item_type: str  # "audit_log", "sync_request", "status_report"
    payload: dict
    created_at: str = ""
    retry_count: int = 0
    max_retries: int = 5

    def should_retry(self) -> bool:
        return self.retry_count < self.max_retries


class OfflineQueue:
    def __init__(self, queue_dir: Path = DEFAULT_QUEUE_DIR):
        self.queue_dir = queue_dir
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, item_type: str, payload: dict) -> QueueItem:
        import uuid
        item = QueueItem(
            item_id=str(uuid.uuid4()),
            item_type=item_type,
            payload=payload,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        item_file = self.queue_dir / f"{item.item_id}.json"
        item_file.write_text(json.dumps(item.__dict__, indent=2))
        return item

    def dequeue(self) -> list[QueueItem]:
        items = []
        for f in sorted(self.queue_dir.glob("*.json")):
            data = json.loads(f.read_text())
            items.append(QueueItem(**data))
        return items

    def remove(self, item_id: str):
        item_file = self.queue_dir / f"{item_id}.json"
        item_file.unlink(missing_ok=True)

    def increment_retry(self, item_id: str):
        item_file = self.queue_dir / f"{item_id}.json"
        if not item_file.exists():
            return
        data = json.loads(item_file.read_text())
        data["retry_count"] = data.get("retry_count", 0) + 1
        item_file.write_text(json.dumps(data, indent=2))

    def purge_expired(self, max_retries: int = 10):
        for f in self.queue_dir.glob("*.json"):
            data = json.loads(f.read_text())
            if data.get("retry_count", 0) >= max_retries:
                f.unlink(missing_ok=True)

    @property
    def size(self) -> int:
        return len(list(self.queue_dir.glob("*.json")))
