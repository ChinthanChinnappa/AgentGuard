import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "./api";

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch((reason: Error) => setError(reason.message));
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand-mark">AG</div>
        <div>
          <p className="eyebrow">Agent evaluation and observability</p>
          <h1>AgentGuard</h1>
        </div>
        <span className="phase-badge">Phase 1</span>
      </header>
      <section className="intro">
        <p className="eyebrow">System status</p>
        <h2>Observe what the agent actually does.</h2>
        <p className="lede">The workspace is connected and ready for trace collection, deterministic evaluation, and policy controls.</p>
      </section>
      <section className="status-panel" aria-live="polite">
        <div>
          <span className={`status-dot ${health ? "online" : "pending"}`} />
          <strong>{error ? "Backend unavailable" : health ? "Backend connected" : "Checking backend"}</strong>
        </div>
        <div className="status-details">
          <span>API {health?.status ?? (error ? "error" : "pending")}</span>
          <span>Database {health?.database ?? (error ? "error" : "pending")}</span>
        </div>
        {error && <p className="error-message">{error}</p>}
      </section>
    </main>
  );
}
