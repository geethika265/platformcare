# Stage 6: real Airflow execution

Verified Apache Airflow 3.3.2 using one-off `airflow dags test` runs with a temporary SQLite metadata database and a real local PlatformCare API. This executes the DAG and its task; it is not a mocked Airflow import. No persistent scheduler, Airflow UI or Docker VM is needed for this check.

## Observed sequence

| Scenario | DAG state | Aggregate task | API pipeline record |
| --- | --- | --- | --- |
| Healthy input | success | success | success, source=airflow |
| Invalid minutes field | failed | failed | failed, source=airflow |
| Healthy recovery | success | success | success, source=airflow |

The failure is intentional: the API records a failed aggregation, then the Airflow task raises an error instead of falsely completing successfully. The next independent healthy run demonstrates recovery. It is not an autonomous agent repair or an automatic Airflow retry.

Evidence is saved in `output/evaluation-airflow.json`, including the actual DAG run IDs, task states, CLI exit codes, pipeline run IDs and assertions.

## How the DAG works

`dags/usage_analytics.py` defines a TaskFlow DAG scheduled every two minutes, with `catchup=False`. Its `aggregate` task reads the run's scenario configuration, calls the authenticated PlatformCare `/runs` endpoint, and returns the pipeline run ID on success. It raises an error for a failed result. The demonstration runs it manually; the two-minute scheduler cadence has not been observed continuously.

## Reproduce with a dedicated environment

Keep Airflow dependencies separate from the main application's environment. Use the official constraints file matching the Airflow and Python versions. The verified Python version is 3.12; the commands below assume an available `python3.12` interpreter.

```bash
python3.12 -m venv /private/tmp/platformcare-airflow-check
/private/tmp/platformcare-airflow-check/bin/python -m pip install --no-cache-dir \
  'apache-airflow==3.3.2' fastapi uvicorn prometheus-client python-dotenv \
  --constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.12.txt
/private/tmp/platformcare-airflow-check/bin/python -m scripts.verify_airflow
```

The verifier creates its own metadata and workload databases under `/private/tmp/platformcare-airflow-runtime`, starts the API only on loopback port 18000, initializes Airflow metadata, executes three DAG runs, and stops its processes. Groq and Slack credentials are not forwarded to Airflow processes. Raw test logs remain temporary and should not be published; the small JSON report contains only execution evidence.

After confirming the test has stopped, remove only the two project-owned temporary directories if desired. Keep the source DAG and report. Do not run multiple verifier instances against the same temporary runtime folder.

## Scope

This proves familiarity with a real Airflow DAG, TaskFlow task execution, run configuration, failure propagation, metadata states and API orchestration. It does not prove production scheduler operation, multi-worker scale, high availability or Spark/Flink/Trino experience.

References:

- Real DAG testing and metadata prerequisites: https://airflow.apache.org/docs/apache-airflow/3.3.2/core-concepts/debug.html
- CLI options: https://airflow.apache.org/docs/apache-airflow/3.3.2/cli-and-env-variables-ref.html
- Constrained installation: https://airflow.apache.org/docs/apache-airflow/3.3.2/installation/installing-from-pypi.html
