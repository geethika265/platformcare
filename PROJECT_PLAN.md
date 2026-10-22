# PlatformCare: Data Platform Health and Support Copilot

## Purpose

Build a portfolio project aligned with the supplied Apple ASE Data Platform Intern, 2027 job description: customer-facing operational dashboards, AI-assisted support, Slack integrations, observability, and tool orchestration.

This is a proposed project, not completed experience. A project can demonstrate technical requirements and provide evidence of communication and iteration; it cannot establish real multi-cloud scale or replace collaboration with actual SREs.

## Product scenario

A small internal analytics team depends on a scheduled event-processing pipeline. When its output becomes stale, an engineer needs to know what is affected, which job failed, what evidence supports a diagnosis, and what to do next.

Use synthetic service-usage events. Run an actual Apache Airflow DAG that validates and aggregates them into PostgreSQL. Keep a last-known-good output so freshness and availability can be distinguished. Use deterministic fault injection for a failed validation step, an unavailable database, and an intentionally slow task.

## Core stack

- Python and FastAPI: support API, health endpoints, fault controls for the local demo.
- Airflow: a real scheduled data workflow and task execution history.
- PostgreSQL: pipeline outputs, incident lifecycle, support requests, and feedback.
- Prometheus and Alertmanager: metrics, rule-based detection, grouping, and notification routing.
- Grafana: platform health and support dashboards; PostgreSQL can supply support metrics.
- Python structured logging: searchable logs with timestamps, job IDs, incident IDs, and severity; a bounded log API suffices initially.
- LangGraph and an LLM API: evidence-gathering, triage, runbook retrieval, and incident summaries.
- MCP server and client: expose and invoke operational tools over MCP.
- Slack Bolt for Python: commands, event handling, and threaded replies.
- Docker Compose and GitHub Actions: reproducible local setup and verification.

Do not add Spark, Flink, Trino, Kubernetes, multiple clouds, Splunk, or PagerDuty just to collect technology names. The JD gives examples and alternatives. Add Spark only after the integrated core works, if time permits.

## Requirements and evidence

| JD requirement | Implementation | Portfolio evidence |
| --- | --- | --- |
| Python applications and scripts | FastAPI service, telemetry exporter, fault runner | Readable source, API examples, tests |
| REST APIs and webhooks | Health/support endpoints, alert receiver, Slack integration | API contract and event-flow demo |
| Customer-focused visualization | Freshness, failed jobs, impacted team, owner, incident link, next step | Dashboard screenshots and provisioned configuration |
| Platform health and incident trends | Up status, duration, failures, incident history | Failure-and-recovery walkthrough |
| Support metrics | Request volume, first-response time, resolution time, escalation and helpfulness | Dashboard with explicitly labeled seeded or measured data |
| LLM agents, prompts, tool calling | Structured triage graph and evidence-based summary | Prompt files and tool traces |
| MCP orchestration | MCP client invokes metrics, logs, job, and runbook tools | Integration test and captured trace |
| Observability | Prometheus metrics, Alertmanager rules, Grafana panels | Reproducible alert and dashboard demo |
| Slack bot | Health command, support request, incident thread, feedback | Working Slack app and recorded demo |
| Big data platform exposure | Real Airflow DAG with controlled faults | DAG code, execution history, explanation of platform role |
| Reduce manual support toil | Compare a manual investigation checklist with the assistant | Evaluation report with task and timing definitions |
| Collaboration and iteration | Ask peers to act as platform customers and review the prototype | Anonymized feedback, issues, before/after changes |
| Documentation and presentation | Architecture, setup, operator guide, user guide, short demo | Maintainer can reproduce a scenario |
| AI-assisted development with review | Use an assistant for a bounded implementation task and review changes | One documented example of an error found and corrected |
| Degree eligibility | Already represented in the resume | Project does not substitute for eligibility |

## Dashboard design

The first view answers: Is my data ready? What is affected? Who owns the issue? What can I do?

Show data age relative to its freshness objective, last successful run, current failed task, affected consumer/team, active incident, and runbook link. Put detailed infrastructure graphs in a drill-down view.

Track request volume, acknowledgment latency, first useful response, resolution time, escalations, and user feedback. Define timestamps and denominators. Calculate resolution statistics only for resolved incidents; show open incident age separately. Mark synthetic records and simulated users clearly. Distinguish data freshness from service availability.

## Agent contract

Expose tools such as:

- `get_service_health(service)`
- `query_metrics(service, metric_name, start, end)` using an allowlist of query templates
- `search_logs(job_id, start, end, limit)`
- `get_job_status(dag_id, run_id)`
- `search_runbooks(query)`
- `get_incident(incident_id)`

