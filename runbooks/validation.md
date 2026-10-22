# Invalid input: VALIDATION_FAILED

Symptoms: the usage aggregate job failed validation because a minutes field is negative.
Impact: no new aggregate is published. If a prior successful output exists, consumers retain it. If no successful output exists, consumers have no published aggregate; check health rather than assuming prior data exists.

1. Confirm the failed run ID and read its VALIDATION_FAILED log entry.
2. Inspect upstream records and quarantine invalid events; preserve the original sample for diagnosis.
3. Correct the producer's nonnegative-minutes contract. Do not silently change invalid data to zero.
4. In this synthetic lab, select the healthy scenario and rerun to demonstrate recovery.
5. Verify successful job status and output freshness before calling the incident resolved.

Owner: demo-data-team. If the bad producer cannot be identified, escalate with the run ID and error evidence.
