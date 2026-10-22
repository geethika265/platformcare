"""Verify real scrapes, firing/resolved alert delivery and provisioned Grafana."""
import json
import time
from pathlib import Path
import httpx
from platformcare.settings import ROOT, token

API="http://127.0.0.1:18000"
PROM="http://127.0.0.1:19090"
GRAF="http://127.0.0.1:13001"
HEADERS={"X-Platform-Token":token()}

def get(url, **kwargs):
    response=httpx.get(url,timeout=5,**kwargs)
    response.raise_for_status()
    return response.json()

def wait_for(check, seconds=55):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=check()
        if value:
            return value
        time.sleep(2)
    raise TimeoutError("Expected monitoring state was not observed within deadline")

def overview():
    return get(API+"/overview",headers=HEADERS)

def main():
    report={"kind":"native Prometheus/Alertmanager/Grafana integration", "checks":{}}
    def run(scenario):
        response=httpx.post(API+"/runs",headers=HEADERS,json={"scenario":scenario,"source":"evaluation"},timeout=10)
        response.raise_for_status()
        return response.json()
    def firing():
        alerts=get(PROM+"/api/v1/alerts")["data"]["alerts"]
        return [a for a in alerts if a["labels"]["alertname"]=="UsagePipelineFailed" and a["state"]=="firing"]
    def webhook_open():
        return [i for i in overview()["incidents"] if i["origin"]=="alertmanager" and not i["resolved"] and "Usage aggregate failed" in i["title"]]
    try:
        targets=wait_for(lambda:[t for t in get(PROM+"/api/v1/targets")["data"]["activeTargets"] if t["health"]=="up"])
        report["scrape_targets"]=[{"health":t["health"],"job":t["labels"].get("job")} for t in targets]
        report["checks"]["scrape_up"]=True
        query=get(PROM+"/api/v1/query",params={"query":"platform_support_requests"})
        report["support_metric"]=query["data"]["result"]
        report["checks"]["support_metric_available"]=bool(query["data"]["result"])
        datasource=get(GRAF+"/api/datasources/uid/platform-prometheus/health")
        report["checks"]["grafana_datasource_healthy"]=datasource.get("status")=="OK"
        dashboard=get(GRAF+"/api/dashboards/uid/platformcare")
        report["dashboard"]={"title":dashboard["dashboard"]["title"],"panels":len(dashboard["dashboard"]["panels"])}
        report["checks"]["dashboard_provisioned"]=True
        failed=run("invalid_input")
        report["failed_run_id"]=failed["id"]
        wait_for(firing)
        report["checks"]["failure_alert_fired"]=True
        print("Failure alert firing in Prometheus",flush=True)
        incident=wait_for(webhook_open)[0]
        report["webhook_incident_id"]=incident["id"]
        report["checks"]["webhook_incident_opened"]=True
        print("Alertmanager webhook created an incident",flush=True)
        run("healthy")
        wait_for(lambda:not firing())
        report["checks"]["failure_alert_cleared"]=True
        wait_for(lambda:any(i["id"]==incident["id"] and i["resolved"] for i in overview()["incidents"]))
        report["checks"]["webhook_incident_resolved"]=True
        report["checks"]["platform_recovered"]=overview()["health"]["status"]=="healthy"
        print("Recovery cleared the alert and resolved its webhook incident",flush=True)
    except Exception as error:
        # This report contains no API credentials or request headers.
        report["error_type"]=type(error).__name__
    output=ROOT/"output/evaluation-monitoring.json"
    output.parent.mkdir(exist_ok=True)
    report["passed"]=len(report["checks"])==9 and all(report["checks"].values())
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not report["passed"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
