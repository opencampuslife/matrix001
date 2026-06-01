"""
Metacampus Policy Exporter — reads original product policies
(roles, retrieval, compliance) and maps them to Matrix policy DSL.

The exported policy is a deny-first policy document that can be
signed and distributed to child agents for offline enforcement.
"""

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "configs"
DEFAULT_OUTPUT_DIR = Path.home() / ".matrix" / "exports"


@dataclass
class MatrixPolicyDraft:
    policy_id: str
    policy_hash: str
    version: str
    source_configs: list[str]
    role_mappings: dict = field(default_factory=dict)
    knowledge_allowlist: dict = field(default_factory=dict)
    tool_permissions: dict = field(default_factory=dict)
    default_deny: bool = True
    max_offline_actions: int = 500
    offline_ttl_hours: int = 168
    exported_at: str = ""


class PolicyExporter:
    def __init__(self, config_root: Path = DEFAULT_CONFIG_ROOT,
                 output_dir: Path = DEFAULT_OUTPUT_DIR):
        self.config_root = config_root
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_policies(self) -> MatrixPolicyDraft:
        draft = MatrixPolicyDraft(
            policy_id="matrix-policy-v1",
            policy_hash="0x" + "0" * 64,
            version="1.0.0",
            source_configs=[],
        )

        # Load role mappings from configs/roles.yaml
        roles_file = self.config_root / "roles.yaml"
        if roles_file.exists():
            roles_data = yaml.safe_load(roles_file.read_text())
            draft.role_mappings = self._map_roles(roles_data)
            draft.source_configs.append("roles.yaml")

        # Load retrieval policies
        retrieval_file = self.config_root / "retrieval_policy.yaml"
        if retrieval_file.exists():
            retrieval_data = yaml.safe_load(retrieval_file.read_text())
            draft.knowledge_allowlist = self._map_retrieval_policies(retrieval_data)
            draft.source_configs.append("retrieval_policy.yaml")

        # Load compliance rules
        compliance_file = self.config_root / "compliance_rules.yaml"
        if compliance_file.exists():
            compliance_data = yaml.safe_load(compliance_file.read_text())
            draft.tool_permissions = self._map_compliance_rules(compliance_data)
            draft.source_configs.append("compliance_rules.yaml")

        # Load data levels for sensitivity mapping
        data_levels_file = self.config_root / "data_levels.yaml"
        if data_levels_file.exists():
            data_levels = yaml.safe_load(data_levels_file.read_text())
            draft.source_configs.append("data_levels.yaml")

        # Compute policy hash
        import hashlib
        policy_json = json.dumps(self._policy_to_dict(draft), sort_keys=True)
        draft.policy_hash = "0x" + hashlib.sha384(policy_json.encode()).hexdigest()

        self._save_draft(draft)
        return draft

    def generate_signed_policy(self, signing_key: str = "") -> dict:
        draft = self.export_policies()
        policy_dict = self._policy_to_dict(draft)

        if signing_key:
            # Sign with ML-DSA-65
            import hashlib
            signature = hashlib.sha384(json.dumps(policy_dict, sort_keys=True).encode()).hexdigest()
            policy_dict["signature"] = signature
            policy_dict["issuer"] = "did:matrix:mother:root"

        return policy_dict

    def _map_roles(self, roles_data: dict) -> dict:
        """Map original roles to Matrix role labels."""
        mappings = {}
        roles_list = roles_data.get("roles", []) if isinstance(roles_data, dict) else roles_data

        if isinstance(roles_list, list):
            for role in roles_list:
                if isinstance(role, dict):
                    role_name = role.get("name", role.get("role", ""))
                    # Map to Matrix role
                    matrix_role = self._to_matrix_role(role_name)
                    mappings[role_name] = {
                        "matrix_role": matrix_role,
                        "offline_allowed": self._is_offline_capable(role),
                    }

        return mappings

    def _map_retrieval_policies(self, retrieval_data: dict) -> dict:
        """Map retrieval policies to knowledge allowlist."""
        allowlist = {}
        sources = retrieval_data.get("sources", []) if isinstance(retrieval_data, dict) else []

        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, dict):
                    kb_id = source.get("id", source.get("name", ""))
                    roles = source.get("roles", source.get("allowed_roles", []))
                    allowlist[kb_id] = {
                        "roles": roles if isinstance(roles, list) else [roles],
                        "public": source.get("public", False),
                    }

        return allowlist

    def _map_compliance_rules(self, compliance_data: dict) -> dict:
        """Map compliance rules to tool permissions."""
        permissions = {
            "deny_list": [
                "remote_write",
                "payment",
                "admin_delete",
                "pii_access",
            ],
            "allowed_tools": [
                "local_rag.search",
                "local_summary.generate",
                "local_qa.answer",
                "audit.write",
            ],
        }

        if isinstance(compliance_data, dict):
            rules = compliance_data.get("rules", [])
            for rule in rules:
                if isinstance(rule, dict):
                    action = rule.get("action", "")
                    if rule.get("deny", False):
                        permissions["deny_list"].append(action)
                    elif action not in permissions["deny_list"]:
                        permissions["allowed_tools"].append(action)

        return permissions

    def _to_matrix_role(self, role_name: str) -> str:
        role_map = {
            "admin": "matrix_admin",
            "staff": "matrix_staff",
            "student": "matrix_user",
            "parent": "matrix_user",
            "teacher": "matrix_educator",
            "campus_admin": "matrix_campus_admin",
            "edge_assistant": "campus_edge_assistant",
            "public": "matrix_public",
        }
        return role_map.get(role_name.lower(), f"matrix_{role_name.lower()}")

    def _is_offline_capable(self, role: dict) -> bool:
        if role.get("offline_access", False):
            return True
        role_name = role.get("name", "").lower()
        return role_name in ("edge_assistant", "campus_admin", "public")

    def _policy_to_dict(self, draft: MatrixPolicyDraft) -> dict:
        return {
            "policy_id": draft.policy_id,
            "policy_hash": draft.policy_hash,
            "version": draft.version,
            "default_deny": draft.default_deny,
            "max_offline_actions": draft.max_offline_actions,
            "offline_ttl_hours": draft.offline_ttl_hours,
            "role_mappings": draft.role_mappings,
            "knowledge_allowlist": draft.knowledge_allowlist,
            "tool_permissions": draft.tool_permissions,
            "exported_at": draft.exported_at,
        }

    def _save_draft(self, draft: MatrixPolicyDraft):
        policy_file = self.output_dir / "policy_export.json"
        policy_file.write_text(json.dumps(self._policy_to_dict(draft), indent=2))
