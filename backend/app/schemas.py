from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceSpanSchema(BaseModel):
    id: str
    trace_id: str
    parent_span_id: str | None = None
    sequence_number: int
    span_type: str
    operation_name: str
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    tool_name: str | None = None
    input_payload: Any = None
    output_payload: Any = None
    error_type: str | None = None
    error_message: str | None = None
    attempt_number: int | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class TraceSchema(BaseModel):
    id: str
    task_name: str | None = None
    task_description: str | None = None
    agent_name: str | None = None
    agent_id: str | None = None
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    final_output: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None
    spans: list[TraceSpanSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TraceListResponse(BaseModel):
    items: list[TraceSchema] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    pages: int


class TraceSpansResponse(BaseModel):
    trace_id: str
    spans: list[TraceSpanSchema] = Field(default_factory=list)
