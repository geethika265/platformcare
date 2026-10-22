"""Opt-in service adapters. No background tasks, dependencies, or automatic exports."""
import json
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request

EVENTS = [{"service": "music", "minutes": 4}, {"service": "tv", "minutes": 12},
          {"service": "music", "minutes": 8}]
EXPECTED = {"music": 12, "tv": 12}
SQL = "SELECT service, SUM(minutes) AS total_minutes FROM (VALUES ('music', 4), ('tv', 12), ('music', 8)) AS events(service, minutes) GROUP BY service"


def origin(url):
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Use a service URL without embedded credentials, query, or fragment")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("Service URLs require HTTPS, except for loopback tests")
    return parsed.scheme, parsed.hostname, parsed.port


def request(url, body=None, headers=None, method=None):
    origin(url)
    payload = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=payload, headers={"Content-Type": "application/json", **(headers or {})}, method=method)
    # Reject redirects: authorization credentials must never be forwarded elsewhere.
    import urllib.request
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    with urllib.request.build_opener(NoRedirect).open(req, timeout=10) as response:
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("Service response exceeded the bounded lab limit")
        return json.loads(raw) if raw else {}


def next_url(base, candidate):
    url = urljoin(base.rstrip('/') + '/', candidate)
    if origin(url) != origin(base):
        raise ValueError("Refusing pagination to another service origin")
    return url


def totals(rows):
    result = {str(row[0]): int(row[1]) for row in rows}
    if result != EXPECTED:
        raise ValueError("Service aggregate differs from the synthetic reference")
    return result


def trino(base, user="platformcare"):
    """Run bounded inline SQL through Trino's statement protocol; no external catalog."""
    headers = {"Content-Type": "text/plain", "X-Trino-User": user}
    # Trino consumes SQL text rather than a JSON string.
    origin(base)
    import urllib.request
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    req = Request(base.rstrip('/') + '/v1/statement', data=SQL.encode(), headers=headers)
    with urllib.request.build_opener(NoRedirect).open(req, timeout=10) as response:
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("Trino response exceeded the bounded lab limit")
        page = json.loads(raw)
    rows = []
    for _ in range(60):
        if page.get('error'):
            raise RuntimeError("Trino query failed; inspect the service's local query log")
        rows.extend(page.get('data', []))
        if not page.get('nextUri'):
            return totals(rows)
        time.sleep(0.1)
        page = request(next_url(base, page['nextUri']), headers=headers)
    # Cancel a query that outlives the bounded polling budget.
    request(next_url(base, page['nextUri']), method='DELETE', headers=headers)
    raise TimeoutError("Trino query exceeded the lab polling budget")


def flink(base):
    """Use a running Flink SQL Gateway, not a simulated streaming engine."""
    session = request(base.rstrip('/') + '/v1/sessions', {"sessionName": "platformcare", "properties": {"execution.runtime-mode": "batch"}})['sessionHandle']
    root = base.rstrip('/') + '/v1/sessions/' + session
    try:
        handle = request(root + '/statements', {"statement": SQL})['operationHandle']
        url = root + '/operations/' + handle + '/result/0'
        rows = []
        for _ in range(60):
            page = request(url)
            if page.get('resultType') == 'NOT_READY':
                time.sleep(0.2)
                continue
            rows.extend(row['fields'] for row in page.get('results', {}).get('data', []))
            if page.get('resultType') == 'EOS' or not page.get('nextResultUri'):
                return totals(rows)
            url = next_url(base, page['nextResultUri'])
        raise TimeoutError("Flink query exceeded the lab polling budget")
    finally:
        request(root, method='DELETE')


def druid(base):
    """Query an existing test datasource populated from fixtures/usage-events.jsonl."""
    sql = 'SELECT service, SUM(minutes) AS total_minutes FROM "platformcare_usage" GROUP BY service'
    rows = request(base.rstrip('/') + '/druid/v2/sql', {"query": sql, "resultFormat": "array", "header": False,
                   "context": {"timeout": 10000, "sqlOuterLimit": 10}})
    return totals(rows)


def splunk(url, token, event):
    """Send an explicitly supplied synthetic event to a Splunk HEC receiver."""
    if not token:
        raise ValueError("Set SPLUNK_HEC_TOKEN locally")
    response = request(url, {"sourcetype": "platformcare:synthetic", "event": event},
                       {"Authorization": "Splunk " + token})
    if response.get('code') != 0:
        raise RuntimeError("Splunk HEC did not accept the event")
    return {"accepted": True, "delivery": "HEC acknowledgment; indexing not verified"}


def pagerduty(routing_key, incident_id, action, url="https://events.pagerduty.com/v2/enqueue"):
    """Explicit trigger/resolve using a stable dedup key; test services only."""
    if not routing_key or action not in {'trigger', 'resolve'}:
        raise ValueError("A routing key and trigger/resolve action are required")
    body = {"routing_key": routing_key, "event_action": action,
            "dedup_key": "platformcare-synthetic-" + incident_id}
    if action == 'trigger':
        body['payload'] = {"summary": "PlatformCare synthetic validation failure", "source": "platformcare-lab",
                           "severity": "warning", "custom_details": {"synthetic": True, "incident_id": incident_id}}
    result = request(url, body)
    if result.get('status') != 'success':
        raise RuntimeError("PagerDuty did not accept the event")
    return {"accepted": True, "action": action, "dedup_key": body['dedup_key']}
