"""Real one-off Airflow DAG tests against an isolated PlatformCare API/database."""
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from platformcare.settings import ROOT, token


def main():
    home=Path('/private/tmp/platformcare-airflow-runtime')
    home.mkdir(mode=0o700,parents=True,exist_ok=True)
    env={k:os.environ[k] for k in ('PATH','HOME','TMPDIR','LANG','LC_ALL') if k in os.environ}
    env.update({
        'AIRFLOW_HOME':str(home),
        'AIRFLOW__CORE__DAGS_FOLDER':str(ROOT/'dags'),
        'AIRFLOW__CORE__LOAD_EXAMPLES':'false',
        'AIRFLOW__CORE__DEFAULT_TIMEZONE':'utc',
        'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN':'sqlite:///'+str(home/'airflow.db'),
        'AIRFLOW__LOGGING__LOGGING_LEVEL':'WARNING',
        'AIRFLOW__METRICS__OTEL_ON':'false',
        'AIRFLOW__METRICS__STATSD_ON':'false',
        'PLATFORM_API':'http://127.0.0.1:18000',
        'PLATFORM_TOKEN':token(),
        'PLATFORM_DB':str(home/'platform.db'),
        'MODEL_MODE':'offline',
        'NO_PROXY':'127.0.0.1,localhost',
    })
    airflow=str(Path(sys.executable).parent/'airflow')
    report={'kind':'real Airflow CLI DAG execution; no persistent scheduler/UI',
            'version':'3.3.2','cases':[],'passed':False}
    api=None
    def stop(process):
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait()
    def execute(name,args):
        with (home/(name+'.log')).open('w') as log:
            process=subprocess.Popen([airflow,*args],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                return process.wait(timeout=150)
            finally:
                stop(process)
    try:
        code=execute('migrate',['db','migrate'])
        if code: raise RuntimeError('metadata_migration_failed')
        print('Airflow metadata database initialized',flush=True)
        with (home/'api.log').open('w') as log:
            api=subprocess.Popen([sys.executable,'-m','uvicorn','platformcare.api:app','--host','127.0.0.1','--port','18000','--log-level','warning','--no-access-log'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            for _ in range(30):
                if api.poll() is not None: raise RuntimeError('api_start_failed')
                try:
                    with urlopen(env['PLATFORM_API']+'/health',timeout=2) as response:
                        if response.status==200: break
                except Exception: time.sleep(1)
            else: raise RuntimeError('api_ready_timeout')
            origin=datetime.now(timezone.utc)-timedelta(minutes=3)
            for i,scenario in enumerate(['healthy','invalid_input','healthy']):
                logical=(origin+timedelta(minutes=i)).isoformat()
                code=execute(f'dag-{i}-{scenario}',['dags','test','usage_analytics',logical,'--dagfile-path',str(ROOT/'dags/usage_analytics.py'),'--conf',json.dumps({'scenario':scenario})])
                with sqlite3.connect(home/'airflow.db') as conn:
                    conn.row_factory=sqlite3.Row
                    dags=[dict(r) for r in conn.execute("SELECT run_id,state FROM dag_run WHERE dag_id='usage_analytics' ORDER BY id DESC LIMIT 1")]
                    tasks=[dict(r) for r in conn.execute("SELECT task_id,state FROM task_instance WHERE dag_id='usage_analytics' AND run_id=?",(dags[0]['run_id'],))] if dags else []
                with sqlite3.connect(home/'platform.db') as conn:
                    conn.row_factory=sqlite3.Row
                    jobs=[dict(r) for r in conn.execute('SELECT id,status,scenario,source FROM runs ORDER BY started DESC LIMIT 1')]
                expected='failed' if scenario=='invalid_input' else 'success'
                passed=bool(dags and tasks and jobs and dags[0]['state']==expected and all(t['state']==expected for t in tasks) and jobs[0]['status']==expected and jobs[0]['scenario']==scenario and jobs[0]['source']=='airflow')
                item={'scenario':scenario,'expected':expected,'cli_exit_code':code,'dag_run':dags[0] if dags else None,'tasks':tasks,'pipeline_run':jobs[0] if jobs else None,'passed':passed}
                report['cases'].append(item)
                print(json.dumps(item),flush=True)
                if not passed: break
            report['passed']=len(report['cases'])==3 and all(item['passed'] for item in report['cases'])
    except Exception as error:
        report['error_type']=type(error).__name__
        report['error_stage']=str(error)[:100] if isinstance(error,RuntimeError) else 'inspect temporary logs locally'
    finally:
        if api: stop(api)
        output=ROOT/'output/evaluation-airflow.json'
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report,indent=2))
        print('Report:',output,flush=True)
        print('All test-owned API/DAG processes stopped',flush=True)
    if not report['passed']: raise SystemExit(1)


if __name__=='__main__':
    main()
