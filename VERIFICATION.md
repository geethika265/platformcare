# Verification record — 2026-10-22

## Observed results

- `python -m pytest -q`: **16 passed** in 5.29 seconds using a temporary Python 3.12 environment. One upstream FastAPI/Starlette TestClient deprecation warning remains; no test failures.
- Stage 1: authenticated API, healthy aggregation, invalid input, dependency fault, job-scoped logs, stale output, slow-job health classification, incident recovery, alert identity, support metrics and redaction covered.
- Stage 2: Streamlit AppTest exercised dashboard controls against the actual FastAPI application using an in-process transport. Healthy -> invalid-input failure -> recovery matched job status, logs and incident counts. Investigation and feedback widgets passed.
- Browser check on the actual local servers independently confirmed healthy -> degraded -> healthy. Latest failure log included `VALIDATION_FAILED`; the incident moved from OPEN to RESOLVED.
- Dashboard MCP investigation returned the failed run ID, matching validation log and `runbooks/validation.md`. This was explicitly **offline replay**, not live inference.
- Stage 3: real MCP initialize/discovery/tool calls ran through a separate stdio server process. Simulated model responses exercised the live orchestration branch: health -> logs -> runbooks -> structured summary. Tests also verified malformed model output and invented runbook citations trigger escalation.

## Fixes made during checks

1. Added an authenticated job-log endpoint and a dashboard log selector.
2. Changed slow-job health to degraded until a fast successful recovery.
3. Added strict agent response validation, including boolean escalation and string-list fields.
4. Restricted runbook citations to exact source fields returned by retrieval.

## Screenshots

- `output/stage2-failure.png`: degraded health and one open incident.
- `output/stage2-recovery.png`: healthy output and zero open incidents.
- `output/stage3-mcp-evidence.png`: validation evidence and retrieved runbook in the dashboard.

## Still unverified

- Broad hosted-model accuracy, healthy/slow-job live cases, and sustained provider reliability remain unverified. Three live smoke scenarios have now run; see the Stage 3 addendum below.
- Real Slack commands and delivery: needs a test Slack app.
- Prometheus, Alertmanager, Grafana and Airflow container runtime: not started in these checks to respect storage/RAM constraints.
- Production load, real customers, multi-cloud scale, and operational improvement percentages: not claimed.

## Resource scope

Docker stayed off. The temporary environment reused the bundled runtime's NumPy/Pandas and occupied approximately 272 MB during verification. It is disposable; verification does not require keeping services running. Source, tests, screenshots and the small local SQLite demo history are preserved.

## Stage 3 live-model addendum

User configured a Groq API key locally. Configuration presence was checked without printing the key. Three isolated synthetic smoke tests then completed using Groq-hosted `openai/gpt-oss-20b`:

| Scenario | Observed tool/evidence behavior | Outcome |
| --- | --- | --- |
| Invalid input | Health, exact job logs, validation runbook, failed job ID in evidence | Passed smoke assertions; final summary described validation failure and no produced aggregate |
| Dependency outage | Health, exact job logs, dependency runbook, failed job ID in evidence | Passed smoke assertions; returned troubleshooting steps and escalation |
| Missing history | Health check, explicit uncertainty, no invented job evidence or runbook citation | Passed smoke assertions; escalated |

Reports are `output/evaluation-live-invalid_input.json`, `output/evaluation-live-dependency_outage.json`, and `output/evaluation-live-missing_history.json`. These are separate from offline replay and simulated-provider unit tests. Three smoke cases do not establish a production accuracy rate. Operational recommendations remain subject to human review; the dependency failure is injected, not evidence of a real database/network outage.

Live testing exposed and prompted fixes:

- Reserved a final synthesis round after the investigation budget, rather than falling back just because the fifth tool consumed the last round.
- Instructed the agent to prefer health -> exact logs -> matching runbook, reducing unnecessary API calls.
- Added one bounded retry for HTTP 429, respecting numeric Retry-After up to 30 seconds; longer waits or repeated failures return control rather than retrying indefinitely.
- Corrected prompt/runbooks so no successful history is not described as an available previous output.
- Preserved the initial Qwen model's rate-limit/service problems in this record and switched the local model setting after the alternative succeeded.
- Re-ran the targeted agent regression suite after these changes: **5 passed** in 2.41 seconds, including the final-synthesis-budget regression. The full dashboard suite was not rerun during this live-only check.

