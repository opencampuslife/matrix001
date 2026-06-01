import { useState } from "react";

interface AuditEntry {
  event_id: string;
  agent_id: string;
  action: string;
  timestamp: string;
  result: string;
  capability_id: string;
  knowledge_version: string;
  action_detail: Record<string, any>;
}

const MOCK_AUDIT: AuditEntry[] = [
  {
    event_id: "evt-001",
    agent_id: "did:matrix:child:abc123",
    action: "rag.query",
    timestamp: "2026-06-01T08:30:00Z",
    result: "allowed",
    capability_id: "cap_abc",
    knowledge_version: "matrix-kb-2026.06.01.001",
    action_detail: { query_hash: "abc...", results_count: 3 },
  },
  {
    event_id: "evt-002",
    agent_id: "did:matrix:child:abc123",
    action: "summary.generate",
    timestamp: "2026-06-01T08:31:00Z",
    result: "allowed",
    capability_id: "cap_abc",
    knowledge_version: "matrix-kb-2026.06.01.001",
    action_detail: {},
  },
  {
    event_id: "evt-003",
    agent_id: "did:matrix:child:xyz789",
    action: "tool.invoke",
    timestamp: "2026-06-01T09:00:00Z",
    result: "denied",
    capability_id: "cap_xyz",
    knowledge_version: "matrix-kb-2026.05.29.003",
    action_detail: { tool: "remote_write", reason: "tool is denied" },
  },
  {
    event_id: "evt-004",
    agent_id: "did:matrix:child:abc123",
    action: "audit.upload",
    timestamp: "2026-06-01T12:00:00Z",
    result: "allowed",
    capability_id: "cap_abc",
    knowledge_version: "",
    action_detail: { entries_uploaded: 47 },
  },
];

export function AuditPage() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");

  const filtered = filter === "all"
    ? MOCK_AUDIT
    : MOCK_AUDIT.filter((e) => e.result === filter);

  return (
    <div>
      <h2 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px" }}>
        Audit Log
      </h2>

      <div style={{ marginBottom: "16px", display: "flex", gap: "8px" }}>
        {["all", "allowed", "denied", "error"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "6px 14px",
              background: filter === f ? "#1d4ed8" : "#e2e8f0",
              color: filter === f ? "#fff" : "#334155",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: 600,
            }}
          >
            {f.toUpperCase()}
          </button>
        ))}
      </div>

      <table style={{
        width: "100%",
        borderCollapse: "separate",
        borderSpacing: 0,
        background: "#fff",
        border: "1px solid #d8dee9",
        borderRadius: "12px",
        overflow: "hidden",
      }}>
        <thead>
          <tr style={{ background: "#f8fafc" }}>
            <th style={thStyle}>Event ID</th>
            <th style={thStyle}>Agent</th>
            <th style={thStyle}>Action</th>
            <th style={thStyle}>Result</th>
            <th style={thStyle}>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((e) => (
            <>
              <tr
                key={e.event_id}
                onClick={() => setExpanded(expanded === e.event_id ? null : e.event_id)}
                style={{
                  borderBottom: "1px solid #e2e8f0",
                  cursor: "pointer",
                  background: expanded === e.event_id ? "#f8fafc" : "#fff",
                }}
              >
                <td style={tdStyle}>
                  <code style={{ fontSize: "11px" }}>{e.event_id}</code>
                </td>
                <td style={tdStyle}>{e.agent_id.split(":")[3] || e.agent_id}</td>
                <td style={tdStyle}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: "999px",
                    fontSize: "11px",
                    fontWeight: 600,
                    background: "#eef2ff",
                    color: "#3730a3",
                  }}>
                    {e.action}
                  </span>
                </td>
                <td style={tdStyle}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: "999px",
                    fontSize: "11px",
                    fontWeight: 600,
                    background: e.result === "allowed" ? "#ecfdf5" : "#fef2f2",
                    color: e.result === "allowed" ? "#047857" : "#b91c1c",
                  }}>
                    {e.result.toUpperCase()}
                  </span>
                </td>
                <td style={tdStyle}>
                  {new Date(e.timestamp).toLocaleString()}
                </td>
              </tr>
              {expanded === e.event_id && (
                <tr key={`${e.event_id}-detail`} style={{ background: "#f8fafc" }}>
                  <td colSpan={5} style={{ padding: "16px 24px", fontSize: "13px" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "8px" }}>
                      <div><strong>Capability:</strong> {e.capability_id}</div>
                      <div><strong>Knowledge Version:</strong> {e.knowledge_version || "N/A"}</div>
                      {Object.entries(e.action_detail).map(([k, v]) => (
                        <div key={k}><strong>{k}:</strong> {JSON.stringify(v)}</div>
                      ))}
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>

      <div style={{
        marginTop: "16px",
        fontSize: "13px",
        color: "#64748b",
      }}>
        Showing {filtered.length} of {MOCK_AUDIT.length} entries
      </div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: "12px 14px",
  textAlign: "left",
  fontWeight: 700,
  fontSize: "13px",
  color: "#0f172a",
};

const tdStyle: React.CSSProperties = {
  padding: "12px 14px",
  fontSize: "13px",
  verticalAlign: "top",
};
