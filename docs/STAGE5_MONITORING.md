# Stage 5: real observability without Docker

Native Apple Silicon tools can verify the same monitoring flow without starting a Docker VM. This is a temporary local test profile, not a production deployment. See VERIFICATION.md for observed results.

## Components

- FastAPI serves real metrics from a temporary copy of the local job/support database.
- Prometheus scrapes every five seconds and evaluates the repository's four alert rules.
- Alertmanager groups notifications and sends authenticated firing/resolved webhooks to the API.
- Grafana uses a provisioned Prometheus datasource and customer-impact dashboard.

Only loopback ports are used: API 18000, Prometheus 19090, Alertmanager 19093, Grafana 13001. No Slack notifications or hosted-model calls are made by this profile. The API runs in offline mode.

## Download and storage scope

Published native archive URLs and SHA-256 checksums are recorded in `infra/native-downloads.json`. Verify checksums before running downloaded binaries. Use a dedicated temporary folder and delete archives after extraction.

Prometheus needs its server binary; `promtool` is useful for configuration checking and can then be removed. Alertmanager similarly uses its server binary, with `amtool` for initial checks.

For Grafana 13.2.4, retain `bin/`, `conf/`, and runtime assets under `public/`. Browser debugging source maps are optional. The required Prometheus datasource is packaged under **`data/plugins-bundled/prometheus/`** and must also be retained. Other bundled datasources are unnecessary for this dashboard. Preserve all files in that required plugin directory so its shipped bundle remains complete. Disable plugin preinstallation and update/usage checks for the temporary session.

The test launcher uses a 20 MB persistent-block retention target and one-hour retention. Prometheus WAL/head files have additional overhead: retention size is not a hard bound on the total directory size. The launcher independently checks free disk and stops if it falls below 1.5 GiB. It also stops after ten minutes and applies Go runtime memory targets. These are soft runtime targets, not operating-system RAM limits.

## Run after placing verified tools in the temporary folder

Use a Python environment containing the API dependencies. The folder layout is:

```text
temporary-folder/
  prometheus-3.13.5.darwin-arm64/prometheus
  alertmanager-0.34.1.darwin-arm64/alertmanager
  grafana-13.2.4/bin/grafana
  grafana-13.2.4/conf/...
  grafana-13.2.4/public/...
  grafana-13.2.4/data/plugins-bundled/prometheus/...
```

```bash
python -m scripts.prepare_monitoring /private/tmp/platformcare-monitoring/runtime
python -m scripts.run_monitoring_lab /private/tmp/platformcare-monitoring
```

The preparer writes owner-only JSON-as-YAML config files into the temporary runtime folder, including the current platform webhook token. Do not commit or share those generated files. Source templates contain no Groq or Slack tokens. Existing project data is copied using SQLite backup; the test workload changes only that copy.

In another terminal with the same Python environment:

```bash
python -m scripts.verify_monitoring
```

This waits for a real scrape, checks Grafana provisioning and datasource health, injects a failed run, observes a firing rule and webhook incident, then runs recovery and observes clearing/resolution. It saves `output/evaluation-monitoring.json`.

Inspect Grafana at `http://127.0.0.1:13001/d/platformcare`. The local profile permits anonymous Viewer access only; its administrator password is randomly generated at launch and is not printed. The customer overview states the consumer, owner, objective and troubleshooting entry point. Status panels are followed by job/support trend charts.

Stop the launcher with Ctrl+C before deleting its temporary directory. Keep only source, the small evaluation report and selected screenshots. Do not delete unrelated Docker images, containers or files.

## What the demonstration proves

A failure changes exported metrics, Prometheus detects it, Alertmanager delivers it, and recovery clears the condition. Grafana displays operational and support signals from actual local records. It does not demonstrate production scale, external paging availability, or multi-cloud operation. The API-down alert cannot deliver to an API receiver while that same API is unavailable; independent production paging needs an independent receiver.

## References

- Prometheus downloads/checksums: https://prometheus.io/download/
- Prometheus retention/WAL caveats: https://prometheus.io/docs/prometheus/latest/storage/
- Grafana OSS downloads/checksums: https://grafana.com/grafana/download?edition=oss&platform=mac
- Grafana configuration/plugin preinstallation: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/