No Docker, Streamlit server, API server, or local model was started for this live check. The temporary MCP/API environment was approximately 40 MB including test tools and is removed after verification. The `.env` key remains local with owner-only permissions.

## Stage 4 local handler checks

`python -m pytest tests/test_slack_bot.py -q`: **12 passed** in 0.24 seconds. Tests used a fake Slack client, temporary SQLite databases and simulated investigation responses. They made no Slack posts, opened no Slack connection, and called no hosted LLM.

Verified handler behavior: acknowledgment before work; duplicate command deduplication; immediate health response for absent history; threaded support answers; failed delivery remains unanswered and avoids starting inference; model failures produce an escalation response; long responses preserve evidence/next steps across valid Slack blocks; helpful/not-helpful and escalation actions persist; incident posts and resolutions avoid repetition under normal polling; historical resolved incidents are not replayed; investigation work is bounded to one active and one queued request; manifest commands match handlers.

Code changes: lazy loading of model dependencies, bounded worker queue, threaded investigations, safe delivery status recording, not-helpful feedback, full response blocks, and a poller that skips old resolved incidents. Added `scripts/configure_slack.py` for hidden local token input and `docs/STAGE4_SLACK_SETUP.md` for workspace/app setup.

**Still pending:** user-created test workspace, app installation/permissions, bot and app-level tokens, real Socket Mode connection, actual Slack commands/buttons, and actual incident notifications. Stage 4 is not yet verified end to end. Temporary test dependencies are removed after local verification; no bot/server is left running.

## Stage 4 live Slack progress

The user created PlatformCare Lab, installed the app, saved both tokens locally, and added PlatformCare to `#new-channel`. The bot connected over Socket Mode. User-provided screenshots verify `/platform-health` returned a degraded status and `/platform-help` produced a live threaded investigation with evidence and the validation runbook.

The local record for request `3f8ecfbf0174` independently confirms an answered live request, MCP tools `get_service_health`, `search_logs`, and `search_runbooks`, and citation `runbooks/validation.md`. Request-to-recorded-response time was 6.06 seconds for this single demo request; it is not a benchmark or production improvement claim. The failed run ID in the answer matches the prepared synthetic case, `490bcbb96e03`.

Feedback buttons, `/incident-summary`, and automatic incident/resolution delivery remain to be checked live. Automatic alerts are disabled because no alert channel has been configured. Only the Slack bot remains running during user testing; its temporary environment occupies about 33 MB. Docker, API and dashboard services are off.

The user then clicked Helpful. The local support record confirms `helpful=1`. A healthy recovery workload completed successfully, returned platform health to healthy, and left zero open pipeline-origin incidents. The user can now check the updated status through `/platform-health`; automated notification delivery is still disabled and unverified.

## Stage 5 native monitoring integration

Ran actual Apple Silicon native Prometheus **3.13.5**, Alertmanager **0.34.1**, and Grafana OSS **13.2.4** with a temporary FastAPI metrics service. Downloads matched their published SHA-256 values. Docker, Airflow, Slack and hosted-model inference were not run during this check.

`python -m scripts.verify_monitoring`: **9 live checks passed**:

1. Prometheus scrape target was up.
2. Real support metrics were queryable.
3. Grafana's Prometheus datasource health check returned OK.
4. The ten-panel customer-impact dashboard was provisioned.
5. A controlled validation failure triggered `UsagePipelineFailed` in Prometheus.
6. Alertmanager delivered an authenticated webhook that opened an incident.
7. A healthy run cleared the failure alert.
8. A resolved webhook closed that same monitoring-origin incident.
9. Platform health returned to healthy.

