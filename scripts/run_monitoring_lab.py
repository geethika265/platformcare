"""Start downloaded native tools for a bounded local verification session."""
import argparse
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from platformcare.settings import ROOT, token


def main(folder):
    folder=Path(folder).resolve()
    runtime=folder/"runtime"
    if not (runtime/"prometheus.json").exists():
        raise SystemExit("Run scripts.prepare_monitoring first")
    processes=[]
    files=[]
    stop=False
    def halt(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,halt)
    signal.signal(signal.SIGINT,halt)
    base={k:os.environ[k] for k in ("PATH","HOME","TMPDIR","LANG","LC_ALL") if k in os.environ}
    base.update(GOMAXPROCS="2",GOMEMLIMIT="128MiB")
    def start(name,command,extra=None):
        log=(runtime/(name+".log")).open("w")
        files.append(log)
        env=base| (extra or {})
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        processes.append((name,process))
    def ready(url):
        for _ in range(45):
            if stop: raise RuntimeError("Stop requested")
            failed=[name for name,p in processes if p.poll() is not None]
            if failed: raise RuntimeError("Service exited: "+", ".join(failed))
            try:
                with urlopen(url,timeout=2) as response:
                    if response.status==200: return
            except Exception:
                time.sleep(1)
        raise RuntimeError("Service startup deadline exceeded")
    try:
        start("api",[sys.executable,"-m","uvicorn","platformcare.api:app","--host","127.0.0.1","--port","18000","--log-level","warning","--no-access-log"],
              {"PLATFORM_DB":str(runtime/"platform.db"),"PLATFORM_TOKEN":token(),"MODEL_MODE":"offline","PROMETHEUS_URL":"http://127.0.0.1:19090"})
        ready("http://127.0.0.1:18000/health")
        request=Request("http://127.0.0.1:18000/runs",data=b'{"scenario":"healthy","source":"evaluation"}',headers={"Content-Type":"application/json","X-Platform-Token":token()})
        with urlopen(request,timeout=5) as response:
            response.read()
        start("alertmanager",[str(next(folder.glob("alertmanager-*/alertmanager"))),"--config.file="+str(runtime/"alertmanager.json"),"--storage.path="+str(runtime/"alertmanager-data"),"--web.listen-address=127.0.0.1:19093","--cluster.listen-address=","--log.level=warn"])
        ready("http://127.0.0.1:19093/-/ready")
        start("prometheus",[str(next(folder.glob("prometheus-*/prometheus"))),"--config.file="+str(runtime/"prometheus.json"),"--storage.tsdb.path="+str(runtime/"prometheus-data"),"--storage.tsdb.retention.time=1h","--storage.tsdb.retention.size=20MB","--web.listen-address=127.0.0.1:19090","--log.level=warn"])
        ready("http://127.0.0.1:19090/-/ready")
        grafana=next(folder.glob("grafana-*/bin/grafana"))
        start("grafana",[str(grafana),"server","--homepath="+str(grafana.parent.parent),"--config="+str(runtime/"grafana.ini")],
              {"GF_SECURITY_ADMIN_PASSWORD":secrets.token_urlsafe(24)})
        ready("http://127.0.0.1:13001/api/health")
        (runtime/"processes.json").write_text(json.dumps({name:p.pid for name,p in processes}))
        print("Ready: Grafana http://127.0.0.1:13001/d/platformcare | Prometheus http://127.0.0.1:19090",flush=True)
        print("Docker is off. Session auto-stops after 10 minutes or below 1.5 GiB free disk.",flush=True)
        deadline=time.monotonic()+600
        while not stop and time.monotonic()<deadline:
            if shutil.disk_usage(folder).free<1.5*1024**3:
                print("Stopping: free disk floor reached",flush=True)
                break
            if any(p.poll() is not None for _,p in processes):
                print("Stopping: a service exited",flush=True)
                break
            time.sleep(1)
    finally:
        for _,process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
        for _,process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait()
        for file in files:
            file.close()
        print("All temporary monitoring services stopped",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("folder")
    main(parser.parse_args().folder)
