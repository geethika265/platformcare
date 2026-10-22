"""Explicit, opt-in checks of external services; never installs or launches engines."""
import argparse
import json
import os
from platformcare import optional_services as services


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service', choices=['trino', 'flink', 'druid', 'splunk', 'pagerduty'])
    parser.add_argument('--incident-id', default='demo-validation')
    parser.add_argument('--action', choices=['trigger', 'resolve'], default='trigger')
    args = parser.parse_args()
    # Load local dotenv only on explicit execution; dependencies remain optional for unit tests.
    from platformcare import settings  # noqa: F401
    try:
        if args.service in {'trino', 'flink', 'druid'}:
            result = getattr(services, args.service)(os.environ[args.service.upper() + '_URL'])
        elif args.service == 'splunk':
            result = services.splunk(os.environ['SPLUNK_HEC_URL'], os.environ['SPLUNK_HEC_TOKEN'],
                                     {"synthetic": True, "code": "VALIDATION_FAILED", "incident_id": args.incident_id})
        else:
            result = services.pagerduty(os.environ['PAGERDUTY_ROUTING_KEY'], args.incident_id, args.action)
    except Exception as error:
        # Never print HTTP bodies, request headers, keys, or configured URLs.
        print(json.dumps({"service": args.service, "passed": False, "error_type": type(error).__name__,
                          "hint": "Check local settings, permissions, and service logs. No live success is claimed."}))
        raise SystemExit(1) from None
    print(json.dumps({"service": args.service, "passed": True, "result": result,
                      "scope": "synthetic smoke check; not production scale"}, indent=2))


if __name__ == '__main__':
    main()
