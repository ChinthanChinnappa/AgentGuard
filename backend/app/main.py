from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import Base, check_database_connection, engine
from app.demo import generate_demo_traces
from app.evaluation import EvaluationConfig, EvaluationService
from app.models import Trace, TraceSpan
from app.tracing import TraceService

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
trace_service = TraceService()
evaluation_service = EvaluationService()

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    try:
        check_database_connection()
    except SQLAlchemyError:
        return {"status": "degraded", "database": "unavailable"}
    return {"status": "ok", "database": "ok"}


@app.get("/api/ready")
def readiness() -> dict[str, str]:
    check_database_connection()
    return {"status": "ready"}


@app.get("/api/traces")
def list_traces(
    status: str | None = Query(default=None, pattern="^(running|completed|failed|cancelled)$"),
    agent: str | None = None,
    task: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, object]:
    return trace_service.list_traces(
        status=status,
        agent=agent,
        task=task,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@app.get("/api/traces/{trace_id}")
def get_trace(trace_id: str) -> dict[str, object]:
    trace = trace_service.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    data = trace_service._serialize_trace(trace)
    data["spans"] = [
        {
            "id": span.id,
            "trace_id": span.trace_id,
            "parent_span_id": span.parent_span_id,
            "sequence_number": span.sequence_number,
            "span_type": span.span_type,
            "operation_name": span.operation_name,
            "status": span.status,
            "started_at": span.started_at.isoformat() if span.started_at else None,
            "ended_at": span.ended_at.isoformat() if span.ended_at else None,
            "duration_ms": span.duration_ms,
            "tool_name": span.tool_name,
            "input_payload": span.input_payload,
            "output_payload": span.output_payload,
            "error_type": span.error_type,
            "error_message": span.error_message,
            "attempt_number": span.attempt_number,
            "metadata": span.span_metadata,
        }
        for span in trace_service.get_trace_spans(trace_id)
    ]
    return data


@app.get("/api/traces/{trace_id}/spans")
def get_trace_spans(trace_id: str) -> dict[str, object]:
    trace = trace_service.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    spans = trace_service.get_trace_spans(trace_id)
    return {
        "trace_id": trace_id,
        "spans": [
            {
                "id": span.id,
                "trace_id": span.trace_id,
                "parent_span_id": span.parent_span_id,
                "sequence_number": span.sequence_number,
                "span_type": span.span_type,
                "operation_name": span.operation_name,
                "status": span.status,
                "started_at": span.started_at.isoformat() if span.started_at else None,
                "ended_at": span.ended_at.isoformat() if span.ended_at else None,
                "duration_ms": span.duration_ms,
                "tool_name": span.tool_name,
                "input_payload": span.input_payload,
                "output_payload": span.output_payload,
                "error_type": span.error_type,
                "error_message": span.error_message,
                "attempt_number": span.attempt_number,
                "metadata": span.span_metadata,
            }
            for span in spans
        ],
    }


@app.get("/api/evaluation-configs")
def list_evaluation_configs() -> list[dict[str, object]]:
    configs = evaluation_service.list_configs()
    return [
        {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "version": config.version,
            "task_scope": config.task_scope,
            "required_success_criteria": config.required_success_criteria,
            "expected_tools": config.expected_tools,
            "tool_schemas": config.tool_schemas,
            "efficiency_thresholds": config.efficiency_thresholds,
            "safety_policies": config.safety_policies,
            "evaluator_weights": config.evaluator_weights,
            "required_evaluators": config.required_evaluators,
            "critical_failure_conditions": config.critical_failure_conditions,
            "created_at": config.created_at.isoformat(),
        }
        for config in configs
    ]


@app.post("/api/evaluation-configs")
def create_evaluation_config(payload: dict[str, object]) -> dict[str, object]:
    config = evaluation_service.create_config(payload)
    return {
        "id": config.id,
        "name": config.name,
        "description": config.description,
        "version": config.version,
        "task_scope": config.task_scope,
        "required_success_criteria": config.required_success_criteria,
        "expected_tools": config.expected_tools,
        "tool_schemas": config.tool_schemas,
        "efficiency_thresholds": config.efficiency_thresholds,
        "safety_policies": config.safety_policies,
        "evaluator_weights": config.evaluator_weights,
        "required_evaluators": config.required_evaluators,
        "critical_failure_conditions": config.critical_failure_conditions,
        "created_at": config.created_at.isoformat(),
    }


@app.get("/api/traces/{trace_id}/evaluations")
def list_trace_evaluations(trace_id: str, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)) -> dict[str, object]:
    trace = trace_service.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return evaluation_service.list_evaluations(trace_id=trace_id, page=page, page_size=page_size)


@app.post("/api/traces/{trace_id}/evaluate")
def evaluate_trace(trace_id: str, config_id: str | None = None) -> dict[str, object]:
    trace = trace_service.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    evaluation = evaluation_service.evaluate_trace(trace_id, config_id=config_id)
    return evaluation_service.serialize_evaluation(evaluation)


@app.get("/api/evaluations")
def list_evaluations(status: str | None = Query(default=None), trace_id: str | None = None, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)) -> dict[str, object]:
    return evaluation_service.list_evaluations(trace_id=trace_id, status=status, page=page, page_size=page_size)


@app.get("/api/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str) -> dict[str, object]:
    evaluation = evaluation_service.get_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation_service.serialize_evaluation(evaluation)


@app.post("/api/demo/traces")
def create_demo_traces() -> dict[str, str]:
    return generate_demo_traces()
