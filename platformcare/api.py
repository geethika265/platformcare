import asyncio
import hmac
import os
from typing import Literal
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field
from . import store
from .metrics import render
from .pipeline import health, run
from .settings import token

app = FastAPI(title="PlatformCare", description="Synthetic data-platform support lab")

def authorized(x_platform_token: str = Header(default=""), authorization: str = Header(default="")):
    supplied = x_platform_token or (authorization[7:] if authorization.startswith("Bearer ") else "")
    if not hmac.compare_digest(supplied, token()):
        raise HTTPException(401, "Invalid platform token")

class RunRequest(BaseModel):
    scenario: Literal["healthy", "invalid_input", "dependency_outage", "slow_job"] = "healthy"
    source: Literal["manual", "airflow", "dashboard", "evaluation"] = "manual"

class SupportRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

class Feedback(BaseModel):
    helpful: bool
    resolved: bool = False

@app.get("/health")
def status():
    return health()

@app.get("/metrics")
def metrics():
    return Response(render(), media_type="text/plain; version=0.0.4")

@app.post("/runs", dependencies=[Depends(authorized)])
def create_run(body: RunRequest):
    return run(body.scenario, body.source)

@app.get("/runs/{key}/logs", dependencies=[Depends(authorized)])
def run_logs(key: str):
    if not store.rows("SELECT id FROM runs WHERE id=?", (key,)):
        raise HTTPException(404, "Unknown run")
    return store.rows("SELECT * FROM logs WHERE run_id=? ORDER BY ts LIMIT 100", (key,))

@app.get("/overview", dependencies=[Depends(authorized)])
def overview():
    return dict(health=health(), runs=store.rows("SELECT * FROM runs ORDER BY started DESC LIMIT 100"),
                incidents=store.rows("SELECT * FROM incidents ORDER BY opened DESC LIMIT 100"),
                support=store.support_metrics(), requests=store.rows("SELECT id,question,opened,answered,escalated,helpful FROM requests ORDER BY opened DESC LIMIT 50"))

@app.post("/support", dependencies=[Depends(authorized)])
async def support(body: SupportRequest):
    key, _ = store.new_request(body.question)
    try:
        # Operational routes work without installing model/MCP dependencies.
        from .agent import investigate
        result = await asyncio.wait_for(investigate(body.question), timeout=180)
    except Exception:
        result = dict(summary="Investigation unavailable; escalate to the platform owner.",
                      evidence=[], runbooks=[], next_steps=["Inspect job logs manually."], escalate=True,
                      mode=os.getenv("MODEL_MODE", "offline"), trace=[])
    store.complete_request(key, result)
    return dict(request_id=key, **result)

@app.post("/support/{key}/feedback", dependencies=[Depends(authorized)])
def feedback(key: str, body: Feedback):
    if not store.rows("SELECT id FROM requests WHERE id=?", (key,)):
        raise HTTPException(404, "Unknown request")
    import time
    store.execute("UPDATE requests SET helpful=?, resolved=CASE WHEN ? THEN ? ELSE resolved END WHERE id=?",
                  (int(body.helpful), body.resolved, time.time(), key))
    return {"saved": True}

@app.post("/webhooks/alerts", dependencies=[Depends(authorized)])
def alerts(body: dict):
    accepted = []
    for alert in body.get("alerts", [])[:100]:
        fingerprint = alert.get("fingerprint")
        if not fingerprint:
            continue
        identity = "alert:" + fingerprint
        if alert.get("status") == "resolved":
            store.resolve(identity)
        elif alert.get("status") == "firing":
            item, created = store.incident(identity, alert.get("annotations", {}).get("summary", "Platform alert"), "alertmanager")
            accepted.append({"id": item["id"], "created": created})
    return {"accepted": accepted}
