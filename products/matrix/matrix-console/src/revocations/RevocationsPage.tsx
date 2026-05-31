import { useEffect, useState } from "react";

interface Revocation {
  revocation_id: string;
  revocation_type: string;
  target_id: string;
  reason: string;
  effective_from: string;
  issued_at: string;
}

export function RevocationsPage() {
  const [revocations, setRevocations] = useState<Revocation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/matrix/api/revocations")
      .then((r) => r.json())
      .then((data) => {
        setRevocations(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const typeColors: Record<string, string> = {
    agent: "#b91c1c",
    capability: "#c2410c",
    knowledge_version: "#6d28d9",
    policy: "#1d4ed8",
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <h2 style={{ fontSize: "24px", fontWeight: 700, margin: 0 }}>
          Revocations
        </h2>
        <button style={{
          padding: "10px 20px",
          background: "#b91c1c",
          color: "#fff",
          border: "none",
          borderRadius: "8px",
          cursor: "pointer",
          fontSize: "14px",
          fontWeight: 600,
        }} onClick={() => {}}>
          + New Revocation
        </button>
      </div>

      {loading ? (
        <div style={{ color: "#4b5563" }}>Loading...</div>
      ) : revocations.length === 0 ? (
        <div style={{
          background: "#f8fafc",
          border: "1px dashed #94a3b8",
          borderRadius: "12px",
          padding: "48px",
          textAlign: "center",
          color: "#64748b",
        }}>
          No revocations issued.
        </div>
      ) : (
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
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Target</th>
              <th style={thStyle}>Reason</th>
              <th style={thStyle}>Effective</th>
            </tr>
          </thead>
          <tbody>
            {revocations.map((r) => (
              <tr key={r.revocation_id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                <td style={tdStyle}>
                  <code style={{ fontSize: "12px" }}>{r.revocation_id}</code>
                </td>
                <td style={tdStyle}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: "999px",
                    fontSize: "12px",
                    fontWeight: 600,
                    background: typeColors[r.revocation_type] + "15",
                    color: typeColors[r.revocation_type] || "#334155",
                  }}>
                    {r.revocation_type}
                  </span>
                </td>
                <td style={tdStyle}>
                  <code style={{ fontSize: "12px" }}>{r.target_id}</code>
                </td>
                <td style={tdStyle}>{r.reason}</td>
                <td style={tdStyle}>
                  {new Date(r.effective_from).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
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
