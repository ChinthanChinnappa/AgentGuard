import { useEffect, useMemo, useState } from "react";
import {
  evaluateTrace,
  fetchEvaluationConfigs,
  fetchHealth,
  fetchTrace,
  fetchTraceEvaluations,
  fetchTraces,
  generateDemoTraces,
  type EvaluationConfig,
  type EvaluationRecord,
  type HealthResponse,
  type TraceDetail,
  type TraceItem,
} from "./api";

const statusOptions = ["all", "running", "completed", "failed", "cancelled"] as const;

function formatTime(value?: string | null) {
  if (!value) return "?";
  return new Date(value).toLocaleString();
}

function formatDuration(ms?: number | null) {
  if (ms === null || typeof ms === "undefined") return "?";
  return `${Math.max(0, Math.round(ms))} ms`;
}

function statusClass(status: string) {
  const normalized = status.toLowerCase();
  return {
    completed: "status-success",
    failed: "status-error",
    fail: "status-error",
    running: "status-running",
    cancelled: "status-cancelled",
    pass: "status-success",
    needs_review: "status-running",
    incomplete: "status-default",
  }[normalized] ?? "status-default";
}

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [traces, setTraces] = useState<TraceItem[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [selectedTrace, setSelectedTrace] = useState<TraceDetail | null>(null);
  const [configs, setConfigs] = useState<EvaluationConfig[]>([]);
  const [configId, setConfigId] = useState<string | null>(null);
  const [evaluations, setEvaluations] = useState<EvaluationRecord[]>([]);
  const [selectedEvaluation, setSelectedEvaluation] = useState<EvaluationRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [evalLoading, setEvalLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<(typeof statusOptions)[number]>("all");
  const [error, setError] = useState<string | null>(null);

  const loadTraces = async (nextStatus = statusFilter) => {
    try {
      setLoading(true);
      const response = await fetchTraces({ status: nextStatus === "all" ? undefined : nextStatus });
      setTraces(response.items);
      if (!selectedTraceId && response.items.length > 0) {
        setSelectedTraceId(response.items[0].id);
      }
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load traces");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((reason: Error) => setHealthError(reason.message));
    fetchEvaluationConfigs()
      .then((items) => {
        setConfigs(items);
        if (items.length > 0) setConfigId(items[0].id);
      })
      .catch((reason: Error) => setError(reason.message));
    void loadTraces(statusFilter);
  }, []);

  useEffect(() => {
    void loadTraces(statusFilter);
  }, [statusFilter]);

  useEffect(() => {
    if (!selectedTraceId) {
      setSelectedTrace(null);
      return;
    }

    const fetchDetail = async () => {
      try {
        setDetailLoading(true);
        const trace = await fetchTrace(selectedTraceId);
        setSelectedTrace(trace);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Failed to load trace");
      } finally {
        setDetailLoading(false);
      }
    };

    void fetchDetail();
  }, [selectedTraceId]);

  useEffect(() => {
    if (!selectedTraceId) {
      setEvaluations([]);
      setSelectedEvaluation(null);
      return;
    }

    const loadEvals = async () => {
      try {
        setEvalLoading(true);
        const result = await fetchTraceEvaluations(selectedTraceId);
        setEvaluations(result.items);
        setSelectedEvaluation(result.items[0] ?? null);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Failed to load evaluations");
      } finally {
        setEvalLoading(false);
      }
    };

    void loadEvals();
  }, [selectedTraceId]);

  const traceCount = useMemo(() => traces.length, [traces]);

  const generateDemo = async () => {
    try {
      const demo = await generateDemoTraces();
      setSelectedTraceId(demo.success_trace_id);
      await loadTraces(statusFilter);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not generate demo traces");
    }
  };

  const runSelectedEvaluation = async () => {
    if (!selectedTraceId) return;
    try {
      setEvalLoading(true);
      const result = await evaluateTrace(selectedTraceId, configId ?? undefined);
      setEvaluations((current) => [result, ...current]);
      setSelectedEvaluation(result);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not evaluate trace");
    } finally {
      setEvalLoading(false);
    }
  };

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand-mark">AG</div>
        <div>
          <p className="eyebrow">Agent evaluation and observability</p>
          <h1>AgentGuard</h1>
        </div>
        <span className="phase-badge">Phase 4</span>
      </header>

      <section className="intro compact">
        <div>
          <p className="eyebrow">System status</p>
          <h2>Evaluation engine</h2>
        </div>
        <button type="button" className="primary-button" onClick={() => void generateDemo()}>
          Generate demo traces
        </button>
      </section>

      <section className="status-panel" aria-live="polite">
        <div>
          <span className={`status-dot ${health ? "online" : "pending"}`} />
          <strong>{healthError ? "Backend unavailable" : health ? "Backend connected" : "Checking backend"}</strong>
        </div>
        <div className="status-details">
          <span>API {health?.status ?? (healthError ? "error" : "pending")}</span>
          <span>Database {health?.database ?? (healthError ? "error" : "pending")}</span>
        </div>
        {healthError && <p className="error-message">{healthError}</p>}
      </section>

      <section className="trace-layout">
        <aside className="trace-list-panel">
          <div className="panel-header">
            <h3>Traces</h3>
            <span>{traceCount}</span>
          </div>

          <div className="toolbar">
            {statusOptions.map((option) => (
              <button
                key={option}
                type="button"
                className={statusFilter === option ? "filter-button active" : "filter-button"}
                onClick={() => setStatusFilter(option)}
              >
                {option}
              </button>
            ))}
          </div>

          {loading ? (
            <p className="empty-state">Loading traces?</p>
          ) : traces.length === 0 ? (
            <p className="empty-state">No traces found for this filter.</p>
          ) : (
            <ul className="trace-list">
              {traces.map((trace) => (
                <li key={trace.id}>
                  <button
                    type="button"
                    className={selectedTraceId === trace.id ? "trace-item selected" : "trace-item"}
                    onClick={() => setSelectedTraceId(trace.id)}
                  >
                    <div className="trace-item-header">
                      <span className={`pill ${statusClass(trace.status)}`}>{trace.status}</span>
                      <span className="muted">{formatDuration(trace.duration_ms)}</span>
                    </div>
                    <strong>{trace.task_name ?? trace.agent_name ?? trace.id}</strong>
                    <small>{trace.agent_name ?? "anonymous-agent"}</small>
                    <span>{formatTime(trace.started_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="trace-detail-panel">
          {detailLoading ? (
            <p className="empty-state">Loading trace details?</p>
          ) : !selectedTrace ? (
            <p className="empty-state">Select a trace to inspect its execution timeline.</p>
          ) : (
            <>
              <div className="detail-header">
                <div>
                  <p className="eyebrow">Trace summary</p>
                  <h3>{selectedTrace.task_name ?? "Unnamed task"}</h3>
                </div>
                <span className={`pill ${statusClass(selectedTrace.status)}`}>{selectedTrace.status}</span>
              </div>

              <div className="summary-grid">
                <div>
                  <label>Trace ID</label>
                  <strong>{selectedTrace.id}</strong>
                </div>
                <div>
                  <label>Agent</label>
                  <strong>{selectedTrace.agent_name ?? "?"}</strong>
                </div>
                <div>
                  <label>Started</label>
                  <strong>{formatTime(selectedTrace.started_at)}</strong>
                </div>
                <div>
                  <label>Duration</label>
                  <strong>{formatDuration(selectedTrace.duration_ms)}</strong>
                </div>
              </div>

              {selectedTrace.error_message && (
                <div className="alert-box error-box">
                  <strong>Error</strong>
                  <p>{selectedTrace.error_message}</p>
                </div>
              )}

              {selectedTrace.final_output && (
                <div className="alert-box success-box">
                  <strong>Final output</strong>
                  <pre>{selectedTrace.final_output}</pre>
                </div>
              )}

              <div className="timeline">
                {selectedTrace.spans.map((span) => (
                  <div key={span.id} className="timeline-item">
                    <div className="timeline-marker" />
                    <div className="timeline-content">
                      <div className="timeline-header">
                        <span className={`pill ${statusClass(span.status === "success" ? "completed" : span.status)}`}>
                          {span.status}
                        </span>
                        <strong>{span.operation_name}</strong>
                        {span.tool_name && <small>{span.tool_name}</small>}
                      </div>
                      <div className="timeline-meta">
                        <span>{span.span_type}</span>
                        <span>{formatTime(span.started_at)}</span>
                        <span>{formatDuration(span.duration_ms)}</span>
                      </div>
                      {span.input_payload !== undefined && (
                        <details>
                          <summary>Input</summary>
                          <pre>{JSON.stringify(span.input_payload, null, 2)}</pre>
                        </details>
                      )}
                      {span.output_payload !== undefined && (
                        <details>
                          <summary>Output</summary>
                          <pre>{JSON.stringify(span.output_payload, null, 2)}</pre>
                        </details>
                      )}
                      {span.error_message && <p className="error-message">{span.error_message}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          <section className="evaluation-panel">
            <div className="panel-header">
              <h3>Evaluations</h3>
              <div className="eval-controls">
                <select value={configId ?? ""} onChange={(event) => setConfigId(event.target.value || null)}>
                  {configs.map((config) => (
                    <option key={config.id} value={config.id}>{config.name}</option>
                  ))}
                </select>
                <button type="button" className="primary-button small" onClick={() => void runSelectedEvaluation()}>
                  Run evaluation
                </button>
              </div>
            </div>

            {evalLoading ? (
              <p className="empty-state">Loading evaluations?</p>
            ) : !selectedEvaluation ? (
              <p className="empty-state">No evaluation has been run for this trace yet.</p>
            ) : (
              <>
                <div className="evaluation-score">
                  <div>
                    <span className="eyebrow">Overall status</span>
                    <div className={`pill ${statusClass(selectedEvaluation.status)}`}>{selectedEvaluation.status}</div>
                  </div>
                  <div>
                    <span className="eyebrow">Score</span>
                    <strong>{selectedEvaluation.score}/100</strong>
                  </div>
                </div>

                <div className="summary-grid compact-grid">
                  <div>
                    <label>Pass</label>
                    <strong>{selectedEvaluation.passed_checks}</strong>
                  </div>
                  <div>
                    <label>Fail</label>
                    <strong>{selectedEvaluation.failed_checks}</strong>
                  </div>
                  <div>
                    <label>Skipped</label>
                    <strong>{selectedEvaluation.skipped_checks}</strong>
                  </div>
                  <div>
                    <label>Inconclusive</label>
                    <strong>{selectedEvaluation.inconclusive_checks}</strong>
                  </div>
                </div>

                {selectedEvaluation.findings.map((finding) => (
                  <div key={finding.id} className="finding-item">
                    <div className="finding-title-row">
                      <span className={`pill ${statusClass(finding.status)}`}>{finding.status}</span>
                      <strong>{finding.evaluator_name}</strong>
                      <small>{finding.check_name}</small>
                    </div>
                    <p>{finding.message}</p>
                    {finding.evidence && <pre>{JSON.stringify(finding.evidence, null, 2)}</pre>}
                  </div>
                ))}
              </>
            )}
          </section>
        </section>
      </section>

      {error && <p className="error-banner">{error}</p>}
    </main>
  );
}
