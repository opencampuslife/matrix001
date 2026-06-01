"""
Local Policy Engine — evaluates whether an offline action is permitted
based on a signed capability token and local policy rules.

Key principle: DENY takes precedence over ALLOW.
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DEFAULT_POLICY_DIR = Path.home() / ".matrix" / "policies"


@dataclass
class CapabilityToken:
    capability_id: str
    agent_id: str
    roles: list[str] = field(default_factory=list)
    allowed_knowledge: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    offline_allowed: bool = False
    offline_expiry: str = ""
    max_offline_actions: int = 500
    policy_hash: str = ""
    issuer_signature: str = ""

    def is_expired(self) -> bool:
        if not self.offline_expiry:
            return False
        try:
            expiry = datetime.fromisoformat(self.offline_expiry.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > expiry
        except ValueError:
            return True


@dataclass
class PolicyResult:
    allowed: bool
    reason: str = ""
    matched_rule: str = ""


class LocalPolicyEngine:
    DENY_PRIORITY_ACTIONS = [
        "remote_write",
        "payment",
        "admin_delete",
        "pii_access",
        "capability_escalate",
    ]

    def __init__(self, policy_dir: Path = DEFAULT_POLICY_DIR):
        self.policy_dir = policy_dir
        self.policy_dir.mkdir(parents=True, exist_ok=True)
        self.capability: Optional[CapabilityToken] = None
        self.offline_action_count: int = 0

    def load_capability(self, capability_data: dict) -> CapabilityToken:
        self.capability = CapabilityToken(**capability_data)
        self.offline_action_count = 0
        return self.capability

    def get_capability(self) -> Optional[CapabilityToken]:
        return self.capability

    def check_action(self, action: str, knowledge_id: str = "",
                     tool_name: str = "") -> PolicyResult:
        if self.capability is None:
            return PolicyResult(False, "no capability loaded")

        if not self.capability.offline_allowed:
            return PolicyResult(False, "offline not allowed by capability", "offline_allowed=false")

        if self.capability.is_expired():
            return PolicyResult(False, "capability token expired", "offline_expiry")

        if self.offline_action_count >= self.capability.max_offline_actions:
            return PolicyResult(False, "max offline actions exceeded", "max_offline_actions")

        # Deny check takes priority
        for denied in self.capability.denied_tools:
            if tool_name and denied in tool_name:
                return PolicyResult(False, f"tool {tool_name} is denied", "denied_tools")
        for denied in self.DENY_PRIORITY_ACTIONS:
            if tool_name and denied in tool_name:
                return PolicyResult(False, f"action {tool_name} is system-denied", "system_deny_list")

        if knowledge_id and knowledge_id not in self.capability.allowed_knowledge:
            return PolicyResult(False, f"knowledge {knowledge_id} not in allowed list", "allowed_knowledge")

        if tool_name and tool_name not in self.capability.allowed_tools:
            return PolicyResult(False, f"tool {tool_name} not in allowed list", "allowed_tools")

        self.offline_action_count += 1
        return PolicyResult(True, "allowed")

    def verify_capability_signature(self, signing_public_key: str) -> bool:
        if self.capability is None:
            return False
        # TODO: verify ML-DSA-65 signature
        return True

    def save_capability(self):
        if self.capability is None:
            return
        cap_file = self.policy_dir / "capability.json"
        cap_file.write_text(json.dumps(self.capability.__dict__, indent=2))
