"""Public fake-transport checks. No devices, databases or models are called."""
import contextlib
import ast
import functools
import tempfile
import copy
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import prepare_runner as prepare
import worker


build = functools.partial(prepare.build, additions_path=prepare.REPAIR / "memory_negation_v24_candidate/PUBLIC_MODEL_ADDITIONS.json", additions_sha="327fe5ee0410dd94ad19ee8784586610c024eced22ea113bc167541224b395c5")


@contextlib.contextmanager
def public_policy():
    with worker.isolated_project_imports():
        sys.path.insert(0, str(prepare.REPAIR / 'feature_trigger_collaboration/board_integration_v17/local_runtime_v17'))
        root = prepare.REPAIR / 'memory_negation_v23_candidate_r4/after'
        memory = worker.load_overlay('common.board_memory', {'source': (root / 'common/board_memory.py').read_text(encoding='utf-8')})
        dialogue = prepare.REPAIR / 'feature_trigger_collaboration/candidate_h01/after/board/runtime/board_dialogue.py'
        worker.load_overlay('board.runtime.board_dialogue', {'source': dialogue.read_text(encoding='utf-8')})
        policy = worker.load_overlay('board.runtime.board_memory_policy', {'source': (root / 'board/runtime/board_memory_policy.py').read_text(encoding='utf-8')})
        from common.model_inference_wire import Owner, make_response
        with patch.object(memory.BoardMemoryStore, '__init__', side_effect=AssertionError('Store instantiated')), \
                patch('sqlite3.connect', side_effect=AssertionError('DB opened')):
            yield memory, policy, Owner, make_response


