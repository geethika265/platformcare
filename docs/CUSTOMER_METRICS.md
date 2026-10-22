# Customer-focused observability

The customer is an engineer waiting for the synthetic daily usage aggregate. The owner is `demo-data-team`, the consumer is `Daily usage dashboard`, and the freshness objective is 300 seconds. This is a local lab, not a production SLO claim.

| Signal | Meaning for the customer | Implementation and next step |
| --- | --- | --- |
| Published output exists | There is data the consumer can use | `platform_has_success`; investigate the first run when zero |
| Output age | Whether available data is fresh enough | `platform_freshness_seconds`; compare with the 300-second objective |
| Latest job failed | The current attempt did not publish output | `platform_latest_failed`; inspect its exact run ID and error log |
| Duration | The current workload may be delayed | `platform_last_run_duration_seconds`; 2-second synthetic latency objective |
| Open incidents | Unresolved issues needing attention | `platform_support_open_incidents`; distinguish pipeline and monitoring origins |
| Failed runs | Count of retained failed jobs | `platform_failed_runs`; this is a gauge over stored history, not a monotonic counter |
| Support requests/unanswered | Request volume and outstanding investigations | `platform_support_requests` and `platform_support_unanswered` |
| First response | Time from request creation to recorded answer | `platform_support_mean_first_response_seconds`; recording time is not guaranteed Slack delivery time |
| Resolution | Mean elapsed time for resolved incidents | `platform_support_mean_resolution_seconds`; exclude unresolved incidents |
| Feedback | Fraction of recorded votes marked helpful | `platform_support_helpful_rate`, shown with `platform_support_feedback_count` |

The Grafana dashboard has ten panels; not every listed metric has its own panel. Streamlit also exposes job details, incidents, investigation output, and feedback. Metrics with no observations are omitted rather than represented as measured zero. Notebook counts/averages are another view of the same SQLite sample.

## Self-service workflow

1. Ask `/platform-health` for current impact and output freshness.
2. Ask `/platform-help Why did the pipeline fail?`.
3. The host invokes read-only MCP health, exact job-log, and runbook tools. The live model returns an investigation summary and next steps with supporting run IDs and retrieved sources.
4. Mark Helpful, Not helpful, or Escalate; review the recorded feedback/sample size.
5. An operator runs the healthy scenario and checks recovery. The agent does not repair a pipeline itself.

Health, live investigation, and Helpful feedback were tested in the Slack workspace. `/incident-summary` is implemented but has not been separately confirmed live. Automatic incident channel notifications remain unverified.

## Evaluate usefulness without inventing savings

Ask a peer to find the failure manually, then investigate a comparable failure using the tool. Record tasks, correctness, elapsed time, sample size, and task order. Collect genuine feedback with `docs/DEMO.md`. No manual-versus-assisted performance improvement has yet been measured.
