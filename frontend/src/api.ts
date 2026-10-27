export type HealthResponse = {
  status: string;
  database: string;
};

export type TraceItem = {
  id: string;
  task_name?: string | null;
  task_description?: string | null;
  agent_name?: string | null;
  agent_id?: string | null;
  status: string;
  started_at?: string | null;
  ended_at?: string | null;
  duration_ms?: number | null;
  final_output?: string | null;
  error_message?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type TraceSpan = {
  id: string;
  trace_id: string;
  parent_span_id?: string | null;
  sequence_number: number;
  span_type: string;
  operation_name: string;
  status: string;
  started_at?: string | null;
  ended_at?: string | null;
  duration_ms?: number | null;
  tool_name?: string | null;
  input_payload?: unknown;
  output_payload?: unknown;
  error_type?: string | null;
  error_message?: string | null;
  attempt_number?: number | null;
  metadata?: Record<string, unknown> | null;
};

export type TraceListResponse = {
  items: TraceItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type TraceDetail = TraceItem & {
  spans: TraceSpan[];
};

export type EvaluationFinding = {
  id: string;
  evaluator_name: string;
  check_name: string;
  status: string;
  severity: string;
  message: string;
  evidence?: Record<string, unknown> | null;
  details?: Record<string, unknown> | null;
};

export type EvaluationRecord = {
  id: string;
  trace_id: string;
  config_id: string;
  status: string;
  score: number;
  passed_checks: number;
  failed_checks: number;
  skipped_checks: number;
  inconclusive_checks: number;
  score_breakdown?: Record<string, number> | null;
  created_at?: string | null;
  findings: EvaluationFinding[];
};

export type EvaluationConfig = {
  id: string;
  name: string;
  description?: string | null;
  version: string;
  task_scope?: string | null;
  required_success_criteria?: Record<string, unknown>[] | null;
  expected_tools?: string[] | null;
  tool_schemas?: Record<string, unknown> | null;
  efficiency_thresholds?: Record<string, unknown> | null;
  safety_policies?: Record<string, unknown> | null;
  evaluator_weights?: Record<string, number> | null;
  required_evaluators?: string[] | null;
  critical_failure_conditions?: string[] | null;
  created_at?: string | null;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json() as Promise<HealthResponse>;
}

export async function fetchTraces(params: {
  status?: string;
  task?: string;
  agent?: string;
  page?: number;
  page_size?: number;
} = {}): Promise<TraceListResponse> {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.set("status", params.status);
  if (params.task) searchParams.set("task", params.task);
  if (params.agent) searchParams.set("agent", params.agent);
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));

  const response = await fetch(`/api/traces?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to load traces: ${response.status}`);
  }
  return response.json() as Promise<TraceListResponse>;
}

export async function fetchTrace(traceId: string): Promise<TraceDetail> {
  const response = await fetch(`/api/traces/${traceId}`);
  if (!response.ok) {
    throw new Error(`Failed to load trace: ${response.status}`);
  }
  return response.json() as Promise<TraceDetail>;
}

export async function fetchEvaluationConfigs(): Promise<EvaluationConfig[]> {
  const response = await fetch("/api/evaluation-configs");
  if (!response.ok) {
    throw new Error(`Failed to load evaluation configs: ${response.status}`);
  }
  return response.json() as Promise<EvaluationConfig[]>;
}

export async function fetchTraceEvaluations(traceId: string): Promise<{ items: EvaluationRecord[]; total: number; page: number; page_size: number; pages: number }> {
  const response = await fetch(`/api/traces/${traceId}/evaluations`);
  if (!response.ok) {
    throw new Error(`Failed to load evaluations: ${response.status}`);
  }
  return response.json() as Promise<{ items: EvaluationRecord[]; total: number; page: number; page_size: number; pages: number }>;
}

export async function evaluateTrace(traceId: string, configId?: string): Promise<EvaluationRecord> {
  const url = configId ? `/api/traces/${traceId}/evaluate?config_id=${encodeURIComponent(configId)}` : `/api/traces/${traceId}/evaluate`;
  const response = await fetch(url, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to evaluate trace: ${response.status}`);
  }
  return response.json() as Promise<EvaluationRecord>;
}

export async function generateDemoTraces(): Promise<{ success_trace_id: string; failed_trace_id: string }> {
  const response = await fetch("/api/demo/traces", { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to generate demo traces: ${response.status}`);
  }
  return response.json() as Promise<{ success_trace_id: string; failed_trace_id: string }>;
}
