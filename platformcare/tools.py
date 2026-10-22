import re
import httpx
import os
from . import store
from .pipeline import health
from .settings import ROOT

def get_service_health() -> dict:
    """Get current customer impact, latest job, owner and data freshness."""
    return health()

def search_logs(run_id: str) -> list:
    """Read up to 30 recent redacted logs for one exact job ID."""
    return store.rows("SELECT * FROM logs WHERE run_id=? ORDER BY ts DESC LIMIT 30", (run_id,))

def search_runbooks(query: str) -> list:
    """Retrieve up to three local troubleshooting passages by lexical relevance."""
    words = set(re.findall(r"[a-z_]+", query.lower()))
    results = []
    for path in sorted((ROOT / "runbooks").glob("*.md")):
        body = path.read_text()
        score = len(words & set(re.findall(r"[a-z_]+", body.lower())))
        if score:
            results.append(dict(source=f"runbooks/{path.name}", passage=body[:5000], score=score))
    return sorted(results, key=lambda x: x["score"], reverse=True)[:3]

def get_incidents() -> list:
    """Read the 20 latest incidents, including unresolved incidents."""
    return store.rows("SELECT * FROM incidents ORDER BY opened DESC LIMIT 20")

def query_metrics(metric: str = "freshness") -> dict:
    """Query an allowlisted Prometheus expression; report unavailable rather than fabricate."""
    queries = {"freshness": "platform_freshness_seconds", "failed": "platform_failed_runs",
               "latency": "platform_last_run_duration_seconds"}
    if metric not in queries:
        return {"error": "Metric must be freshness, failed, or latency"}
    try:
        response = httpx.get(os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090") + "/api/v1/query",
                             params={"query": queries[metric]}, timeout=3)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        return {"error": "Prometheus unavailable; use job/log evidence and report this gap"}

TOOLS = [get_service_health, search_logs, search_runbooks, get_incidents, query_metrics]