Evidence: `output/evaluation-monitoring.json` and `output/stage5-grafana.png`. The browser independently showed actual data for output age, successful-output presence, failure state, open incidents, workload duration, support requests and response time. The chart includes the failure/recovery transition. No claim is made that all four alert conditions were fault-injected: the config validators accepted all four rules, while the end-to-end check exercised the pipeline-failure rule.

The native configuration passed `promtool check config` and `amtool check-config`. Grafana initially reported its Prometheus plugin missing because this release bundles it under `data/plugins-bundled/prometheus/`; retaining that required plugin fixed the real datasource check. Unrelated bundled datasources and debugging source maps were omitted. Added native preparation, bounded launcher and integration-check scripts plus a reproducibility guide and checksummed download manifest.

The test used a SQLite backup of project records. Test workloads and monitoring incidents affected only the temporary copy. Runtime tools/data used approximately 940 MB total during the check; at least about 2.3 GiB free disk remained. The launcher used Go memory targets, small retention settings, a 1.5 GiB free-disk stop floor, and a ten-minute lifetime. All four services are stopped and the native tools, temporary credentials/config and Python environment are removed at the end; only source, report and screenshot are retained.

A process-memory sample before shutdown showed **301.5 MB combined resident memory across the four services**. This is one observed sample, not a peak-RAM guarantee. Final browser verification showed a published output, no latest-job failure, zero open incidents and readable support chart legends.

Still pending: actual Airflow execution and automatic Slack incident/resolution notifications. Core Slack health/help/feedback and the native metrics/dashboard/alert/webhook flow have separate live evidence.

## Stage 6 actual Airflow execution

Installed Apache Airflow **3.3.2** in a dedicated temporary Python 3.12 environment using the official version/Python constraints. `python -m scripts.verify_airflow` initialized a temporary Airflow metadata database and ran the repository DAG three times through the actual `airflow dags test` CLI:

| Scenario | Airflow DAG/task states | CLI exit | Matching API source/status |
| --- | --- | --- | --- |
| Healthy | success / success | 0 | airflow / success |
| Invalid input | failed / failed | 1 | airflow / failed |
| Healthy recovery | success / success | 0 | airflow / success |

All three case assertions passed. Actual Airflow metadata, the `aggregate` task state, and pipeline records were compared; this is not a mocked DAG test. Full safe execution evidence is in `output/evaluation-airflow.json`. The API's model import was made lazy so operational routes can be tested without installing model/MCP dependencies into Airflow's constrained environment.

The test environment occupied approximately **255 MB**. Its local API and test-owned DAG processes stopped automatically; the environment, metadata, raw logs and downloaded constraints are removed after verification. Docker, a persistent scheduler/UI, Slack posting and LLM inference were not used. Existing project workload/support records were not changed by the isolated test.

The scheduler's continuous two-minute cadence, Airflow UI, container deployment and multi-worker production behavior remain unverified. Automatic Slack incident/resolution notifications are also still a separate unverified integration; Slack command/AI-thread/Helpful feedback and monitoring webhook delivery have their own live evidence.


## Optional extension checks — 2026-10-23

Added opt-in Spark example, Flink SQL Gateway/Trino/Druid SQL checks, Splunk HEC sender, and PagerDuty trigger/resolve sender. None is wired into the core incident flow or launched automatically. No optional engine, Jupyter installation, or additional dependency was downloaded.

`python3 -m unittest discover -s tests -p test_optional_services.py -v`: **8 passed** using fake transports. These check response contracts, SQL/payload construction, result mismatches, Flink cleanup, stable PagerDuty correlation keys, and rejection of insecure remote URLs/cross-origin pagination. They do not prove live compatibility with those services. Spark source was syntax-checked only; no Spark runtime was available.

All **4 notebook code cells** executed as ordinary Python against the existing local synthetic SQLite database using read-only connections. The notebook has no persisted outputs or credentials. No Jupyter kernel/server was launched, so Jupyter runtime compatibility remains unverified.

Added customer/support metric definitions and documented AI-review examples grounded in prior test failures and fixes. Real peer feedback, owner presentation, manual-versus-assisted support-time measurement, optional vendor/engine runtime tests, and multi-cloud deployment remain absent. Optional source is not a basis for claiming those technologies as verified experience.
