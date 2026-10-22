"""Exercise dashboard widgets against the real API using an in-process transport."""
import pytest
import httpx
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from platformcare.api import app
from platformcare.settings import ROOT


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DB", str(tmp_path / "ui.db"))
    monkeypatch.setenv("PLATFORM_TOKEN", "ui-test")
    monkeypatch.setenv("MODEL_MODE", "offline")
    with TestClient(app) as client:
        def route(method, url, **kwargs):
            kwargs.pop("timeout", None)
            return client.request(method, url, **kwargs)
        monkeypatch.setattr(httpx, "get", lambda url, **kw: route("GET", url, **kw))
        monkeypatch.setattr(httpx, "post", lambda url, **kw: route("POST", url, **kw))
        yield AppTest.from_file(str(ROOT / "dashboard.py"), default_timeout=20)


def test_dashboard_runs_failure_logs_and_recovery(dashboard):
    ui = dashboard.run()
    assert not ui.exception and not ui.error
    assert ui.metric[0].value == "UNKNOWN"
    ui.button[0].click().run()
    assert not ui.exception
    assert ui.metric[0].value == "HEALTHY"
    assert len(ui.dataframe) == 2  # job history and selected job logs
    ui.selectbox[0].select("invalid_input").run()
    ui.button[0].click().run()
    assert not ui.exception and not ui.error
    assert ui.metric[0].value == "DEGRADED"
    assert ui.metric[3].value == "1"
    assert "VALIDATION_FAILED" in ui.dataframe[1].value["code"].tolist()
    ui.selectbox[0].select("healthy").run()
    ui.button[0].click().run()
    assert not ui.exception
    assert ui.metric[0].value == "HEALTHY"
    assert ui.metric[3].value == "0"


def test_dashboard_mcp_investigation_and_feedback(dashboard):
    ui = dashboard.run()
    ui.selectbox[0].select("invalid_input").run()
    ui.button[0].click().run()
    next(button for button in ui.button if button.label == "Investigate using MCP").click().run()
    assert not ui.exception and not ui.error
    result = ui.session_state["investigation"]
    assert "runbooks/validation.md" in result["runbooks"]
    assert len(result["trace"]) == 3
    next(button for button in ui.button if button.label == "Save feedback").click().run()
    assert not ui.exception
    assert any("Feedback saved" in item.value for item in ui.success)
