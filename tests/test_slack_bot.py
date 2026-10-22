"""Handler and delivery contracts with fake Slack replies; no messages are sent."""
import json
import threading
import pytest
from slack_sdk.models.blocks import Block
from platformcare import store
from platformcare.pipeline import run
from platformcare import slack_bot as bot


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DB", str(tmp_path / "slack.db"))


class Registry:
    def __init__(self):
        self.commands, self.actions = {}, {}
    def command(self, name):
        def register(fn):
            self.commands[name] = fn
            return fn
        return register
    def action(self, name):
        def register(fn):
            self.actions[name] = fn
            return fn
        return register


class Client:
    def __init__(self):
        self.messages = []
        self.fail = False
    def chat_postMessage(self, **kwargs):
        if self.fail:
            raise RuntimeError("simulated Slack delivery failure")
        self.messages.append(kwargs)
        return {"ts": f"{len(self.messages)}.000"}


def result():
    return dict(mode="live", summary="Validation failed", evidence=["log:2 VALIDATION_FAILED"],
                runbooks=["runbooks/validation.md"], next_steps=["Inspect input"], escalate=False)


def test_health_acknowledges_before_responding():
    app, events = Registry(), []
    bot.register_handlers(app, lambda *_: True)
    app.commands["/platform-health"](lambda: events.append("ack"), lambda **kw: events.append(kw["text"]))
    assert events[0] == "ack"
    assert "no successful output" in events[1]


def test_help_acknowledges_then_enqueues_once_for_duplicate_command():
    app, events, submitted = Registry(), [], []
    def submit(*args):
        assert events[0] == "ack"
        submitted.append(args)
        return True
    bot.register_handlers(app, submit)
    body = {"text": "Why did it fail?", "trigger_id": "same-trigger", "channel_id": "C_TEST"}
    for _ in range(2):
        app.commands["/platform-help"](lambda *_: events.append("ack"), body, Client(), lambda **_: None)
    assert len(submitted) == 1
    assert store.support_metrics()["requests"] == 1


def test_busy_queue_returns_feedback_and_does_not_claim_response():
    app, replies = Registry(), []
    bot.register_handlers(app, lambda *_: False)
    app.commands["/platform-help"](lambda *_: None,
        {"trigger_id": "busy", "channel_id": "C_TEST", "text": "help"}, Client(), lambda **kw: replies.append(kw["text"]))
    assert "busy" in replies[0]
    assert store.support_metrics()["unanswered"] == 1


def test_support_response_is_threaded_and_records_after_delivery(monkeypatch):
    client = Client()
    key, _ = store.new_request("help")
    async def investigate(_):
        return result()
    monkeypatch.setattr(bot, "investigate", investigate)
    assert bot.investigate_and_reply("help", key, "C_TEST", client)
    assert client.messages[1]["thread_ts"] == "1.000"
    assert "runbooks/validation.md" in client.messages[1]["text"]
    assert store.support_metrics()["unanswered"] == 0


def test_failed_delivery_stays_unanswered_without_calling_model(monkeypatch):
    client, called = Client(), []
    client.fail = True
    key, _ = store.new_request("help")
    async def investigate(_):
        called.append(True)
        return result()
    monkeypatch.setattr(bot, "investigate", investigate)
    assert not bot.investigate_and_reply("help", key, "C_TEST", client)
    assert called == []
    assert store.support_metrics()["unanswered"] == 1


def test_model_error_delivers_human_escalation(monkeypatch):
    client = Client()
    key, _ = store.new_request("help")
    async def investigate(_):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(bot, "investigate", investigate)
    assert bot.investigate_and_reply("help", key, "C_TEST", client)
    assert store.support_metrics()["escalations"] == 1


def test_long_response_preserves_tail_with_valid_slack_blocks():
    data = result()
    data["evidence"] = ["a" * 3100]
    data["next_steps"] = ["UNIQUE_FINAL_STEP"]
    data["summary"] = "Invalid input <!here>"
    blocks = bot.result_blocks(data, "request-id")
    assert "UNIQUE_FINAL_STEP" in "".join(b["text"]["text"] for b in blocks if b["type"] == "section")
    assert "<!here>" not in bot.format_result(data)
    assert all(len(b["text"]["text"]) <= 3000 for b in blocks if b["type"] == "section")
    assert all(block.to_dict() for block in Block.parse_all(blocks))


def test_incident_posts_once_then_resolves_in_same_thread():
    client = Client()
    item, _ = store.incident("failure", "Synthetic failure", "pipeline")
    bot.deliver_incident_updates(client, "C_TEST")
    bot.deliver_incident_updates(client, "C_TEST")
    assert len(client.messages) == 1
    store.resolve("failure")
    bot.deliver_incident_updates(client, "C_TEST")
    bot.deliver_incident_updates(client, "C_TEST")
    assert len(client.messages) == 2
    assert client.messages[1]["thread_ts"] == "1.000"


def test_historical_resolved_incidents_are_not_posted():
    client = Client()
    store.incident("old", "Old incident", "pipeline")
    store.resolve("old")
    bot.deliver_incident_updates(client, "C_TEST")
    assert not client.messages


def test_feedback_and_escalation_persist():
    key, _ = store.new_request("help")
    app = Registry()
    bot.register_handlers(app, lambda *_: True)
    body = {"actions": [{"value": key}]}
    for action in ["helpful", "not_helpful", "escalate"]:
        app.actions[action](lambda: None, body, lambda **_: None)
    assert store.support_metrics()["helpful_rate"] == 0
    assert store.support_metrics()["escalations"] == 1


def test_worker_queue_is_bounded():
    workers, release, started = bot.SupportWorkers(), threading.Event(), threading.Event()
    def work():
        started.set()
        release.wait(timeout=3)
    try:
        assert workers.submit(work)
        assert started.wait(timeout=1)
        assert workers.submit(work)
        assert not workers.submit(work)
    finally:
        release.set()
        workers.close()


def test_manifest_matches_registered_commands():
    from platformcare.settings import ROOT
    manifest = json.loads((ROOT / "slack-manifest.json").read_text())
    app = Registry()
    bot.register_handlers(app, lambda *_: True)
    assert {x["command"] for x in manifest["features"]["slash_commands"]} == set(app.commands)
    assert manifest["settings"]["socket_mode_enabled"] is True
    assert set(manifest["oauth_config"]["scopes"]["bot"]) == {"commands", "chat:write"}
