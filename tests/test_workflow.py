import asyncio
import json
import time
import pytest
from fastapi.testclient import TestClient
from platformcare import store
from platformcare.api import app
from platformcare.pipeline import run, health
from platformcare.agent import investigate

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("PLATFORM_TOKEN", "test-only")
    monkeypatch.setenv("MODEL_MODE", "offline")

def test_failure_retains_last_good_output_and_recovery_resolves():
    good = run("healthy")
    assert json.loads(good["output"]) == {"music": 12, "tv": 12}
    bad = run("invalid_input")
    assert bad["status"] == "failed" and bad["output"] is None
    assert health()["status"] == "degraded"
    assert health()["freshness_seconds"] is not None
    assert store.support_metrics()["open_incidents"] == 1
    run("healthy")
    assert health()["status"] == "healthy"
    assert store.support_metrics()["open_incidents"] == 0

def test_alert_identity_and_resolution():
    with TestClient(app) as client:
        alert = {"alerts": [{"fingerprint": "abc", "status": "firing", "annotations": {"summary": "failed"}}]}
        assert client.post("/webhooks/alerts", json=alert).status_code == 401
        headers = {"Authorization": "Bearer test-only"}
        first = client.post("/webhooks/alerts", json=alert, headers=headers).json()
        second = client.post("/webhooks/alerts", json=alert, headers=headers).json()
        assert first["accepted"][0]["created"] is True
        assert second["accepted"][0]["created"] is False
        alert["alerts"][0]["status"] = "resolved"
        client.post("/webhooks/alerts", json=alert, headers=headers)
        assert store.support_metrics()["open_incidents"] == 0

def test_missing_and_stale_data():
    assert health()["status"] == "unknown"
    run("healthy")
    store.execute("UPDATE runs SET finished=?", (time.time()-400,))
    assert health()["status"] == "degraded"

def test_support_dedup_feedback_and_metrics():
    key, created = store.new_request("help", "event-1")
    assert created
    assert store.new_request("help", "event-1") == (key, False)
    assert store.support_metrics()["mean_first_response_seconds"] is None
    store.complete_request(key, {"escalate": True})
    with TestClient(app) as client:
        response = client.post(f"/support/{key}/feedback", json={"helpful": True}, headers={"X-Platform-Token": "test-only"})
        assert response.status_code == 200
        metrics = client.get("/metrics").text
        assert "platform_support_helpful_rate 1.0" in metrics
    assert store.support_metrics()["escalations"] == 1

def test_redaction():
    text = store.redact("token=private password: hidden sk-abcdef xoxb-123456")
    assert "private" not in text and "hidden" not in text and "abcdef" not in text

@pytest.mark.asyncio
async def test_real_mcp_protocol_investigation():
    failed = run("invalid_input")
    result = await investigate("Why did the pipeline fail?")
    assert result["mode"] == "offline"
    assert "runbooks/validation.md" in result["runbooks"]
    assert any(failed["id"] in evidence for evidence in result["evidence"])
    assert [t["tool"] for t in result["trace"]] == ["get_service_health", "search_logs", "search_runbooks"]
    assert not any(t["is_error"] for t in result["trace"])

@pytest.mark.asyncio
async def test_no_history_abstains():
    result = await investigate("Explain failure")
    assert result["escalate"] and not result["evidence"]

def test_api_runs_and_bad_scenario():
    with TestClient(app) as client:
        headers = {"X-Platform-Token": "test-only"}
        assert client.post("/runs", headers=headers, json={"scenario": "unrecognized"}).status_code == 422
        assert client.post("/runs", headers=headers, json={"scenario": "dependency_outage"}).json()["status"] == "failed"
        assert client.get("/overview", headers=headers).json()["health"]["status"] == "degraded"

def test_logs_are_bounded_to_job_and_require_auth():
    first = run("invalid_input")
    run("healthy")
    with TestClient(app) as client:
        path = f"/runs/{first['id']}/logs"
        assert client.get(path).status_code == 401
        response = client.get(path, headers={"X-Platform-Token": "test-only"})
        assert response.status_code == 200
        assert all(item["run_id"] == first["id"] for item in response.json())
        assert any(item["code"] == "VALIDATION_FAILED" for item in response.json())

def test_slow_job_is_degraded_until_fast_recovery(monkeypatch):
    finished = run("healthy")
    store.execute("UPDATE runs SET started=? WHERE id=?", (finished["finished"]-3, finished["id"]))
    assert health()["status"] == "degraded"
    run("healthy")
    assert health()["status"] == "healthy"
