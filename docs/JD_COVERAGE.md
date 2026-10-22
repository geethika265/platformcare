# Evidence against the supplied JD

The architecture includes all named technical categories, using alternatives where the JD says "e.g.". Implemented code, locally tested behavior, and live external integration are different levels of evidence. Check VERIFICATION.md for observed runtime status.

| Requirement | Code/evidence | Remaining proof |
| --- | --- | --- |
| Python proficiency | Pipeline, API, MCP server/client, Slack handlers | Explain design and debugging choices yourself |
| Building/consuming APIs | FastAPI routes, LLM HTTP client, Slack SDK | Live Slack/model credentials |
| Webhooks | Authenticated Alertmanager receiver, dedup/resolution tests | Container notification flow |
| Prompt design and tool calling | System prompt, live model loop, bounded tool dispatch | Live tool-capable model evaluation |
| Dashboard libraries | Streamlit customer dashboard, Grafana provisioning | View and capture full-stack dashboard |
| MCP orchestration | Discovery, initialize, tools/call via stdio child process | Already covered by real-protocol local tests |
| Observability tooling | Prometheus exporter/rules, Grafana, Alertmanager | Container runtime verification |
| Slack integration | Health/help/incident commands, feedback, incident threads | Test app install and actual command execution |
| Big data ecosystem exposure | Real Airflow DAG orchestrates a job over REST | Trigger DAG in Airflow; explain scheduling/retries |
| Customer impact dashboards | Freshness, owner, consumer, next steps, open/resolved incidents | Peer usability feedback |
| Incident and support trends | Timestamped incident/request store; dashboard charts and metrics | Genuine feedback sample and longer observations |
| AI automation of support toil | Tool-driven evidence gathering and runbook retrieval | Measure manual-versus-assisted task time honestly |
| Rapid iteration | Editable local prototype, scenario runner | Actual documented feedback-driven revision |
| Maintainable documentation | README, runbooks, setup, architecture, demo | Fresh-user setup feedback |
| Presentation and communication | Demo script and technical explanation prompts | Record and present your own demo |
| AI-assisted development with review | Project developed with Codex; tests exposed real defects | Review the code and document your understanding/corrections |
| Portfolio | Complete source and reproducible commands | User-owned GitHub upload and video |
| Degree enrollment | Existing resume education | No project can replace eligibility |
| SRE/developer partnership | Not established by solo implementation | Real collaboration; do not fabricate it |

Not necessary to add every example technology: Grafana/Prometheus satisfy the observability examples; Streamlit satisfies dashboarding; Airflow provides one data-platform technology. Splunk, PagerDuty, Spark, Flink, and Trino are not all mandatory simultaneous tools. Multi-cloud scale is team context and is not demonstrated by this local lab.

Resume timing does not need to be stated. Scope, testing and outcomes must be accurate. Avoid a performance percentage until measured. Reframe the current resume summary from wireless validation toward this role only after you understand and can demonstrate this project.
