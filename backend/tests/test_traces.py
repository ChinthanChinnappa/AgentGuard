from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_demo_traces_are_persisted_and_visible():
    response = client.post("/api/demo/traces")

    assert response.status_code == 200
    payload = response.json()
    assert {"success_trace_id", "failed_trace_id"}.issubset(payload)

    list_response = client.get("/api/traces")
    assert list_response.status_code == 200
    results = list_response.json()
    trace_ids = {item["id"] for item in results["items"]}
    assert payload["success_trace_id"] in trace_ids
    assert payload["failed_trace_id"] in trace_ids

    success_trace = client.get(f"/api/traces/{payload['success_trace_id']}")
    assert success_trace.status_code == 200
    success_payload = success_trace.json()
    assert success_payload["status"] == "completed"
    assert len(success_payload["spans"]) >= 1

    spans_response = client.get(f"/api/traces/{payload['success_trace_id']}/spans")
    assert spans_response.status_code == 200
    spans_payload = spans_response.json()
    assert spans_payload["trace_id"] == payload["success_trace_id"]
    assert len(spans_payload["spans"]) >= 1
