from fastapi.testclient import TestClient

from app.main import app
from app.tracing import TraceService


client = TestClient(app)
trace_service = TraceService()


def test_default_config_evaluation_passes_for_satisfied_trace():
    trace = trace_service.start_trace(
        task_name="Calculate total",
        task_description="Compute total cost of three items.",
        agent_name="bench-agent",
        agent_id="bench-1",
    )
    tool = trace_service.start_span(
        trace_id=trace.id,
        span_type="tool",
        operation_name="calculate_total",
        tool_name="calculator",
        input_payload={"items": ["apple", "banana", "orange"], "unit_price": 2.5},
    )
    trace_service.end_span(span_id=tool.id, status="success", output_payload={"total": 7.5})
    trace_service.complete_trace(trace_id=trace.id, final_output="7.5")

    response = client.post(f"/api/traces/{trace.id}/evaluate")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"PASS", "NEEDS_REVIEW"}
    assert payload["score"] >= 50


def test_forbidden_tool_policy_causes_failed_evaluation():
    trace = trace_service.start_trace(
        task_name="Unsafe action",
        task_description="Attempt an unauthorized mutation.",
    )
    tool = trace_service.start_span(
        trace_id=trace.id,
        span_type="tool",
        operation_name="delete_file",
        tool_name="delete_file",
        input_payload={"path": "/tmp/unsafe"},
    )
    trace_service.end_span(span_id=tool.id, status="error", error_message="Denied by policy")
    trace_service.fail_trace(trace_id=trace.id, error_message="Denied by policy", final_output="Task failed")

    response = client.post(f"/api/traces/{trace.id}/evaluate")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAIL"
    assert any(finding["severity"] == "critical" for finding in payload["findings"])


def test_evaluation_api_exposes_configuration_and_history():
    config_response = client.post(
        "/api/evaluation-configs",
        json={
            "name": "custom-benchmark",
            "description": "Benchmark config",
            "version": "1.0.0",
            "required_success_criteria": [{"type": "final_output_present", "expected": True}],
            "expected_tools": ["calculator"],
            "tool_schemas": {"calculator": {"required": ["items"], "types": {"items": "list"}}},
            "efficiency_thresholds": {"max_tool_calls": 5},
            "safety_policies": {"allowed_tools": ["calculator"], "denied_tools": ["delete_file"]},
            "evaluator_weights": {"task_success": 40, "tool_selection": 15, "tool_argument_validation": 15, "efficiency": 10, "error_recovery": 10, "safety_and_permissions": 10},
            "required_evaluators": ["task_success", "tool_selection", "tool_argument_validation", "efficiency", "error_recovery", "safety_and_permissions"],
            "critical_failure_conditions": ["forbidden_tool_invocation"],
        },
    )
    assert config_response.status_code == 200
    config = config_response.json()

    trace = trace_service.start_trace(task_name="custom", task_description="custom validation")
    tool = trace_service.start_span(trace_id=trace.id, span_type="tool", operation_name="calculate_total", tool_name="calculator", input_payload={"items": [1, 2, 3]})
    trace_service.end_span(span_id=tool.id, status="success", output_payload={"total": 6})
    trace_service.complete_trace(trace_id=trace.id, final_output="6")

    eval_response = client.post(f"/api/traces/{trace.id}/evaluate?config_id={config['id']}")
    assert eval_response.status_code == 200
    evaluation = eval_response.json()
    assert evaluation["trace_id"] == trace.id

    list_response = client.get("/api/evaluations")
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1
