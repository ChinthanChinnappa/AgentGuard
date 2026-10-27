from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Trace, TraceSpan

TRACE_STATUSES = {"running", "completed", "failed", "cancelled"}
SPAN_STATUSES = {"running", "success", "error", "cancelled"}
SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "auth",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "cookie",
    "session",
    "jwt",
    "key",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def sanitize_payload(value: Any, *, max_length: int = 4000) -> Any:
    if value is None:
        return None

    def redact(obj: Any) -> Any:
        if isinstance(obj, dict):
            redacted: dict[str, Any] = {}
            for key, item in obj.items():
                normalized_key = str(key).lower().replace("-", "_")
                if any(sensitive in normalized_key for sensitive in SENSITIVE_KEYS):
                    redacted[key] = "[REDACTED]"
                else:
                    redacted[key] = redact(item)
            return redacted
        if isinstance(obj, list):
            return [redact(item) for item in obj]
        if isinstance(obj, tuple):
            return tuple(redact(item) for item in obj)
        return obj

    redacted = redact(value)
    text_value = json.dumps(redacted, default=str, sort_keys=True)
    if len(text_value) > max_length:
        return text_value[: max_length - 3] + "..."
    return redacted if not isinstance(redacted, str) else redacted


class TraceService:
    def _new_trace_id(self) -> str:
        import uuid

        return str(uuid.uuid4())

    def _new_span_id(self) -> str:
        import uuid

        return str(uuid.uuid4())

    def start_trace(
        self,
        *,
        task_name: str | None = None,
        task_description: str | None = None,
        agent_name: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        status: str = "running",
    ) -> Trace:
        if status not in TRACE_STATUSES:
            raise ValueError(f"Unsupported trace status: {status}")

        trace = Trace(
            id=self._new_trace_id(),
            task_name=task_name,
            task_description=task_description,
            agent_name=agent_name,
            agent_id=agent_id,
            status=status,
            started_at=utc_now(),
            trace_metadata=sanitize_payload(metadata) if metadata else None,
        )
        with SessionLocal() as session:
            session.add(trace)
            session.commit()
            session.refresh(trace)
        return trace

    def get_trace(self, trace_id: str) -> Trace | None:
        with SessionLocal() as session:
            return session.get(Trace, trace_id)

    def list_traces(
        self,
        *,
        status: str | None = None,
        agent: str | None = None,
        task: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        if page < 1:
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="page_size must be between 1 and 100")

        with SessionLocal() as session:
            statement = select(Trace)
            if status is not None:
                statement = statement.where(Trace.status == status)
            if agent:
                statement = statement.where(or_(Trace.agent_name == agent, Trace.agent_id == agent))
            if task:
                keyword = f"%{task.lower()}%"
                statement = statement.where(
                    or_(
                        func.lower(Trace.task_name).like(keyword),
                        func.lower(Trace.task_description).like(keyword),
                    )
                )
            if start_date is not None:
                statement = statement.where(Trace.started_at >= start_date)
            if end_date is not None:
                statement = statement.where(Trace.started_at <= end_date)

            statement = statement.order_by(Trace.started_at.desc())
            total = session.execute(select(func.count()).select_from(statement.subquery())).scalar_one()
            paged = statement.offset((page - 1) * page_size).limit(page_size)
            traces = session.execute(paged).scalars().all()

        return {
            "items": [self._serialize_trace(trace) for trace in traces],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max((total + page_size - 1) // page_size, 1) if total else 0,
        }

    def _serialize_trace(self, trace: Trace) -> dict[str, Any]:
        return {
            "id": trace.id,
            "task_name": trace.task_name,
            "task_description": trace.task_description,
            "agent_name": trace.agent_name,
            "agent_id": trace.agent_id,
            "status": trace.status,
            "started_at": normalize_datetime(trace.started_at).isoformat() if normalize_datetime(trace.started_at) else None,
            "ended_at": normalize_datetime(trace.ended_at).isoformat() if normalize_datetime(trace.ended_at) else None,
            "duration_ms": trace.duration_ms,
            "final_output": trace.final_output,
            "error_message": trace.error_message,
            "metadata": trace.trace_metadata,
        }

    def start_span(
        self,
        *,
        trace_id: str,
        span_type: str,
        operation_name: str,
        parent_span_id: str | None = None,
        tool_name: str | None = None,
        input_payload: Any | None = None,
        status: str = "running",
        attempt_number: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceSpan:
        if span_type not in {"agent", "tool", "model", "retry", "system"}:
            raise ValueError(f"Unsupported span type: {span_type}")
        if status not in SPAN_STATUSES:
            raise ValueError(f"Unsupported span status: {status}")

        with SessionLocal() as session:
            trace = session.get(Trace, trace_id)
            if trace is None:
                raise ValueError(f"Trace {trace_id} does not exist")
            max_sequence = session.execute(
                select(func.coalesce(func.max(TraceSpan.sequence_number), 0)).where(TraceSpan.trace_id == trace_id)
            ).scalar_one()
            span = TraceSpan(
                id=self._new_span_id(),
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                sequence_number=max_sequence + 1,
                span_type=span_type,
                operation_name=operation_name,
                status=status,
                started_at=utc_now(),
                tool_name=tool_name,
                input_payload=sanitize_payload(input_payload),
                attempt_number=attempt_number,
                span_metadata=sanitize_payload(metadata) if metadata else None,
            )
            session.add(span)
            session.commit()
            session.refresh(span)
            return span

    def end_span(
        self,
        *,
        span_id: str,
        status: str = "success",
        output_payload: Any | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceSpan:
        if status not in SPAN_STATUSES:
            raise ValueError(f"Unsupported span status: {status}")

        with SessionLocal() as session:
            span = session.get(TraceSpan, span_id)
            if span is None:
                raise ValueError(f"Span {span_id} does not exist")

            ended_at = utc_now()
            started_at = normalize_datetime(span.started_at) or ended_at
            duration_ms = int((normalize_datetime(ended_at) - started_at).total_seconds() * 1000)
            span.status = status
            span.ended_at = ended_at
            span.duration_ms = duration_ms
            span.output_payload = sanitize_payload(output_payload)
            span.error_type = error_type
            span.error_message = error_message
            if metadata:
                span.span_metadata = sanitize_payload(metadata)
            session.add(span)
            session.commit()
            session.refresh(span)
            return span

    def record_event(
        self,
        *,
        trace_id: str,
        operation_name: str,
        span_type: str = "system",
        status: str = "success",
        **kwargs: Any,
    ) -> TraceSpan:
        span = self.start_span(trace_id=trace_id, span_type=span_type, operation_name=operation_name, **kwargs)
        return self.end_span(span_id=span.id, status=status, **{key: value for key, value in kwargs.items() if key in {"output_payload", "error_type", "error_message", "metadata"}})

    def complete_trace(
        self,
        *,
        trace_id: str,
        final_output: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        return self._finalize_trace(trace_id=trace_id, status="completed", final_output=final_output, metadata=metadata)

    def fail_trace(
        self,
        *,
        trace_id: str,
        error_message: str,
        metadata: dict[str, Any] | None = None,
        final_output: str | None = None,
    ) -> Trace:
        return self._finalize_trace(
            trace_id=trace_id,
            status="failed",
            final_output=final_output,
            error_message=error_message,
            metadata=metadata,
        )

    def _finalize_trace(
        self,
        *,
        trace_id: str,
        status: str,
        final_output: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        with SessionLocal() as session:
            trace = session.get(Trace, trace_id)
            if trace is None:
                raise ValueError(f"Trace {trace_id} does not exist")
            ended_at = utc_now()
            trace.status = status
            trace.ended_at = ended_at
            trace.final_output = final_output
            trace.error_message = error_message
            started_at = normalize_datetime(trace.started_at) or ended_at
            trace.duration_ms = int((ended_at - started_at).total_seconds() * 1000)
            if metadata:
                trace.trace_metadata = sanitize_payload(metadata)
            session.add(trace)
            session.commit()
            session.refresh(trace)
            return trace

    def get_trace_spans(self, trace_id: str) -> list[TraceSpan]:
        with SessionLocal() as session:
            spans = session.execute(
                select(TraceSpan).where(TraceSpan.trace_id == trace_id).order_by(TraceSpan.sequence_number)
            ).scalars().all()
            return list(spans)
