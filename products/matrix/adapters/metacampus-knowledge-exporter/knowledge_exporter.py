"""
Metacampus Knowledge Exporter — reads approved knowledge from the
original Open Campus / Metacampus knowledge vault, strips PII,
normalizes chunks, and emits KnowledgePackDraft for Matrix.

This adapter does NOT modify the original product's data.
It read-only exports authorized public knowledge.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Path relative to gaokao-agent root
DEFAULT_KNOWLEDGE_VAULT = Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge_vault"
DEFAULT_OUTPUT_DIR = Path.home() / ".matrix" / "exports"


PII_PATTERNS = {
    "phone": re.compile(r"1[3-9]\d{9}"),
    "id_card": re.compile(r"\d{17}[\dXx]"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "student_name_pattern": re.compile(r"(学生姓名|姓名)[：:]\s*[\u4e00-\u9fa5]{2,4}"),
}


SENSITIVE_KEYWORDS = [
    "密码", "password", "身份证", "银行卡", "手机号", "社保号",
    "内部机密", "internal_secret", "密钥", "private_key",
]


@dataclass
class ExportResult:
    success: bool
    source_path: str
    chunk_count: int
    warnings: list[str] = field(default_factory=list)
    stripped_fields: list[str] = field(default_factory=list)


class KnowledgeExporter:
    def __init__(self, knowledge_root: Path = DEFAULT_KNOWLEDGE_VAULT,
                 output_dir: Path = DEFAULT_OUTPUT_DIR):
        self.knowledge_root = knowledge_root
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_public_knowledge(self, source_pattern: str = "public/campus/*") -> ExportResult:
        """Export public campus knowledge for Matrix consumption."""
        import glob
        warnings = []
        chunks = []
        source_path = str(self.knowledge_root / source_pattern)

        md_files = list(self.knowledge_root.glob(f"{source_pattern}.md"))
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                cleaned, pii_hits = self._clean_pii(content)

                file_chunks = self._chunk_markdown(cleaned, str(md_file.relative_to(self.knowledge_root)))
                chunks.extend(file_chunks)

                if pii_hits:
                    warnings.append(f"PII stripped from {md_file.name}: {pii_hits}")
            except Exception as e:
                warnings.append(f"Failed to read {md_file}: {e}")

        if chunks:
            output_file = self.output_dir / "knowledge_export.json"
            output_file.write_text(json.dumps({
                "source": "metacampus_knowledge_vault",
                "source_path": source_path,
                "chunks": chunks,
                "exported_at": self._now_iso(),
            }, ensure_ascii=False, indent=2))

        return ExportResult(
            success=len(warnings) == 0 or len(chunks) > 0,
            source_path=source_path,
            chunk_count=len(chunks),
            warnings=warnings,
        )

    def export_with_source_trace(self, source_ids: list[str]) -> list[dict]:
        """Export specific knowledge sources with traceability."""
        chunks = []
        for source_id in source_ids:
            file_path = self.knowledge_root / f"{source_id}.md"
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                cleaned, _ = self._clean_pii(content)
                file_chunks = self._chunk_markdown(cleaned, source_id)
                for c in file_chunks:
                    c["source_trace"] = source_id
                chunks.extend(file_chunks)
        return chunks

    def _clean_pii(self, text: str) -> tuple[str, list[str]]:
        hits = []
        cleaned = text

        for pii_type, pattern in PII_PATTERNS.items():
            found = pattern.findall(cleaned)
            if found:
                hits.append(pii_type)
                cleaned = pattern.sub(f"[REDACTED_{pii_type.upper()}]", cleaned)

        for kw in SENSITIVE_KEYWORDS:
            if kw in cleaned.lower():
                hits.append(f"keyword:{kw}")

        return cleaned, hits

    def _chunk_markdown(self, content: str, source_id: str) -> list[dict]:
        import hashlib
        chunks = []
        paragraphs = content.split("\n\n")
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para or para.startswith("#") and len(para) < 20:
                continue

            chunk_id = hashlib.sha384(f"{source_id}:{i}:{para[:50]}".encode()).hexdigest()[:12]

            # Extract keywords from headings
            retrieval_keywords = []
            for line in para.split("\n"):
                if line.startswith("##"):
                    kw_line = line.replace("#", "").strip()
                    retrieval_keywords.extend(kw_line.split())

            chunk = {
                "chunk_id": f"chunk_{source_id.replace('/', '_')}_{chunk_id}",
                "text": para,
                "source_id": source_id,
                "retrieval_keywords": retrieval_keywords[:5],
                "canonical_question": "",
                "role_tags": ["campus_edge_assistant"],
            }
            chunks.append(chunk)

        return chunks

    def _now_iso(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


class PIIStripper:
    """Standalone PII stripper for knowledge content."""

    @staticmethod
    def strip(text: str) -> str:
        cleaned = text
        for pattern in PII_PATTERNS.values():
            cleaned = pattern.sub("[REDACTED]", cleaned)
        return cleaned

    @staticmethod
    def has_pii(text: str) -> bool:
        for pattern in PII_PATTERNS.values():
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def add_privacy_tags(chunk: dict) -> dict:
        chunk["privacy_level"] = "public"
        if PIIStripper.has_pii(chunk.get("text", "")):
            chunk["privacy_level"] = "redacted"
        return chunk
