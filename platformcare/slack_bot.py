"""Local Socket Mode; optional HTTP mode uses Bolt's signature verification."""
import asyncio
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from . import store
from .pipeline import health


async def investigate(question):
    # Health/incident commands and handler tests do not need model dependencies.
    from .agent import investigate as run
    return await asyncio.wait_for(run(question), timeout=180)


def slack_text(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_result(result):
    lines = [f"*{slack_text(result.get('mode', 'unknown'))} investigation*", slack_text(result["summary"])]
    for key, title in (("evidence", "Evidence"), ("runbooks", "Runbooks"), ("next_steps", "Next steps")):
        lines.append(f"*{title}*\n" + "\n".join("• " + slack_text(x) for x in result.get(key, [])))
    if result.get("escalate"):
        lines.append("Manual review requested from demo-data-team. No on-call person has been paged.")
    return "\n".join(lines)[:12000]


def result_blocks(result, key):
    text = format_result(result)
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": text[i:i+2500]}}
              for i in range(0, len(text), 2500)]
    blocks.append({"type": "actions", "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": "Helpful"}, "action_id": "helpful", "value": key},
        {"type": "button", "text": {"type": "plain_text", "text": "Not helpful"}, "action_id": "not_helpful", "value": key},
        {"type": "button", "text": {"type": "plain_text", "text": "Escalate"}, "action_id": "escalate", "value": key}]})
    return blocks


def investigate_and_reply(question, key, channel, client):
    try:
        root = client.chat_postMessage(channel=channel, text=f"Support request {key}: investigating synthetic pipeline evidence.")
        try:
            result = asyncio.run(investigate(question))
        except Exception:
            result = dict(summary="Investigation failed; inspect job logs and escalate to the owner.",
                          mode=os.getenv("MODEL_MODE", "offline"), evidence=[], runbooks=[],
                          next_steps=["Open the PlatformCare dashboard."], escalate=True)
        client.chat_postMessage(channel=channel, thread_ts=root["ts"], text=format_result(result),
                                blocks=result_blocks(result, key))
    except Exception:
        # A delivery failure is not a useful response. Keep answered unset and
        # record a safe status without logging tokens or SDK request headers.
        store.execute("UPDATE requests SET result=? WHERE id=?",
                      (json.dumps({"delivery_error": "Slack delivery failed; retry with a new support command"}), key))
        return False
    store.complete_request(key, result)
    return True


class SupportWorkers:
    """One active investigation plus one queued request bounds local RAM/API load."""
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="platformcare-support")
        self.slots = threading.BoundedSemaphore(2)

    def submit(self, function, *args):
        if not self.slots.acquire(blocking=False):
            return False
        def work():
            try:
                function(*args)
            finally:
                self.slots.release()
        try:
            self.executor.submit(work)
        except RuntimeError:
            self.slots.release()
            return False
        return True

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=True)


def register_handlers(app, submit):
    @app.command("/platform-health")
    def platform_health(ack, respond):
        ack()
        state = health()
        age = state["freshness_seconds"]
        freshness = f"{age:.0f}s" if age is not None else "no successful output"
        respond(text=f"usage-analytics: {state['status']} | last output age: {freshness} | owner: {state['owner']} | Synthetic workload")

    @app.command("/platform-help")
    def platform_help(ack, body, client, respond):
        ack("Investigating job state, logs, and runbooks…")
        question = (body.get("text") or "Why is the pipeline unhealthy?").strip()[:2000]
        key, created = store.new_request(question, body.get("trigger_id"))
        if created and not submit(investigate_and_reply, question, key, body["channel_id"], client):
            store.execute("UPDATE requests SET result=? WHERE id=?",
                          (json.dumps({"delivery_error": "Investigation queue full; retry later"}), key))
            respond(text="Both investigation slots are busy. Please retry shortly.")

    @app.command("/incident-summary")
    def incident_summary(ack, respond, body):
        ack()
        items = store.rows("SELECT * FROM incidents WHERE id=?", (body.get("text", "").strip(),))
        respond(text=json.dumps(items[0], indent=2) if items else "Unknown incident. Copy an ID from the dashboard.")

    def feedback(ack, body, respond, useful):
        ack()
        store.execute("UPDATE requests SET helpful=? WHERE id=?", (int(useful), body["actions"][0]["value"]))
        respond(text="Feedback saved.", replace_original=False)

    @app.action("helpful")
    def helpful(ack, body, respond):
        feedback(ack, body, respond, True)

    @app.action("not_helpful")
    def not_helpful(ack, body, respond):
        feedback(ack, body, respond, False)

    @app.action("escalate")
    def escalate(ack, body, respond):
        ack()
        store.execute("UPDATE requests SET escalated=1 WHERE id=?", (body["actions"][0]["value"],))
        respond(text="Escalation recorded for demo-data-team. No on-call person has been paged.", replace_original=False)


def deliver_incident_updates(client, channel):
    """One poll iteration. A crash between a Slack post and DB commit may duplicate."""
    for item in store.rows("SELECT * FROM incidents ORDER BY opened"):
        try:
            if not item["slack_ts"] and item["resolved"] is None:
                message = client.chat_postMessage(channel=channel, text=f"Incident {item['id']}: {item['title']} | owner demo-data-team | synthetic lab")
                store.execute("UPDATE incidents SET slack_ts=? WHERE id=?", (message["ts"], item["id"]))
            elif item["slack_ts"] and item["resolved"] and store.claim_delivery("resolution:" + item["id"]):
                try:
                    client.chat_postMessage(channel=channel, thread_ts=item["slack_ts"], text="Resolved: condition cleared. Verify data freshness in the dashboard.")
                except Exception:
                    store.execute("DELETE FROM deliveries WHERE key=?", ("resolution:" + item["id"],))
                    raise
        except Exception:
            print("Slack incident delivery failed; retrying later", flush=True)


def build_app(workers):
    app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.getenv("SLACK_SIGNING_SECRET", ""))
    register_handlers(app, workers.submit)
    return app


def main():
    required = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"] if os.getenv("SLACK_TRANSPORT", "socket") == "socket" else ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"]
    if any(not os.getenv(key) for key in required):
        raise SystemExit("Slack configuration missing. Follow docs/STAGE4_SLACK_SETUP.md; never paste tokens into chat.")
    workers, stop = SupportWorkers(), threading.Event()
    try:
        app = build_app(workers)
        channel = os.getenv("SLACK_ALERT_CHANNEL")
        if channel:
            def poll():
                while not stop.is_set():
                    deliver_incident_updates(app.client, channel)
                    stop.wait(10)
            threading.Thread(target=poll, daemon=True, name="platformcare-incidents").start()
        if os.getenv("SLACK_TRANSPORT", "socket") == "http":
            app.start(port=3000)
        else:
            SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
    finally:
        stop.set()
        workers.close()


if __name__ == "__main__":
    main()
