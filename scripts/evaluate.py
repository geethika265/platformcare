"""Small deterministic MCP evaluation, not a live-model accuracy benchmark."""
import asyncio
import json
import os
import tempfile
from pathlib import Path
from platformcare.pipeline import run
from platformcare.agent import investigate

async def main():
    results = []
    with tempfile.TemporaryDirectory() as directory:
        for scenario, expected in [("healthy", "healthy"), ("invalid_input", "validation.md"),
                                   ("dependency_outage", "dependency.md"), ("slow_job", "latency.md")]:
            os.environ["PLATFORM_DB"] = str(Path(directory) / (scenario + ".db"))
            run(scenario, "evaluation")
            result = await investigate("Explain the current pipeline state", mode="offline")
            passed = expected in result["summary"] if scenario == "healthy" else any(expected in r for r in result["runbooks"])
            results.append(dict(scenario=scenario, passed=passed, **result))
        os.environ["PLATFORM_DB"] = str(Path(directory) / "empty.db")
        result = await investigate("Explain the current pipeline state", mode="offline")
        results.append(dict(scenario="missing_history", passed=result["escalate"] and not result["evidence"], **result))
    output = Path("output/evaluation-offline.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"kind": "offline MCP integration checks, not LLM accuracy", "cases": results}, indent=2))
    print(f"{sum(r['passed'] for r in results)}/{len(results)} offline checks passed; report: {output}")
    if not all(r["passed"] for r in results):
        raise SystemExit(1)

if __name__ == "__main__":
    asyncio.run(main())
