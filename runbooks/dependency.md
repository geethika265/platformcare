# Dependency unavailable: DEPENDENCY_UNAVAILABLE

Symptoms: a controlled ConnectionError prevents publishing aggregates to the simulated sink.
Impact: a previous successful output, if one exists, remains available but becomes stale. If health reports no successful history, there is no published aggregate to fall back on.

1. Confirm DEPENDENCY_UNAVAILABLE in logs for the failed run.
2. In a real platform, inspect the sink's network reachability, health and credentials without exposing secrets.
3. In this lab the outage is injected, not an actual database outage. Run the healthy scenario to clear it.
4. Verify a successful output and freshness; avoid repeatedly retrying a persistently unavailable dependency.

Owner: demo-data-team. Escalate sustained dependency failures with timestamps and run ID.
