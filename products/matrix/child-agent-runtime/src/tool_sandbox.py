"""
Tool Sandbox — controls which local tools a child agent may invoke
based on the capability token's allowed_tools and denied_tools.

Tools are isolated function calls with no external network access.
"""

import json
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ToolDefinition:
    tool_id: str
    description: str
    category: str  # "search", "generate", "system", "admin"
    risk_level: str  # "low", "medium", "high", "critical"
    handler: Optional[Callable] = None


DEFAULT_TOOLS: dict[str, ToolDefinition] = {
    "local_rag.search": ToolDefinition(
        tool_id="local_rag.search",
        description="Search local knowledge base for relevant chunks",
        category="search",
        risk_level="low",
    ),
    "local_summary.generate": ToolDefinition(
        tool_id="local_summary.generate",
        description="Generate a summary from retrieved chunks",
        category="generate",
        risk_level="low",
    ),
    "local_qa.answer": ToolDefinition(
        tool_id="local_qa.answer",
        description="Answer a question using local knowledge",
        category="generate",
        risk_level="low",
    ),
    "audit.write": ToolDefinition(
        tool_id="audit.write",
        description="Write an audit log entry locally",
        category="system",
        risk_level="low",
    ),
    "remote_write": ToolDefinition(
        tool_id="remote_write",
        description="Write data to remote server (restricted)",
        category="admin",
        risk_level="critical",
    ),
    "payment": ToolDefinition(
        tool_id="payment",
        description="Process payments (restricted)",
        category="admin",
        risk_level="critical",
    ),
    "admin_delete": ToolDefinition(
        tool_id="admin_delete",
        description="Delete data (restricted)",
        category="admin",
        risk_level="critical",
    ),
}


class ToolSandbox:
    def __init__(self, allowed_tools: list[str] | None = None,
                 denied_tools: list[str] | None = None):
        self.allowed_tools: set[str] = set(allowed_tools or [])
        self.denied_tools: set[str] = set(denied_tools or [])
        self.registered_tools: dict[str, ToolDefinition] = dict(DEFAULT_TOOLS)
        self.invocation_count: dict[str, int] = {}

    def register_tool(self, tool: ToolDefinition):
        self.registered_tools[tool.tool_id] = tool

    def can_invoke(self, tool_id: str) -> tuple[bool, str]:
        if tool_id not in self.registered_tools:
            return False, f"unknown tool: {tool_id}"

        tool = self.registered_tools[tool_id]

        if tool.risk_level == "critical":
            if tool_id not in self.allowed_tools:
                return False, f"critical tool {tool_id} requires explicit allow"

        if tool_id in self.denied_tools:
            return False, f"tool {tool_id} is denied"

        if self.allowed_tools and tool_id not in self.allowed_tools:
            return False, f"tool {tool_id} not in allowed list"

        return True, ""

    def invoke(self, tool_id: str, **kwargs) -> dict:
        can, reason = self.can_invoke(tool_id)
        if not can:
            return {"error": reason, "tool_id": tool_id}

        tool = self.registered_tools[tool_id]
        self.invocation_count[tool_id] = self.invocation_count.get(tool_id, 0) + 1

        if tool.handler:
            try:
                result = tool.handler(**kwargs)
                return {"result": result, "tool_id": tool_id, "status": "success"}
            except Exception as e:
                return {"error": str(e), "tool_id": tool_id, "status": "error"}

        return {"result": f"tool {tool_id} invoked (stub)", "tool_id": tool_id, "status": "success"}

    def get_available_tools(self) -> list[dict]:
        available = []
        for tool_id, tool in self.registered_tools.items():
            can, _ = self.can_invoke(tool_id)
            available.append({
                "tool_id": tool.tool_id,
                "description": tool.description,
                "category": tool.category,
                "risk_level": tool.risk_level,
                "available": can,
            })
        return available