Invoke these through an actual MCP client-server connection. Ordinary Python function calls alone do not demonstrate MCP.

Return structured output: affected service, impact, observed evidence, likely cause, uncertainty, cited runbook passages, recommended next steps, and escalation reason. Link evidence to job/log identifiers and time windows. Report insufficient evidence when appropriate.

Keep the MVP agent investigative: it recommends actions and hands unresolved cases to a person. Do not build automatic production remediation. Use bounded tool calls and time windows, handle tool failures, and redact synthetic secret patterns before sending logs to the model. Treat log and runbook content as data, not instructions.

## Slack experience

- `/platform-health`: service and pipeline freshness summary with dashboard link.
- `/platform-help <question>`: collect request context and start a support thread.
- `/incident-summary <id>`: summarize an existing incident and cite its evidence.
- Alert notification: one incident thread, with updates and resolution attached to it.
- Feedback: useful/not useful and escalate actions, persisted as support records.

Acknowledge commands promptly before starting LLM work. For HTTP event delivery, verify signatures and deduplicate retries. Alertmanager owns notification grouping; application incident identity prevents duplicate records and threads. A webhook-only notification demo does not cover interactive Slack support.

## Suggested schedule

Planning estimate: 4-6 weeks at approximately 10-15 focused hours per week; adjust after checking local runtime requirements and existing familiarity.

1. Week 1: Airflow-to-PostgreSQL workflow, logs, metrics, health API, one reproducible failure.
2. Week 2: Prometheus alerts, Alertmanager, incident lifecycle, Grafana customer overview.
3. Week 3: Slack commands, asynchronous replies, incident threading, support metrics.
4. Week 4: MCP tools, agent investigation, versioned runbooks, cited summaries.
5. Week 5: Evaluation, retries and tool failures, two peer feedback sessions, fixes.
6. Week 6 if needed: setup verification, documentation, demonstration, optional Spark extension.

The first deliverable is one complete vertical slice: failed DAG -> alert -> incident -> dashboard -> Slack investigation -> cited next step -> recovery. Extend breadth only after that works.

## Evaluation

Create at least 12 labeled cases covering validation failure, database outage, delayed processing, healthy state, missing runbook, and unavailable tool. Separate diagnosis cases from cases where abstaining or escalating is correct. Reserve some cases for final evaluation after prompt iteration.

Record alert detection delay, correct triage category, retrieved runbook relevance, supported versus unsupported summary claims, appropriate abstention, duplicate incident count, tool-call success, response latency, and model usage/cost. Set targets before final evaluation and publish actual results, including failures.

Compare manual and assisted investigation on the same task definitions. Counterbalance task order where possible and identify participant count and practice effects. With only yourself or a few peers, describe results as a small local evaluation; do not claim production MTTR reduction.

## Completion criteria

- A fresh setup can start the documented environment with prerequisites clearly stated.
- Three controlled failure scenarios and recovery produce correct state changes.
- A Slack user can investigate a failure using real operational evidence.
- Traces show the agent invoking MCP tools.
- Grafana displays customer impact and support workflow metrics.
- Slack retries do not create duplicate support records or incident threads.
- CI checks the API, incident transitions, tool contracts, and deterministic mocked-agent cases.
- A separately run live-model evaluation records actual outcomes.
- README, architecture, runbooks, evaluation report, screenshots, and a short demo are present.
- At least two documented feedback-driven improvements are shipped.

## Resume positioning after completion

Suggested title: Data Platform Observability and AI Support Copilot.

Write bullets from measured implementation facts: monitored an Airflow pipeline with Prometheus/Grafana; built MCP-backed incident investigation and cited runbook retrieval; integrated Slack self-service and incident threads. Add only evaluation numbers actually measured. Keep failure injection and synthetic workload context explicit where it matters.

The current resume summary targets wireless validation. For this application, revise it toward data-platform reliability, Python automation, observability, and AI-assisted internal support after the new evidence exists.

## Implementation references

- Slack acknowledgments: https://docs.slack.dev/tools/bolt-python/concepts/acknowledge/
- Slack HTTP request verification: https://docs.slack.dev/tools/bolt-python/reference/middleware/request_verification/request_verification.html
- Prometheus alerting architecture: https://prometheus.io/docs/alerting/latest/overview/
- MCP specification architecture: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/architecture/index.mdx
- Airflow core concepts: https://airflow.apache.org/docs/apache-airflow/stable/concepts.html
