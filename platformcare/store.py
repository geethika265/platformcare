"""SQLite transactions preserve alert identity and support timestamps across restarts."""
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from uuid import uuid4
from .settings import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, started REAL, finished REAL,
 status TEXT, scenario TEXT, source TEXT, records INTEGER, output TEXT);
CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, run_id TEXT, ts REAL,
 level TEXT, code TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY, fingerprint TEXT,
 title TEXT, opened REAL, resolved REAL, origin TEXT, slack_ts TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS active_fingerprint ON incidents(fingerprint)
 WHERE resolved IS NULL;
CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, event_key TEXT UNIQUE,
 question TEXT, opened REAL, answered REAL, resolved REAL, helpful INTEGER,
 escalated INTEGER DEFAULT 0, result TEXT);
CREATE TABLE IF NOT EXISTS deliveries(key TEXT PRIMARY KEY, created REAL);
"""

@contextmanager
def connection():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()

def rows(query, args=()):
    with connection() as conn:
        return [dict(r) for r in conn.execute(query, args)]

def execute(query, args=()):
    with connection() as conn:
        conn.execute(query, args)

def redact(text):
    text = re.sub(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+", r"\1=[REDACTED]", str(text))
    return re.sub(r"(?:xox[baprs]-|sk-)[A-Za-z0-9_-]+", "[REDACTED]", text)

def log(run_id, level, code, message):
    execute("INSERT INTO logs(run_id,ts,level,code,message) VALUES(?,?,?,?,?)",
            (run_id, time.time(), level, code, redact(message)[:2000]))

def incident(fingerprint, title, origin):
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT * FROM incidents WHERE fingerprint=? AND resolved IS NULL", (fingerprint,)).fetchone()
        if existing:
            return dict(existing), False
        item = dict(id=uuid4().hex[:12], fingerprint=fingerprint, title=title,
                    opened=time.time(), resolved=None, origin=origin, slack_ts=None)
        conn.execute("INSERT INTO incidents VALUES(:id,:fingerprint,:title,:opened,:resolved,:origin,:slack_ts)", item)
        return item, True

def resolve(fingerprint):
    execute("UPDATE incidents SET resolved=? WHERE fingerprint=? AND resolved IS NULL", (time.time(), fingerprint))

def claim_delivery(key):
    with connection() as conn:
        result = conn.execute("INSERT OR IGNORE INTO deliveries VALUES(?,?)", (key, time.time()))
        return result.rowcount == 1

def new_request(question, event_key=None):
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if event_key:
            existing = conn.execute("SELECT id FROM requests WHERE event_key=?", (event_key,)).fetchone()
            if existing:
                return existing[0], False
        key = uuid4().hex[:12]
        conn.execute("INSERT INTO requests(id,event_key,question,opened) VALUES(?,?,?,?)",
                     (key, event_key, redact(question)[:2000], time.time()))
        return key, True

def complete_request(key, result):
    execute("UPDATE requests SET answered=?, result=?, escalated=? WHERE id=?",
            (time.time(), json.dumps(result), int(result.get("escalate", False)), key))

def support_metrics():
    requests = rows("SELECT * FROM requests")
    incidents = rows("SELECT * FROM incidents")
    latencies = [r["answered"]-r["opened"] for r in requests if r["answered"]]
    resolutions = [r["resolved"]-r["opened"] for r in incidents if r["resolved"]]
    feedback = [r["helpful"] for r in requests if r["helpful"] is not None]
    return dict(requests=len(requests), unanswered=sum(r["answered"] is None for r in requests),
                escalations=sum(r["escalated"] for r in requests),
                mean_first_response_seconds=sum(latencies)/len(latencies) if latencies else None,
                mean_resolution_seconds=sum(resolutions)/len(resolutions) if resolutions else None,
                helpful_rate=sum(feedback)/len(feedback) if feedback else None,
                feedback_count=len(feedback), incidents=len(incidents),
                open_incidents=sum(r["resolved"] is None for r in incidents))
