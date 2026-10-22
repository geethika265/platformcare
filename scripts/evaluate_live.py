"""One bounded live-model check per invocation using a temporary synthetic DB."""
import argparse
import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import httpx
from platformcare.agent import investigate
from platformcare.pipeline import run
from platformcare.settings import ROOT

async def main(scenario):
    report = {"kind": "live model + real MCP smoke test", "scenario": scenario,
              "tested_at": datetime.now(timezone.utc).isoformat(),
              "model": os.getenv("MODEL_NAME", ""), "passed": False}
    with tempfile.TemporaryDirectory(prefix="platformcare-live-") as directory:
        os.environ["PLATFORM_DB"] = str(Path(directory) / "evaluation.db")
        job = None if scenario == "missing_history" else run(scenario, "evaluation")
        try:
            result = await asyncio.wait_for(investigate("Investigate the current usage analytics state. Explain customer impact, cite job/log evidence and relevant runbook sources, and give next steps. If evidence is missing, explicitly escalate.", mode="live"), timeout=180)
            report["result"] = result
            tools = [entry["tool"] for entry in result["trace"] if not entry["is_error"]]
            expected = {"invalid_input": "runbooks/validation.md", "dependency_outage": "runbooks/dependency.md", "slow_job": "runbooks/latency.md"}.get(scenario)
            report["checks"] = {
                "checked_health": "get_service_health" in tools,
                "inspected_logs": "search_logs" in tools if job else None,
                "cited_expected_runbook": expected in result["runbooks"] if expected else None,
                "job_id_in_evidence": any(job["id"] in text for text in result["evidence"]) if job else None,
                "missing_history_escalated": result["escalate"] if not job else None,
                "structured_response": bool(result["summary"] and result["next_steps"]),
            }
            report["passed"] = all(value is not False for value in report["checks"].values())
        except httpx.HTTPStatusError as error:
            # No headers, credential-bearing request or full exception is saved.
            report["error"] = {"kind": "provider_http_error", "status": error.response.status_code}
        except (httpx.HTTPError, TimeoutError):
            report["error"] = {"kind": "connection_or_timeout"}
        except Exception as error:
            # Task-group context managers can wrap network errors in groups.
            pending = [error]
            report["error"] = {"kind": "orchestration_error"}
            while pending:
                item = pending.pop()
                if isinstance(item, BaseExceptionGroup):
                    pending.extend(item.exceptions)
                elif isinstance(item, httpx.HTTPStatusError):
                    report["error"] = {"kind": "provider_http_error", "status": item.response.status_code}
                    if item.response.status_code == 429:
                        report["error"]["retry_after"] = item.response.headers.get("retry-after")
                elif isinstance(item, (httpx.HTTPError, TimeoutError)):
                    report["error"] = {"kind": "connection_or_timeout"}
    folder = ROOT / "output"
    folder.mkdir(exist_ok=True)
    output = folder / f"evaluation-live-{scenario}.json"
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps({"scenario": scenario, "passed": report["passed"], "checks": report.get("checks"),
                      "error": report.get("error"), "report": str(output)}, indent=2))
    if not report["passed"]:
        raise SystemExit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["healthy", "invalid_input", "dependency_outage", "slow_job", "missing_history"], default="invalid_input", nargs="?")
    asyncio.run(main(parser.parse_args().scenario))
