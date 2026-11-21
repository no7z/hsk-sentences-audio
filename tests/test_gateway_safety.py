"""Financial and checkpoint guards, using local fakes only; never call an API."""
from decimal import Decimal
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gateway_advanced import AUTHOR, REVIEWER, Gateway
from import_advanced_batch import validate_batch


class GatewaySafetyTest(unittest.TestCase):
    def client(self, directory, limit='1', balance='1'):
        obj = Gateway.__new__(Gateway)
        obj.key = 'local-test-placeholder'
        obj.directory = Path(directory)
        obj.ledger = obj.directory / 'ledger.jsonl'
        obj.lock = threading.Lock()
        obj.limit, obj.reserved, obj.spent = Decimal(limit), Decimal(0), Decimal(0)
        obj.catalog = {AUTHOR: {'pricing': {'input': '0.000001', 'output': '0.000002'}}}
        obj.get = lambda path: {'balance': balance}
        return obj

    def test_cap_stops_before_paid_request(self):
        with tempfile.TemporaryDirectory() as folder:
            g = self.client(folder, limit='0.00001')
            with patch('urllib.request.urlopen') as post:
                with self.assertRaisesRegex(RuntimeError, 'spending cap'):
                    g.complete('test', AUTHOR, 'system', 'prompt', 100)
                post.assert_not_called()
            self.assertFalse(g.ledger.exists())

    def test_balance_floor_stops_before_paid_request(self):
        with tempfile.TemporaryDirectory() as folder:
            g = self.client(folder, balance='0.15')
            with patch('urllib.request.urlopen') as post:
                with self.assertRaises(RuntimeError):
                    g.complete('test', AUTHOR, 'system', 'prompt', 100)
                post.assert_not_called()

    def test_unknown_timeout_preserves_reservation_and_has_no_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            g = self.client(folder)
            with patch('urllib.request.urlopen', side_effect=TimeoutError) as post:
                with self.assertRaises(TimeoutError):
                    g.complete('test', AUTHOR, 'system', 'prompt', 100)
                self.assertEqual(post.call_count, 1)
            events = [json.loads(s) for s in g.ledger.read_text().splitlines()]
            self.assertEqual([e['event'] for e in events], ['start', 'error'])
            self.assertGreater(g.reserved, 0)
            self.assertNotIn(g.key, g.ledger.read_text())

    def test_actual_cost_replaces_reservation_and_incomplete_output_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            g = self.client(folder)
            response = {'id': 'local-test', 'model': AUTHOR,
                        'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'cost': '0.00005'},
                        'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}
            with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())):
                with self.assertRaisesRegex(ValueError, 'Incomplete'):
                    g.complete('test', AUTHOR, 'system', 'prompt', 100)
            self.assertEqual(g.reserved, 0)
            self.assertEqual(g.spent, Decimal('0.00005'))

    def test_restart_conservatively_counts_unresolved_requests(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'ledger.jsonl').write_text(json.dumps({'event': 'start', 'request_id': 'interrupted',
                                                          'reserved_usd': '0.12'}) + '\n', encoding='utf-8')
            models = {'data': [{'id': m, 'pricing': {'input': '0.000001', 'output': '0.000002'}}
                               for m in (AUTHOR, REVIEWER)]}
            with patch('gateway_advanced.read_key', return_value='local-test'), patch.object(Gateway, 'get', return_value=models):
                g = Gateway(path, Decimal('1'))
            self.assertEqual(g.spent, Decimal('0.12'))

    def test_numbered_pinyin_rejected_before_import(self):
        sentence = {'chinese': '他在会上清楚表述了自己的观点。', 'en': 'He clearly expressed his views at the meeting.',
                    'topic': 'school_work', 'targets': ['表述'], 'token_pinyin': {'表述': 'biao3 shu4'},
                    'gloss': {'表述': 'to articulate'}, 'grammar': []}
        errors = validate_batch({'batch': 'test', 'sentences': [sentence]},
                                {'batch': 'test', 'targets': [{'word': '表述'}]}, [])
        self.assertTrue(any('tone marks' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
