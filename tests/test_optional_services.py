"""Adapter contract tests use fake transports; they are not vendor integration evidence."""
import json
import unittest
from unittest.mock import patch
from platformcare import optional_services as services


class AdapterTests(unittest.TestCase):
    def test_rejects_remote_plaintext_and_embedded_credentials(self):
        for url in ['http://example.com', 'https://user:password@example.com', 'https://example.com?token=secret']:
            with self.assertRaises(ValueError):
                services.origin(url)

    def test_pagination_cannot_forward_to_other_origin(self):
        with self.assertRaises(ValueError):
            services.next_url('https://example.com', 'https://elsewhere.test/result')
        self.assertEqual(services.next_url('https://example.com', '/result/1'), 'https://example.com/result/1')

    def test_splunk_checks_acknowledgment_and_auth_header(self):
        with patch.object(services, 'request', return_value={'code': 0}) as send:
            self.assertTrue(services.splunk('https://splunk.test/hec', 'test-key', {'synthetic': True})['accepted'])
            self.assertEqual(send.call_args.args[2]['Authorization'], 'Splunk test-key')
        with patch.object(services, 'request', return_value={'code': 4}):
            with self.assertRaises(RuntimeError):
                services.splunk('https://splunk.test/hec', 'test-key', {})

    def test_pagerduty_lifecycle_preserves_dedup_key(self):
        with patch.object(services, 'request', return_value={'status': 'success'}) as send:
            services.pagerduty('test-key', 'incident-1', 'trigger')
            trigger = send.call_args.args[1]
            services.pagerduty('test-key', 'incident-1', 'resolve')
            resolve = send.call_args.args[1]
        self.assertEqual(trigger['dedup_key'], resolve['dedup_key'])
        self.assertEqual(trigger['event_action'], 'trigger')
        self.assertNotIn('payload', resolve)
        self.assertTrue(trigger['payload']['custom_details']['synthetic'])

    def test_druid_queries_fixture_datasource_and_validates_totals(self):
        with patch.object(services, 'request', return_value=[['music', 12], ['tv', 12]]) as send:
            self.assertEqual(services.druid('https://druid.test'), services.EXPECTED)
            self.assertIn('FROM "platformcare_usage"', send.call_args.args[1]['query'])
            self.assertEqual(send.call_args.args[1]['context']['timeout'], 10000)
        with patch.object(services, 'request', return_value=[['music', 1]]):
            with self.assertRaises(ValueError):
                services.druid('https://druid.test')

    def test_flink_reads_results_and_closes_session(self):
        responses = [{'sessionHandle': 'session'}, {'operationHandle': 'operation'},
                     {'resultType': 'PAYLOAD', 'results': {'data': [{'fields': ['music', 12]}, {'fields': ['tv', 12]}]}}, {}]
        with patch.object(services, 'request', side_effect=responses) as send:
            self.assertEqual(services.flink('https://flink.test'), services.EXPECTED)
            self.assertEqual(send.call_args.kwargs['method'], 'DELETE')

    def test_flink_closes_session_after_query_failure(self):
        with patch.object(services, 'request', side_effect=[{'sessionHandle': 's'}, RuntimeError('query failed'), {}]) as send:
            with self.assertRaises(RuntimeError):
                services.flink('https://flink.test')
            self.assertEqual(send.call_args.kwargs['method'], 'DELETE')

    def test_trino_sql_is_text_and_pagination_collects_results(self):
        import urllib.request
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return json.dumps({'nextUri': 'https://trino.test/query/1'}).encode()
        class Opener:
            def open(self, req, timeout):
                self.req = req
                return Response()
        opener = Opener()
        with patch.object(urllib.request, 'build_opener', return_value=opener), patch.object(services, 'request', return_value={'data': [['music', 12], ['tv', 12]]}), patch.object(services.time, 'sleep'):
            self.assertEqual(services.trino('https://trino.test'), services.EXPECTED)
        self.assertEqual(opener.req.data.decode(), services.SQL)
        self.assertEqual(opener.req.get_header('Content-type'), 'text/plain')


if __name__ == '__main__':
    unittest.main()
