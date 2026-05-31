import { useState } from "react";
import { TopologyPage } from "../topology/TopologyPage";
import { PoliciesPage } from "../policies/PoliciesPage";
import { KnowledgeVersionsPage } from "../knowledge-versions/KnowledgeVersionsPage";
import { RevocationsPage } from "../revocations/RevocationsPage";
import { AuditPage } from "../audit/AuditPage";

type Page = "topology" | "policies" | "knowledge" | "revocations" | "audit";

const NAV_ITEMS: { id: Page; label: string; icon: string }[] = [
  { id: "topology", label: "Agent Topology", icon: "◉" },
  { id: "policies", label: "Policies", icon: "⚙" },
  { id: "knowledge", label: "Knowledge Versions", icon: "📦" },
  { id: "revocations", label: "Revocations", icon: "⊘" },
  { id: "audit", label: "Audit", icon: "📋" },
];

export function App() {
  const [page, setPage] = useState<Page>("topology");

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <nav style={{
        width: "220px",
        background: "#1e293b",
        color: "#e2e8f0",
        padding: "24px 0",
        flexShrink: 0,
      }}>
        <div style={{ padding: "0 20px 24px", borderBottom: "1px solid #334155", marginBottom: "16px" }}>
          <h1 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>
            Matrix Console
          </h1>
          <p style={{ fontSize: "12px", color: "#94a3b8", margin: "4px 0 0" }}>
            Open Campus Matrix
          </p>
        </div>
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => setPage(item.id)}
            style={{
              display: "block",
              width: "100%",
              textAlign: "left",
              padding: "10px 20px",
              background: page === item.id ? "#334155" : "transparent",
              color: page === item.id ? "#f1f5f9" : "#94a3b8",
              border: "none",
              cursor: "pointer",
              fontSize: "14px",
              fontFamily: "inherit",
            }}
          >
            <span style={{ marginRight: "8px" }}>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <main style={{ flex: 1, padding: "32px", overflow: "auto" }}>
        {page === "topology" && <TopologyPage />}
        {page === "policies" && <PoliciesPage />}
        {page === "knowledge" && <KnowledgeVersionsPage />}
        {page === "revocations" && <RevocationsPage />}
        {page === "audit" && <AuditPage />}
      </main>
    </div>
  );
}
