from __future__ import annotations

from typing import Any

from app.tracing import TraceService


def generate_demo_traces() -> dict[str, str]:
    service = TraceService()

    success_trace = service.start_trace(
        task_name="Calculate total price",
        task_description="Calculate the total of three products with tax.",
        agent_name="demo-agent",
        agent_id="agent-demo-1",
        metadata={"environment": "demo"},
    )
    tool_span = service.start_span(
        trace_id=success_trace.id,
        span_type="tool",
        operation_name="calculate_total",
        tool_name="calculator",
        input_payload={"products": ["A", "B", "C"], "tax_rate": 0.1, "api_key": "super-secret"},
    )
    service.end_span(
        span_id=tool_span.id,
        status="success",
        output_payload={"subtotal": 65.5, "total": 72.05, "api_key": "[REDACTED]"},
    )
    service.complete_trace(trace_id=success_trace.id, final_output="72.05")

    failed_trace = service.start_trace(
        task_name="Price lookup",
        task_description="Fetch product prices for a failing checkout flow.",
        agent_name="demo-agent",
        agent_id="agent-demo-1",
        metadata={"environment": "demo"},
    )
    failing_tool = service.start_span(
        trace_id=failed_trace.id,
        span_type="tool",
        operation_name="price_lookup",
        tool_name="catalog_lookup",
        input_payload={"sku": "SKU-42", "token": "abc123"},
    )
    service.end_span(
        span_id=failing_tool.id,
        status="error",
        error_type="LookupError",
        error_message="Product catalog is temporarily unavailable.",
        output_payload={"error": "catalog unavailable"},
    )
    service.fail_trace(trace_id=failed_trace.id, error_message="Product catalog is temporarily unavailable.", final_output="Task failed")

    return {"success_trace_id": success_trace.id, "failed_trace_id": failed_trace.id}
