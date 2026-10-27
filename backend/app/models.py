from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Trace(Base):
    __tablename__ = "traces"
    __table_args__ = (
        Index("ix_traces_status_started_at", "status", "started_at"),
        Index("ix_traces_agent_started_at", "agent_name", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    task_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_metadata: Mapped[dict[str, Any] | None] = mapped_column("trace_metadata", JSON, nullable=True)

    spans: Mapped[list["TraceSpan"]] = relationship(
        back_populates="trace",
        cascade="all, delete-orphan",
        order_by="TraceSpan.sequence_number",
    )


class TraceSpan(Base):
    __tablename__ = "trace_spans"
    __table_args__ = (
        Index("ix_trace_spans_trace_sequence", "trace_id", "sequence_number"),
        Index("ix_trace_spans_tool_name", "tool_name", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), ForeignKey("traces.id"), nullable=False, index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    span_type: Mapped[str] = mapped_column(String(32), nullable=False)
    operation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_payload: Mapped[dict[str, Any] | Any | None] = mapped_column(JSON, nullable=True)
    output_payload: Mapped[dict[str, Any] | Any | None] = mapped_column(JSON, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    span_metadata: Mapped[dict[str, Any] | None] = mapped_column("span_metadata", JSON, nullable=True)

    trace: Mapped[Trace] = relationship(back_populates="spans")
