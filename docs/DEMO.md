# Three-minute demonstration

0:00 — Explain the customer: an engineer needs fresh daily usage data, not a wall of infrastructure graphs. Identify synthetic workload, owner, consumer and freshness objective.

0:25 — Show a healthy run, then trigger invalid input. Explain why a failed latest job and stale output are separate signals.

0:55 — Show incident state, log evidence and monitoring. If the full stack is available, show the firing Prometheus rule and Grafana panel. Do not present configuration files as runtime proof.

1:25 — Ask for support in Slack (or the dashboard if Slack is not yet configured). Show the tool trace: health -> logs -> runbook. Explain MCP as the interface between the assistant and operational tools. State whether the response is live inference or offline replay.

2:00 — Explain the cited runbook and proposed next step. Execute healthy recovery yourself, show the resolved incident and fresh output. The agent does not repair anything automatically.

2:30 — Show support response/feedback metrics and the test report. Explain one limitation and a concrete next improvement.

## Questions to prepare for

- Why measure data freshness separately from API availability?
- Which operations travel over MCP, and how can you prove it?
- How do duplicate alert deliveries and Slack retries behave?
- What happens when Prometheus, a tool, or the model is unavailable?
- Why does retrieval use lexical matching here? When would embeddings help?
- How do you prevent an agent from treating logs as instructions?
- What does the Airflow scheduler execute, and what makes its task fail?
- Which metrics are actually measured, and which claims have you deliberately not made?

## Feedback record (fill after a real session)

Participant/date:
Task attempted:
Observed difficulty:
Requested improvement:
Change shipped:
Recheck result:
