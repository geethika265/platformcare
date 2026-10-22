# Slow processing: SLOW_JOB and freshness

Symptoms: SLOW_JOB indicates a controlled three-second delay against the lab's two-second latency objective.
Impact: completion is delayed. A slow job can still publish valid results; it does not automatically mean data is stale.

1. Inspect the latest run duration and SLOW_JOB log.
2. Check last-success age independently against the five-minute data freshness objective.
3. Investigate input volume and dependency wait time; no real scaling claim follows from this tiny synthetic workload.
4. Run the healthy scenario to clear the controlled latency incident.
5. For no successful history, establish a successful run rather than treating freshness=0 as healthy.

Owner: demo-data-team. Escalate if repeated slow runs threaten consumer freshness.
