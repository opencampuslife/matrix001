import { useState } from "react";

interface KnowledgeVersion {
  version: string;
  merkle_root: string;
  package_count: number;
  issuer: string;
  issued_at: string;
  status: "active" | "revoked" | "pending";
}

const MOCK_VERSIONS: KnowledgeVersion[] = [
  {
    version: "matrix-kb-2026.06.01.001",
    merkle_root: "0x" + "a".repeat(8) + "..." + "b".repeat(8),
    package_count: 3,
    issuer: "did:matrix:mother:root",
    issued_at: "2026-06-01T00:00:00Z",
    status: "active",
  },
  {
    version: "matrix-kb-2026.05.29.003",
    merkle_root: "0x" + "c".repeat(8) + "..." + "d".repeat(8),
    package_count: 2,
    issuer: "did:matrix:mother:root",
    issued_at: "2026-05-29T12:00:00Z",
    status: "active",
  },
];

export function KnowledgeVersionsPage() {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div>
      <h2 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px" }}>
        Knowledge Versions
      </h2>

      <div style={{ display: "grid", gap: "16px" }}>
        {MOCK_VERSIONS.map((v) => (
          <div
            key={v.version}
            onClick={() => setSelected(selected === v.version ? null : v.version)}
            style={{
              background: "#fff",
              border: selected === v.version ? "2px solid #1d4ed8" : "1px solid #d8dee9",
              borderRadius: "12px",
              padding: "20px",
              cursor: "pointer",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: "16px", fontFamily: "monospace" }}>
                  {v.version}
                </div>
                <div style={{ fontSize: "13px", color: "#4b5563", marginTop: "4px" }}>
                  Issuer: {v.issuer} | Packages: {v.package_count}
                </div>
              </div>
              <span style={{
                padding: "4px 10px",
                borderRadius: "999px",
                fontSize: "12px",
                fontWeight: 600,
                background: v.status === "active" ? "#ecfdf5" : "#fef2f2",
                color: v.status === "active" ? "#047857" : "#b91c1c",
              }}>
                {v.status.toUpperCase()}
              </span>
            </div>

            {selected === v.version && (
              <div style={{
                marginTop: "16px",
                padding: "16px",
                background: "#f8fafc",
                borderRadius: "8px",
                fontSize: "13px",
              }}>
                <div><strong>Merkle Root:</strong> <code>{v.merkle_root}</code></div>
                <div><strong>Issued:</strong> {new Date(v.issued_at).toLocaleString()}</div>
                <div style={{ marginTop: "12px" }}>
                  <strong>Package List:</strong>
                  <ul style={{ margin: "4px 0", paddingLeft: "20px" }}>
                    <li>kpkg_admission_public_001 (admission policies)</li>
                    <li>kpkg_campus_faq_001 (campus FAQ)</li>
                    <li>kpkg_canteen_info_001 (canteen information)</li>
                  </ul>
                </div>
                <div style={{
                  marginTop: "12px",
                  padding: "8px 12px",
                  background: "#fef3c7",
                  borderRadius: "6px",
                  color: "#92400e",
                }}>
                  Chain anchor: knowledge_version = {v.version}, merkle_root = {v.merkle_root}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
