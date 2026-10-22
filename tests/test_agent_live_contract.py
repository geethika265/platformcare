"""Simulated provider responses with real MCP calls; not live inference evidence."""
import json
import httpx
import pytest
from platformcare.agent import investigate
from platformcare.pipeline import run

@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DB", str(tmp_path / "agent.db"))
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://model.example/v1")
    monkeypatch.setenv("MODEL_API_KEY", "fake-test-key")

def completion(message):
    return httpx.Response(200, json={"choices": [{"message": message}]})

def call(name, arguments, key):
    return completion({"role": "assistant", "content": None, "tool_calls": [
        {"id": key, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]})

@pytest.mark.asyncio
async def test_model_requests_tools_over_mcp_before_summary():
    failed = run("invalid_input")
    turns = []
    def respond(request):
        body = json.loads(request.content)
        turns.append(body)
        assert request.url.path == "/v1/chat/completions"
        assert {t["function"]["name"] for t in body["tools"]} >= {"get_service_health", "search_logs", "search_runbooks"}
        if len(turns) == 1:
            return call("get_service_health", {}, "health")
        if len(turns) == 2:
            assert failed["id"] in body["messages"][-1]["content"]
            return call("search_logs", {"run_id": failed["id"]}, "logs")
        if len(turns) == 3:
            assert "VALIDATION_FAILED" in body["messages"][-1]["content"]
            return call("search_runbooks", {"query": "VALIDATION_FAILED"}, "runbooks")
        return completion({"role": "assistant", "content": json.dumps({
            "summary": "Input validation failed; inspect the negative minutes record.",
            "evidence": ["run:" + failed["id"]], "runbooks": ["runbooks/validation.md"],
            "next_steps": ["Quarantine invalid input before rerunning."], "escalate": False})})
    result = await investigate("Why did the job fail?", mode="live", model_transport=httpx.MockTransport(respond))
    assert len(turns) == 4
    assert result["runbooks"] == ["runbooks/validation.md"]
    assert not result["escalate"]
    assert [t["tool"] for t in result["trace"]] == ["get_service_health", "search_logs", "search_runbooks"]

@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["not JSON", json.dumps({"summary": "fine", "evidence": [], "runbooks": [], "next_steps": [], "escalate": "false"})])
async def test_malformed_model_result_escalates(raw):
    def respond(request):
        return completion({"role": "assistant", "content": raw})
    result = await investigate("Help", mode="live", model_transport=httpx.MockTransport(respond))
    assert result["escalate"] is True and not result["evidence"]

@pytest.mark.asyncio
async def test_invented_runbook_path_rejected():
    count = 0
    def respond(request):
        nonlocal count
        count += 1
        if count == 1:
            return call("get_service_health", {}, "health")
        return completion({"role": "assistant", "content": json.dumps({
            "summary": "Insufficient evidence", "evidence": [],
            "runbooks": ["runbooks/invented.md"], "next_steps": [], "escalate": False})})
    result = await investigate("Help", mode="live", model_transport=httpx.MockTransport(respond))
    assert result["runbooks"] == [] and result["escalate"] is True

@pytest.mark.asyncio
async def test_final_response_reserved_after_investigation_budget():
    turns = 0
    def respond(request):
        nonlocal turns
        turns += 1
        body = json.loads(request.content)
        if turns <= 5:
            return call("get_service_health", {}, f"health-{turns}")
        assert body["tool_choice"] == "none"
        assert body["response_format"] == {"type": "json_object"}
        return completion({"role": "assistant", "content": json.dumps({
            "summary": "No job history is available.", "evidence": [], "runbooks": [],
            "next_steps": ["Ask the platform owner for job history."], "escalate": True})})
    result = await investigate("Help", mode="live", model_transport=httpx.MockTransport(respond))
    assert turns == 6
    assert result["summary"] == "No job history is available."
    assert result["escalate"] is True
