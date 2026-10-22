# Stage 3: hosted model setup without downloading a model

Recommended first provider for this synthetic-data prototype: Groq Free plan. Its official documentation lists free quotas, local tool calling, and an OpenAI-compatible endpoint. Access and per-model limits depend on your account. Stay on the Free plan; a paid upgrade is unnecessary for these checks.

1. Open https://console.groq.com/keys and create an account/API key yourself.
2. Copy `.env.example` to `.env` if you do not already have a local environment file.
3. Set these values locally; never paste a key into chat, screenshots, or source control:

```dotenv
MODEL_MODE=live
MODEL_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=openai/gpt-oss-20b
MODEL_API_KEY=your-key-here
```

This model was available on the configured Groq account and completed live MCP-backed investigation checks on 2026-10-22. The initially suggested Qwen model encountered rate-limit/service errors in testing. Availability and quotas can change; the host is configurable so another supported tool-calling model can be substituted without changing MCP tools.

Restart the API after editing `.env`. Request an investigation from the dashboard. The model receives synthetic operational evidence, chooses tools, and returns its summary. The tools themselves remain local and are invoked via stdio MCP; Groq does not need inbound access to your laptop.

Verify the trace includes a health check and relevant job logs/runbook retrieval. Check the claimed cause against the actual failure and verify all cited paths. Repeat with dependency failure, slow processing, and missing history. Record actual outcomes, not just successful HTTP responses. A 429 means a provider rate limit: wait and retry later; don't enable paid billing just to complete the prototype.

Offline mode and tests with simulated model replies are useful for verifying orchestration. They do not count as a live model evaluation. No hosted API call is made by the automated tests.

For an explicit live smoke test, run `python -m scripts.evaluate_live invalid_input`.
Each invocation uses an isolated temporary synthetic database and saves its result under `output/evaluation-live-<scenario>.json`. Other cases are `dependency_outage`, `slow_job`, `healthy`, and `missing_history`. This command sends real requests; the ordinary pytest suite does not.

Sources:

- Free plan quotas: https://console.groq.com/docs/rate-limits
- Tool support: https://console.groq.com/docs/tool-use/overview
- Endpoint: https://console.groq.com/docs/openai
- Model availability/preview status: https://console.groq.com/docs/models
