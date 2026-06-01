import { useEffect, useState } from "react";

interface Agent {
  agent_id: string;
  agent_type: string;
  parent_id: string;
  roles: string[];
  active: boolean;
  created_at: string;
}

export function TopologyPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/matrix/api/agents")
      .then((r) => r.json())
      .then((data) => {
        setAgents(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((e) => {
        setError("Unable to connect to Mother Agent at localhost:18080");
        setLoading(false);
      });
  }, []);

  if (loading) return <div style={{ color: "#4b5563" }}>Loading agent topology...</div>;
  if (error) return <div style={{ color: "#b91c1c" }}>{error}</div>;

  const motherAgents = agents.filter((a) => a.agent_type === "mother");
  const childAgents = agents.filter((a) => a.agent_type === "child");

  return (
    <div>
      <h2 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px" }}>
        Agent Topology
      </h2>

      {agents.length === 0 ? (
        <div style={{
          background: "#f8fafc",
          border: "1px dashed #94a3b8",
          borderRadius: "12px",
          padding: "48px",
          textAlign: "center",
          color: "#64748b",
        }}>
          No agents registered yet.
          <br />
          Run <code style={{ background: "#e2e8f0", padding: "2px 6px", borderRadius: "4px" }}>
            python -m child_agent_runtime register
          </code> to register the first child agent.
        </div>
      ) : (
        <>
          <section style={{ marginBottom: "32px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px", color: "#1d4ed8" }}>
              Mother Agents ({motherAgents.length})
            </h3>
            <div style={{ display: "grid", gap: "12px" }}>
              {motherAgents.map((a) => (
                <AgentCard key={a.agent_id} agent={a} />
              ))}
            </div>
          </section>

          <section>
            <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px", color: "#6d28d9" }}>
              Child Agents ({childAgents.length})
            </h3>
            <div style={{ display: "grid", gap: "12px" }}>
              {childAgents.map((a) => (
                <AgentCard key={a.agent_id} agent={a} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  return (
    <div style={{
      background: "#fff",
      border: "1px solid #d8dee9",
      borderRadius: "12px",
      padding: "16px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
    }}>
      <div>
        <div style={{ fontWeight: 600, marginBottom: "4px" }}>
          <span style={{
            display: "inline-block",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: agent.active ? "#047857" : "#b91c1c",
            marginRight: "8px",
          }} />
          {agent.agent_id}
        </div>
        <div style={{ fontSize: "13px", color: "#4b5563" }}>
          Type: {agent.agent_type} | Roles: {agent.roles.join(", ")}
        </div>
        <div style={{ fontSize: "12px", color: "#94a3b8" }}>
          Registered: {new Date(agent.created_at).toLocaleString()}
        </div>
      </div>
      <div>
        <span style={{
          padding: "4px 10px",
          borderRadius: "999px",
          fontSize: "12px",
          fontWeight: 600,
          background: agent.active ? "#ecfdf5" : "#fef2f2",
          color: agent.active ? "#047857" : "#b91c1c",
        }}>
          {agent.active ? "ACTIVE" : "INACTIVE"}
        </span>
      </div>
    </div>
  );
}
