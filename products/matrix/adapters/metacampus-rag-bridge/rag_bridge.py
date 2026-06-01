"""
Metacampus RAG Bridge — optional online fallback bridge between Matrix
child agents and the original product's RAG service.

This bridge is ONLY used when the child agent is online and needs
supplementary knowledge. It does NOT create an offline dependency.

The Matrix child agent always prioritizes its local encrypted knowledge.
This bridge is a fallback convenience.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BridgeConfig:
    rag_service_url: str = "http://localhost:8000/api/rag/search"
    fallback_enabled: bool = False
    timeout_seconds: int = 5
    max_results: int = 3


class RAGBridge:
    """Online RAG bridge to original product. Offline-safe by design."""

    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()

    def search(self, query: str, roles: list[str] | None = None,
               top_k: int = 3) -> list[dict]:
        """
        Search original product RAG online.
        Returns empty list if offline or config disables fallback.
        """
        if not self.config.fallback_enabled:
            return []

        try:
            import urllib.request
            payload = json.dumps({
                "query": query,
                "top_k": min(top_k, self.config.max_results),
                "roles": roles or [],
            }).encode()

            req = urllib.request.Request(
                self.config.rag_service_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            import socket
            socket.setdefaulttimeout(self.config.timeout_seconds)

            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                return result.get("results", [])

        except Exception:
            return []

    def is_available(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(
                self.config.rag_service_url.replace("/search", "/health"),
                method="GET",
            )
            import socket
            socket.setdefaulttimeout(2)
            with urllib.request.urlopen(req) as resp:
                return resp.status == 200
        except Exception:
            return False

    def bridge_search(self, query: str, local_results: list[dict],
                      roles: list[str] | None = None) -> list[dict]:
        """
        Try online RAG for supplementary results. Always includes local results first.
        Online results are annotated as 'remote_fallback'.
        """
        combined = list(local_results)

        if not self.config.fallback_enabled:
            return combined

        online_results = self.search(query, roles=roles)
        for r in online_results:
            r["source"] = "remote_fallback"
            r["priority"] = "supplementary"
            combined.append(r)

        return combined