class PublicWorkerTests(unittest.TestCase):
    def test_builder_extracts_only_public_sources_and_rubric(self):
        value = build('before', 'all')
        self.assertEqual(15, len(value['cases']))
        self.assertIs(value['old_prompt_messages_copied'], False)
        self.assertEqual({}, value['candidate_sources'])
        self.assertEqual(301, value['final_summary_max_utf8_bytes'])
        self.assertTrue(all(set(row) == {'case', 'sources', 'semantic_review_rubric'} for row in value['cases']))

    def test_before_dry_never_calls_execution(self):
        path = prepare.HERE / 'BEFORE_PILOT_PAYLOAD.json'
        with patch('sys.argv', ['worker.py', '--payload', str(path), '--payload-sha256', worker.digest(path.read_bytes())]), \
                patch.object(worker, 'execute', side_effect=AssertionError('Model/device execution attempted')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            worker.main()
        self.assertIn('NO_DEVICE_OR_MODEL_ACCESS', output.getvalue())

    def test_production_default_client_accepts_public_case_with_full_refs(self):
        with public_policy() as (memory, policy, Owner, make_response):
            literal = '用户询问你会不会唱歌？'
            transport = types.SimpleNamespace(request=lambda kind, payload, **kwargs:
                make_response(Owner.from_dict(payload), result={'text': json.dumps({'summary': literal, 'keywords': ['唱歌']}, ensure_ascii=False)}),
                cancel=lambda owner: None)
            client = worker.RecordingClient(transport, lambda: None)
            summary = policy.BoardSummaryClient(client, board_boot_id='public-memory-v24-test', final_summary_max_utf8_bytes=301)
            case = build('before', 'question_will')['cases'][0]
            prepared = worker.prepared_case(case, memory)
            result = summary(prepared, lambda: False)
            task = {'scope_kind': prepared['scope']['kind'], 'scope_id': prepared['scope']['id'],
                    'topic': prepared['topic'], 'start_utc': prepared['start_utc'], 'end_utc': prepared['end_utc']}
            memory.BoardMemoryStore._candidate(result, task, prepared['sources'])
            self.assertEqual(1, len(client.calls))
            self.assertEqual(1, summary.metrics['model_calls'])
            self.assertIs(summary.metrics['complete_source_coverage'], True)
            self.assertEqual(result['source_refs'][0]['event_id'], prepared['sources'][0]['event_id'])
            self.assertEqual({'num_predict': 384}, client.calls[0]['request']['options'])

    def test_rejected_narrative_still_preserves_this_public_model_text(self):
        with public_policy() as (memory, policy, Owner, make_response):
            text = json.dumps({'summary': '用户确认可以唱歌。', 'keywords': ['唱歌']}, ensure_ascii=False)
            transport = types.SimpleNamespace(request=lambda kind, payload, **kwargs:
                make_response(Owner.from_dict(payload), result={'text': text}), cancel=lambda owner: None)
            client = worker.RecordingClient(transport, lambda: None)
            summary = policy.BoardSummaryClient(client, board_boot_id='public-memory-v24-test', final_summary_max_utf8_bytes=301)
            case = build('before', 'question_will')['cases'][0]
            with self.assertRaises(memory.CandidateRejected):
                summary(worker.prepared_case(case, memory), lambda: False)
            self.assertEqual(text, client.calls[0]['response']['result']['text'])
            self.assertEqual(('negation_missing',), summary.failure_metadata()['rejection_reasons'])

    def test_pre_cancel_keeps_original_summary_cancellation(self):
        with public_policy() as (memory, policy, Owner, make_response):
            client = worker.RecordingClient(types.SimpleNamespace(request=lambda *a, **k: self.fail('Unexpected call')), lambda: None)
            summary = policy.BoardSummaryClient(client, board_boot_id='public-memory-v24-test', final_summary_max_utf8_bytes=301)
            case = build('before', 'question_will')['cases'][0]
            with self.assertRaises(InterruptedError):
                summary(worker.prepared_case(case, memory), lambda: True)
            self.assertEqual('cancelled', summary.failure_metadata()['code'])
            self.assertEqual([], client.calls)

    def test_project_imports_restore_original_modules_and_path(self):
        original_path = list(sys.path)
        previous = sys.modules.get('common')
        marker = types.ModuleType('common')
        marker.__path__ = ['public-marker']
        marker.kept = 'kept'
        sys.modules['common'] = marker
        try:
            with worker.isolated_project_imports():
                sys.modules['common'] = types.ModuleType('common')
                sys.path.insert(0, 'public-test-only')
            self.assertIs(sys.modules['common'], marker)
            self.assertEqual('kept', marker.kept)
            self.assertEqual(original_path, sys.path)
        finally:
            if previous is None:
                sys.modules.pop('common', None)
            else:
                sys.modules['common'] = previous

    def test_public_guard_blocks_db_and_device_events(self):
        with self.assertRaises(RuntimeError):
            worker.prohibit_private_data_and_devices('ctypes.dlopen', (None,))
        for event, args in [('sqlite3.connect', (':memory:',)), ('ctypes.dlopen', ('native.so',)),
                            ('open', ('/home/root/private.sqlite3', 'r', 0)), ('open', ('/dev/video0', 'r', 0))]:
            with self.subTest(event=event, args=args), self.assertRaises(RuntimeError):
                worker.prohibit_private_data_and_devices(event, args)

    def test_metadata_guard_only_allows_python_C_API_and_restores_summary_phase(self):
        self.assertEqual('summary', worker.AUDIT_PHASE)
        with worker.metadata_guard_imports():
            self.assertEqual('metadata_guard', worker.AUDIT_PHASE)
            worker.prohibit_private_data_and_devices('ctypes.dlopen', (None,))
            for event, args in [('ctypes.dlopen', ('libvart.so',)), ('sqlite3.connect', (':memory:',))]:
                with self.assertRaises(RuntimeError):
                    worker.prohibit_private_data_and_devices(event, args)
        self.assertEqual('summary', worker.AUDIT_PHASE)
        with self.assertRaises(RuntimeError):
            worker.prohibit_private_data_and_devices('ctypes.dlopen', (None,))

    def test_devnull_remains_allowed_and_database_reads_forbidden(self):
        for phase in ('summary', 'metadata_guard'):
            with patch.object(worker, 'AUDIT_PHASE', phase):
                worker.prohibit_private_data_and_devices('open', ('/dev/null', 'r+', 2))
                with self.assertRaises(RuntimeError):
                    worker.prohibit_private_data_and_devices('sqlite3.connect', (b'file:///private.sqlite3?mode=ro',))

    def test_request_plan_uses_production_capacity_and_all_fifteen_cases(self):
        value = build('before', 'all')
        self.assertEqual(16, value['planned_initial_model_calls'])
        self.assertEqual(15, len(value['initial_request_plan']))
        self.assertTrue(all(row['maximum_initial_message_cost'] <= 2048 for row in value['initial_request_plan']))
        self.assertEqual(256, value['production_max_calls_per_case'])
        self.assertEqual(900000, value['production_total_budget_ms_per_case'])

    def test_candidate_overlay_cannot_replace_common_memory(self):
        value = build('before', 'all')
        value['mode'] = 'candidate'
        value['candidate_sources'] = {'common.board_memory': {}}
        with tempfile.TemporaryDirectory(prefix='public-v24-shell-') as directory:
            path = Path(directory) / 'public.json'
            raw = json.dumps(value).encode()
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'policy_only'):
                worker.read_payload(path, worker.digest(raw))

    def test_only_messages_ast_body_may_change(self):
        raw = (prepare.ACTUAL_SOURCES / prepare.POLICY_RELATIVE).read_bytes()
        original = prepare.protected_policy(raw)
        tree = ast.parse(raw)
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BoardSummaryClient')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_messages')
        method.body = [ast.Return(value=ast.Constant(value='public fixture'))]
        self.assertEqual(original, prepare.protected_policy(ast.unparse(tree)))
        altered = raw.replace(b'total_budget_ms=900000', b'total_budget_ms=800000', 1)
        self.assertNotEqual(original, prepare.protected_policy(altered))

    def test_original_audit_import_pause_and_fast_guard_ast_are_identical(self):
        old = (prepare.REPAIR / 'memory_negation_model_validation_v23/r2_devnull/worker.py').read_bytes()
        self.assertEqual('45a0cc92e1b5bf9a02b8746313556d6abec1f056f7bdf943ad75aa99c071752c', worker.digest(old))
        wanted = {'need', 'digest', 'parse', 'isolated_project_imports', 'metadata_guard_imports',
                  'prohibit_private_data_and_devices', 'saved_pause', 'fast_guard'}
        def functions(raw):
            return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(raw).body
                    if isinstance(node, ast.FunctionDef) and node.name in wanted}
        self.assertEqual(functions(old), functions((prepare.HERE / 'worker.py').read_bytes()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
