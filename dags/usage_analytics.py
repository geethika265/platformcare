"""A real Airflow DAG orchestrates the local workload over its authenticated REST API."""
import json
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from airflow.sdk import dag, task, get_current_context

@dag(dag_id="usage_analytics", start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
     schedule="*/2 * * * *", catchup=False, tags=["platformcare", "synthetic"],
     params={"scenario": "healthy"})
def usage_analytics():
    @task(retries=0)
    def aggregate():
        context = get_current_context()
        scenario = context["dag_run"].conf.get("scenario", context["params"]["scenario"])
        payload = json.dumps({"scenario": scenario, "source": "airflow"}).encode()
        request = Request(os.environ["PLATFORM_API"] + "/runs", data=payload,
                          headers={"Content-Type": "application/json", "X-Platform-Token": os.environ["PLATFORM_TOKEN"]})
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        if result["status"] != "success":
            raise RuntimeError(f"Pipeline run {result['id']} failed; inspect PlatformCare logs")
        return result["id"]
    aggregate()

usage_analytics()
