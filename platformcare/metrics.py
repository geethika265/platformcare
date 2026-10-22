from prometheus_client import CollectorRegistry, Gauge, generate_latest
from . import store
from .pipeline import health

def render():
    registry = CollectorRegistry()
    state = health()
    runs = store.rows("SELECT * FROM runs ORDER BY started DESC")
    latest = runs[0] if runs else None
    values = {
        "platform_has_success": (int(state["freshness_seconds"] is not None), "Whether a successful output exists"),
        "platform_freshness_seconds": (state["freshness_seconds"] or 0, "Age of last successful output; check platform_has_success"),
        "platform_latest_failed": (int(bool(latest and latest["status"] == "failed")), "Latest run failed"),
        "platform_failed_runs": (sum(r["status"] == "failed" for r in runs), "Failed runs retained in database"),
        "platform_last_run_duration_seconds": ((latest["finished"]-latest["started"]) if latest and latest["finished"] else 0, "Duration of latest completed run"),
    }
    for key, value in store.support_metrics().items():
        if value is not None:
            values["platform_support_" + key] = (value, "Support workflow metric: " + key)
    for name, (value, description) in values.items():
        Gauge(name, description, registry=registry).set(value)
    return generate_latest(registry)
