"""A real aggregation workload with explicitly controlled synthetic faults."""
import argparse
import json
import time
from uuid import uuid4
from . import store

SCENARIOS = ("healthy", "invalid_input", "dependency_outage", "slow_job")

def run(scenario="healthy", source="manual"):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario")
    key, started = uuid4().hex[:12], time.time()
    store.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)",
                  (key, started, None, "running", scenario, source, 0, None))
    store.log(key, "INFO", "STARTED", f"Processing synthetic usage events; source={source}")
    status, output, records = "success", None, 0
    try:
        events = [{"service": "music", "minutes": 4}, {"service": "tv", "minutes": 12},
                  {"service": "music", "minutes": 8}]
        if scenario == "invalid_input":
            events.append({"service": "music", "minutes": -3})
        if scenario == "dependency_outage":
            raise ConnectionError("Controlled dependency outage; aggregate sink unavailable")
        if scenario == "slow_job":
            time.sleep(3)
            store.log(key, "WARNING", "SLOW_JOB", "Controlled processing delay exceeded 2-second demo latency objective")
        totals = {}
        for event in events:
            if event["minutes"] < 0:
                raise ValueError("Validation failed: minutes must be nonnegative")
            totals[event["service"]] = totals.get(event["service"], 0) + event["minutes"]
        output, records = json.dumps(totals), len(events)
        store.log(key, "INFO", "COMPLETED", f"Aggregated {records} synthetic records")
    except (ValueError, ConnectionError) as error:
        status = "failed"
        code = "VALIDATION_FAILED" if isinstance(error, ValueError) else "DEPENDENCY_UNAVAILABLE"
        store.log(key, "ERROR", code, str(error))
    store.execute("UPDATE runs SET finished=?,status=?,records=?,output=? WHERE id=?",
                  (time.time(), status, records, output, key))
    if status == "failed":
        store.incident("pipeline-failure", "Usage aggregate pipeline failed", "pipeline")
    else:
        store.resolve("pipeline-failure")
    if scenario == "slow_job":
        store.incident("pipeline-slow", "Usage aggregate exceeded latency objective", "pipeline")
    elif status == "success":
        store.resolve("pipeline-slow")
    return store.rows("SELECT * FROM runs WHERE id=?", (key,))[0]

def health():
    latest = store.rows("SELECT * FROM runs ORDER BY started DESC LIMIT 1")
    good = store.rows("SELECT finished FROM runs WHERE status='success' ORDER BY finished DESC LIMIT 1")
    age = max(0, time.time()-good[0]["finished"]) if good else None
    state = "unknown"
    if latest:
        last = latest[0]
        too_slow = last["finished"] is not None and last["finished"] - last["started"] > 2
        state = "degraded" if last["status"] == "failed" or too_slow or age is None or age > 300 else "healthy"
        if latest[0]["status"] == "running":
            state = "running"
    return dict(service="usage-analytics", owner="demo-data-team", impacted_consumer="Daily usage dashboard",
                status=state, freshness_seconds=age, freshness_objective_seconds=300,
                latest_run=latest[0] if latest else None, workload="synthetic")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=SCENARIOS, default="healthy", nargs="?")
    print(json.dumps(run(parser.parse_args().scenario), indent=2))
