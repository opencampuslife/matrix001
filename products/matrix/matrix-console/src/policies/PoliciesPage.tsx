import { useState } from "react";

export function PoliciesPage() {
  const [policies, setPolicies] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadPolicies = () => {
    setLoading(true);
    // Load from local policy export
    fetch("/matrix/api/capabilities/issue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_id: "did:matrix:mother:root",
        roles: ["campus_edge_assistant"],
        allowed_knowledge: ["kb.admission.public", "kb.campus.faq"],
        allowed_tools: ["local_rag.search", "local_summary.generate"],
        denied_tools: ["remote_write", "payment", "admin_delete"],
        offline_allowed: true,
        offline_ttl_hours: 168,
        max_offline_actions: 500,
        policy_hash: "0xmatrix_policy_v1",
      }),
    })
      .then((r) => r.json())
      .then((data) => {
        setPolicies(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  return (
    <div>
      <h2 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px" }}>
        Policies & Capabilities
      </h2>

      <button
        onClick={loadPolicies}
        disabled={loading}
        style={{
          padding: "10px 20px",
          background: "#1d4ed8",
          color: "#fff",
          border: "none",
          borderRadius: "8px",
          cursor: "pointer",
          fontSize: "14px",
          fontWeight: 600,
          marginBottom: "24px",
        }}
      >
        {loading ? "Loading..." : "Issue Test Capability"}
      </button>

      {policies && (
        <div style={{
          background: "#fff",
          border: "1px solid #d8dee9",
          borderRadius: "12px",
          padding: "24px",
        }}>
          <h3 style={{ marginTop: 0, fontSize: "16px" }}>
            Capability Token
          </h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
            <tbody>
              {Object.entries(policies).map(([key, value]) => (
                <tr key={key} style={{ borderBottom: "1px solid #e2e8f0" }}>
                  <td style={{ padding: "8px 12px", fontWeight: 600, color: "#334155", width: "200px" }}>
                    {key}
                  </td>
                  <td style={{ padding: "8px 12px", fontFamily: "monospace", fontSize: "13px" }}>
                    {Array.isArray(value) ? value.join(", ") : String(value ?? "")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{
        marginTop: "24px",
        padding: "16px",
        background: "#f0fdf4",
        border: "1px solid #86efac",
        borderRadius: "8px",
        fontSize: "13px",
        color: "#166534",
      }}>
        <strong>Policy Rules:</strong>
        <ul style={{ margin: "8px 0 0", paddingLeft: "20px" }}>
          <li>DENY takes priority over ALLOW</li>
          <li>Critical tools (remote_write, payment, admin_delete) require explicit allow</li>
          <li>Offline capability expires after TTL hours</li>
          <li>Max offline actions enforced per capability</li>
        </ul>
      </div>
    </div>
  );
}
