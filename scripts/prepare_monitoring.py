"""Generate a loopback-only native test profile; does not download or start tools."""
import argparse
import json
from pathlib import Path
import sqlite3
from platformcare.settings import ROOT, db_path, token

def prepare(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    rules = str(ROOT / "infra/alerts.yml")
    prometheus = {
        "global": {"scrape_interval": "5s", "evaluation_interval": "5s"},
        "rule_files": [rules],
        "alerting": {"alertmanagers": [{"static_configs": [{"targets": ["127.0.0.1:19093"]}]}]},
        "scrape_configs": [{"job_name": "platformcare", "static_configs": [{"targets": ["127.0.0.1:18000"]}]}],
    }
    alertmanager = {
        "route": {"receiver": "platformcare", "group_by": ["alertname"], "group_wait": "5s", "group_interval": "10s", "repeat_interval": "1h"},
        "receivers": [{"name": "platformcare", "webhook_configs": [{
            "url": "http://127.0.0.1:18000/webhooks/alerts", "send_resolved": True,
            "http_config": {"authorization": {"type": "Bearer", "credentials": token()}}
        }]}],
    }
    for name, value in [("prometheus.json", prometheus), ("alertmanager.json", alertmanager)]:
        path=destination/name
        path.touch(mode=0o600, exist_ok=True)
        path.chmod(0o600)
        path.write_text(json.dumps(value, indent=2))
    provision = destination / "provisioning"
    for section in ("datasources", "dashboards", "plugins", "alerting"):
        (provision / section).mkdir(parents=True, exist_ok=True)
    (provision / "datasources/prometheus.yaml").write_text(json.dumps({
        "apiVersion": 1, "datasources": [{"name": "Prometheus", "uid": "platform-prometheus", "type": "prometheus", "access": "proxy", "url": "http://127.0.0.1:19090", "isDefault": True}]
    }))
    (provision / "dashboards/platform.yaml").write_text(json.dumps({
        "apiVersion": 1, "providers": [{"name": "PlatformCare", "type": "file", "options": {"path": str(ROOT / "infra/grafana/dashboards")}}]
    }))
    (destination / "grafana.ini").write_text(f"""[server]
http_addr = 127.0.0.1
http_port = 13001
[paths]
data = {destination}/grafana-data
logs = {destination}/grafana-logs
plugins = {destination}/plugins
provisioning = {provision}
[analytics]
reporting_enabled = false
check_for_updates = false
check_for_plugin_updates = false
[plugins]
preinstall_disabled = true
plugin_admin_enabled = false
[auth.anonymous]
enabled = true
org_role = Viewer
[log]
mode = console
level = warn
""")
    source = db_path().resolve()
    target = destination / "platform.db"
    if source.exists() and not target.exists():
        with sqlite3.connect(source) as old, sqlite3.connect(target) as new:
            old.backup(new)
    print("Native monitoring profile prepared; no services started.")
    print("Ports: API 18000, Prometheus 19090, Alertmanager 19093, Grafana 13001")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("destination")
    prepare(parser.parse_args().destination)
