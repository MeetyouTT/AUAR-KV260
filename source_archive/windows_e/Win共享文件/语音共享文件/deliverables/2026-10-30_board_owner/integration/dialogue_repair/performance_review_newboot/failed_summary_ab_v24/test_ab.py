"""Synthetic RAM-only A/B contract checks, with the actual summary classes."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import run_ab


common, arguments, source, remote, contract = run_ab.inputs()
base = contract.base
definition = importlib.util.spec_from_file_location('_ab_public_r4_sources',
    run_ab.REPAIR / 'memory_negation_v23_candidate_r4/run_public_tests.py')
public = importlib.util.module_from_spec(definition)
definition.loader.exec_module(public)
candidate = contract.reviewed_messages(
    (run_ab.REPAIR / 'memory_negation_v23_candidate_r4/after/board/runtime/board_memory_policy.py').read_bytes(),
    arguments['candidate_source'].encode('utf8'))


def prepared():
    rows = [dict(event_id='public-ab-event', revision=1, source='user_said', include_in_summary=True,
                 text='这不是蓝色文件夹，而是绿色文件夹。', metadata={}, recorded_utc=1.)]
    return dict(schema_version=1, scope=dict(kind='conversation', id='public-ab-scope'), topic='public',
                start_utc=1., end_utc=2., sources=rows,
                required_claims=public.STORE.BoardMemoryStore._required_claims(rows))


class FakePair:
    def __init__(self, answers):
        self.answers = iter(answers)
        self.calls = []

    def request(self, kind, payload, *, deadline, cancelled):
        if not 0 < deadline - time.monotonic() <= 30 or payload['budget_ms'] > 30000:
            raise AssertionError('public deadline bound')
        self.calls.append(copy.deepcopy(payload))
        return public.make_response(public.Owner.from_dict(payload), result={'text': json.dumps(
            dict(summary=next(self.answers), keywords=['公开']), ensure_ascii=False)})

    def cancel(self, owner):
        pass


class PairTests(unittest.TestCase):
    def run_pair(self, transport, *, data=None, guard=lambda: None, cancellation=lambda: lambda: False):
        result = contract.empty_result()
        old = public.POLICY.BoardSummaryClient._messages
        with patch.object(public.STORE.BoardMemoryStore, '__init__', side_effect=AssertionError('Store instantiated')), \
                patch('sqlite3.connect', side_effect=AssertionError('Database opened')):
            try:
                contract.pair(data or prepared(), public.STORE, public.POLICY, transport, candidate,
                              guard, cancellation, result)
            finally:
                self.assertIs(public.POLICY.BoardSummaryClient._messages, old)
        contract.validate_output(result)
        return result

    def test_same_complete_snapshot_two_requests_and_exact_method_restoration(self):
        transport = FakePair(['记录颜色为绿色。', '这不是蓝色文件夹，而是绿色文件夹。'])
        value = self.run_pair(transport)
        self.assertEqual(2, len(transport.calls))
        self.assertEqual(2, value['calls'])
        self.assertEqual(1, value['same_source_snapshot'])
        self.assertEqual(1, value['original_messages_restored'])
        self.assertEqual(0, value['before']['accepted'])
        self.assertEqual(1, value['candidate']['accepted'])
        self.assertEqual(value['before']['sources'], value['candidate']['sources'])
        self.assertEqual(transport.calls[0]['messages'][1], transport.calls[1]['messages'][1])
        self.assertNotEqual(transport.calls[0]['messages'][0], transport.calls[1]['messages'][0])
        self.assertNotEqual(transport.calls[0]['board_boot_id'], transport.calls[1]['board_boot_id'])

    def test_reduction_is_limited_to_one_actual_call_each_arm(self):
        transport = FakePair(['这不是蓝色文件夹。' * 40] * 2)
        value = self.run_pair(transport)
        self.assertEqual(2, len(transport.calls))
        self.assertEqual(1, value['before']['calls'])
        self.assertEqual(1, value['candidate']['calls'])
        self.assertEqual(0, value['before']['accepted'])
        self.assertEqual(0, value['candidate']['accepted'])

    def test_pre_cancel_and_guard_failure_restore_without_model_call(self):
        transport = FakePair([])
        with self.assertRaises(base.Refused):
            self.run_pair(transport, cancellation=lambda: lambda: True)
        self.assertEqual([], transport.calls)
        def refused():
            raise base.Refused()
        with self.assertRaises(base.Refused):
            self.run_pair(transport, guard=refused)
        self.assertEqual([], transport.calls)

    def test_changed_snapshot_prevents_second_request(self):
        data = prepared()
        transport = FakePair(['这不是蓝色文件夹，而是绿色文件夹。'])
        request = transport.request
        def mutate(*args, **kwargs):
            value = request(*args, **kwargs)
            data['topic'] = 'public mutation'
            return value
        transport.request = mutate
        with self.assertRaises(base.Refused):
            self.run_pair(transport, data=data)
        self.assertEqual(1, len(transport.calls))

    def test_guard_failure_after_request_preserves_call_and_stops_second_arm(self):
        transport = FakePair(['这不是蓝色文件夹，而是绿色文件夹。'])
        value = contract.empty_result()
        old = public.POLICY.BoardSummaryClient._messages
        def guard():
            if transport.calls:
                raise base.Refused()
        with self.assertRaises(base.Refused):
            contract.pair(prepared(), public.STORE, public.POLICY, transport, candidate,
                          guard, lambda: lambda: False, value)
        contract.validate_output(value)
        self.assertEqual(1, len(transport.calls))
        self.assertEqual(1, value['calls'])
        self.assertEqual(1, value['before']['calls'])
        self.assertIsNone(value['candidate'])
        self.assertEqual(1, value['original_messages_restored'])
        self.assertIs(public.POLICY.BoardSummaryClient._messages, old)

    def test_whole_module_ast_excludes_every_other_method(self):
        original = (run_ab.REPAIR / 'memory_negation_v23_candidate_r4/after/board/runtime/board_memory_policy.py').read_bytes()
        changed = arguments['candidate_source'].replace('total_budget_ms=900000', 'total_budget_ms=800000', 1).encode()
        with patch.object(contract, 'CANDIDATE_POLICY', base.digest(changed)), self.assertRaises(base.Refused):
            contract.reviewed_messages(original, changed)

    def test_contract_rejects_content_ids_and_unknown_enum(self):
        value = contract.empty_result()
        value['before'] = contract.project_arm(base.empty_result())
        for alteration in ('raw_text', 'source_id', 'response_hash'):
            bad = copy.deepcopy(value)
            bad['before'][alteration] = 'PRIVATE_SENTINEL'
            with self.assertRaises(base.Refused):
                contract.validate_output(bad)
        value['error_class'] = 'PRIVATE_SENTINEL'
        with self.assertRaises(base.Refused):
            contract.validate_output(value)

    def test_parent_has_only_ninety_second_owned_child_timeout(self):
        self.assertEqual(1, remote.count('timeout=90'))
        self.assertNotIn('timeout=45', remote)
        self.assertEqual(2, remote.count('process.kill()'))
        self.assertNotIn('os.kill', remote)
        self.assertEqual(380, len(arguments['mapping']['component_pins']))

    def test_fd_boundary_only_emits_fixed_pair_projection(self):
        code = "import io,json,sys;namespace={'__name__':'_public_test'};" \
               "exec(json.loads(sys.stdin.buffer.read())['source'],namespace);" \
               "namespace['execute']=lambda args:(print('PRIVATE_SENTINEL'),namespace['empty_result']())[1];" \
               "sys.stdin=io.TextIOWrapper(io.BytesIO(b'{}'));namespace['child_main']()"
        value = subprocess.run([sys.executable, '-B', '-c', code],
            input=json.dumps(dict(source=source)).encode('utf8'), capture_output=True, timeout=8)
        self.assertEqual(0, value.returncode)
        self.assertNotIn(b'PRIVATE_SENTINEL', value.stdout + value.stderr)
        contract.validate_output(json.loads(value.stdout))


if __name__ == '__main__':
    unittest.main(verbosity=2)
