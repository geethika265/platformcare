# Initial project scope: Data Platform Support Mini

This document records the initial prototype scope. The implementation subsequently expanded; consult README.md and VERIFICATION.md for the current features, verified results, and limitations.

## What to build

A Streamlit dashboard and Slack support bot for a small Python batch pipeline. The pipeline reads synthetic usage events, validates records, and produces a daily aggregate. Run it as a plain Python script; no Airflow setup in the core scope.

Create real successful and failed runs, persist their status and timestamps in SQLite, and write structured JSON logs. Include a controlled invalid-input failure. Label the workload as synthetic.

Streamlit shows last successful run, data freshness, failed-run count, current incident, and a suggested runbook. Slack supports `/platform-health` and `/platform-help <question>`. The help workflow lets an LLM call bounded tools to fetch job state, inspect recent logs, and search three local Markdown runbooks. Return a short diagnosis with job IDs and runbook references, or state that evidence is insufficient.

Share Python service functions across the dashboard and bot. Do not introduce a separate API backend unless needed for the chosen Slack transport.

## Core stack

Python, Streamlit, SQLite, Slack Bolt, one LLM API with tool calling, local Markdown runbooks. No vector database, LangGraph dependency, containers, or cloud deployment required for the core demo. Existing familiarity can justify using LangGraph, but it is optional.

Use Slack Socket Mode for the local prototype. That demonstrates a Slack app and API consumption, but not an HTTP webhook endpoint. Access to a workspace where an app can be installed and a model API credential are prerequisites. Without them, complete the local dashboard and tool workflow and describe Slack or live-model integration as unverified.

## Honest JD coverage

| Requirement | Initial prototype evidence |
| --- | --- |
| Python | Pipeline, dashboard, Slack handlers, investigation tools |
| API consumption | Slack API and model API |
| Dashboarding | Streamlit platform health and freshness view |
| Agent concepts, prompt design, tool calling | Three investigative tools and structured cited summary |
| Slack integration | Real health/help commands in a test workspace |
| Incident summary and documentation retrieval | Failure logs plus three searchable runbooks |
| Written/verbal communication | README and short narrated demo |
| AI-assisted development | Brief note describing a generated change reviewed and corrected |
| Portfolio | Repository, screenshots, setup instructions, demo |
| MCP | Stretch only: expose existing tools via MCP and actually invoke them through a client |
| Prometheus/Grafana or similar observability tooling | Not included; JSON logs and a custom dashboard provide only basic operational visibility |
| Big data technology | Not included; a Python batch script is not Airflow or Spark |
| HTTP webhooks | Not included with Socket Mode |
| Support analytics | Optional: persist support request time and first useful response; clearly label demo sample size |
| SRE collaboration and feedback-driven iteration | Not established by solo implementation; include a peer review only if it actually happens |
| Degree eligibility | Existing education, not a project feature |

Do not claim complete JD coverage. The JD accepts exposure to big data technologies or willingness to learn; most named tools are examples, not a checklist requiring all of them.

## Definition of done

1. Run the pipeline successfully; dashboard and Slack agree on its health.
2. Run invalid input; the dashboard shows the failed run and last successful output age.
3. Ask Slack for help; the agent fetches real run evidence and cites the matching validation runbook.
4. Give the agent insufficient evidence; it avoids inventing a cause.
5. Confirm Slack acknowledgment happens promptly and long model work runs asynchronously.
6. Save a short demo and instructions that another person can follow.

Investigative tools remain read-only. No automatic remediation is needed. Keep secrets out of source control and logs.

## Resume bullet after verification

Built a Python data-platform support prototype with a Streamlit health dashboard and Slack bot; integrated LLM tool calling to inspect batch-job logs and retrieve runbooks for incident triage.

Add MCP, webhooks, monitoring products, and evaluation figures only if implemented and verified.
