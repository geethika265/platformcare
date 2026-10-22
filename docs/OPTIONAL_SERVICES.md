# Optional services: code exists, live verification pending

These adapters extend the lab without installing an engine, starting Docker, exporting data automatically, or changing the main application. They use three synthetic events whose expected totals are `music=12` and `tv=12`. They are separate smoke checks, not replacements for the Python pipeline or distributed-scale demonstrations.

**Current evidence:** eight local fake-transport contract tests pass. Spark, Flink, Trino, Druid, Splunk, and PagerDuty have not run against real services. Do not list them as verified hands-on integrations on the basis of these files alone.

## Engine checks

Use an existing service or remote lab. Keep its credentials out of URLs and Git. The present adapters support unauthenticated endpoints or an authenticated proxy with no credentials in the URL. Trino defaults to user `platformcare`. Production authentication/TLS setups may require extending the adapters. HTTPS is required for remote URLs; HTTP is allowed only on loopback.

| Engine | Check | Requirements |
| --- | --- | --- |
| Spark | `spark-submit --master 'local[1]' scripts/spark_aggregate.py` | Existing compatible Spark/Java runtime; not installed by this project |
| Flink | `python -m scripts.optional_services flink` | Running Flink SQL Gateway, `FLINK_URL` set locally |
| Trino | `python -m scripts.optional_services trino` | Running coordinator, `TRINO_URL` set locally |
| Druid | `python -m scripts.optional_services druid` | Running Druid SQL endpoint, `DRUID_URL`; prepared test datasource described below |

Spark groups a small DataFrame. Flink and Trino execute inline SQL without a configured external catalog. Druid queries a prepared test datasource through its SQL endpoint. The REST adapters validate the returned aggregates, bound polling/response sizes, and report failure rather than return reference values as if the engine had computed them. Tests use simulated responses and cannot prove the SQL is accepted by a particular server version.

### Druid fixture prerequisite

In a dedicated test Druid service, ingest `fixtures/usage-events.jsonl` using the console's local-file ingestion wizard. Use datasource name `platformcare_usage`, `timestamp` as the timestamp column, `service` as a string dimension and `minutes` as a long numeric column. Disable rollup for this sample. Wait for all three rows to become queryable before running the check. Use an empty dedicated datasource and do not append the fixture repeatedly: duplicated records should fail the aggregate assertion. No ingestion or server is started by this project.

## Splunk HEC

Set `SPLUNK_HEC_URL` to your test receiver's full `/services/collector/event` endpoint and save `SPLUNK_HEC_TOKEN` locally in `.env`. With app dependencies installed, explicitly run:

```bash
python -m scripts.optional_services splunk
```

This sends one labeled synthetic validation event. A successful HEC response proves receiver acceptance, not searchable indexing. Verify the event in Splunk separately. This is not yet an automatic log exporter.

## PagerDuty Events API v2

Use a dedicated test service without real on-call escalation. Save its Events API integration key as `PAGERDUTY_ROUTING_KEY` locally. Running trigger explicitly authorizes sending a synthetic event to that service:

```bash
python -m scripts.optional_services pagerduty --incident-id lab-validation --action trigger
python -m scripts.optional_services pagerduty --incident-id lab-validation --action resolve
```

Both calls use the same stable synthetic dedup key. Receiver acceptance does not prove that a human received or acknowledged a notification. This adapter is manual; it is not connected to the incident poller.

## Notebook

Open `notebooks/customer_support_walkthrough.ipynb` with an existing Jupyter environment. No additional Python libraries are needed by its cells. It reads SQLite in read-only mode, joins failed runs to error logs, and explains customer/support metrics. Create local demo runs using the README first. The notebook contains no saved data or credentials. Its code cells have been smoke-checked as Python; a Jupyter server/kernel launch was not tested.

## Multi-cloud scope

AWS appears in the owner's earlier cloud-log project. This lab runs locally; that does not demonstrate operating across two clouds. A meaningful future exercise would deploy the same API/metrics contract into two approved cloud accounts, verify authenticated connectivity and failure isolation, and compare the customer view across environments. No cloud resources, accounts, or deployments are created here. Infrastructure templates alone would not establish multi-cloud runtime experience.

## References

- Spark DataFrame API: https://spark.apache.org/docs/latest/api/python/getting_started/quickstart_df.html
- Flink SQL Gateway REST API: https://nightlies.apache.org/flink/flink-docs-release-2.3/docs/sql/interfaces/sql-gateway/rest/
- Trino statement protocol: https://trino.io/docs/current/develop/client-protocol.html
- Druid SQL API: https://druid.apache.org/docs/latest/api-reference/sql-api/
- Splunk HEC events: https://help.splunk.com/en/data-management/collect-http-event-data/use-hec-in-splunk-enterprise/set-up-and-use-http-event-collector-in-splunk-web
- PagerDuty Events API: https://developer.pagerduty.com/docs/events-api-v2/overview/
