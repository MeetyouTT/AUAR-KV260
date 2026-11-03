import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch

import probe_memory_reason as probe

BOOT = '00000000-0000-0000-0000-000000000001'
CONFIG = b'public synthetic config'
PIN = hashlib.sha256(CONFIG).hexdigest()


def fixture():
    return dict(phase='IDLE', board_business=dict(data_origin='board', started=True,
        writer=dict(boot_id=BOOT, held=True), memory=dict(running=True, completed=160, discarded=106,
        error='candidate_rejected', retry_backoff=dict(last_failure_code='candidate_rejected', failure_streak=5,
        retry_in_seconds=33.9, last_delay_seconds=48., maximum_seconds=60.),
        summary_diagnostics=dict(state='failed', stage='full_source_validation', code='candidate_rejected',
        error_class='CandidateRejected', rejection_reasons=['protected_number_missing_or_changed'])),
        clock=dict(safe_for_compaction=True, anchored=True, persistent=True, same_boot=True,
        verified_age_seconds=241.18, uncertainty_seconds=19.69),
        clock_refresh=dict(error='', retry_in_seconds=10.)))


def actual_clean():
    root = Path(__file__).resolve().parent.parent
    path = root / 'animation_thinking_collaboration/runtime_v16/tools/production_memory_presentation.py'
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    keep = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_clean'
            or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('_BODY_KEYS', '_HISTORY_KEYS') for t in n.targets)]
    namespace = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['_clean']


def run_remote(state=None, boot=BOOT, configs=None):
    state = fixture() if state is None else state
    configs = iter([CONFIG, CONFIG] if configs is None else configs)
    class FakePath:
        def __init__(self, value): self.value = value
        def read_text(self):
            assert self.value == '/proc/sys/kernel/random/boot_id'
            return boot
        def read_bytes(self):
            assert self.value.endswith('/startup/config.json')
            return next(configs)
    connection = types.SimpleNamespace(request=lambda *a: None,
        getresponse=lambda: types.SimpleNamespace(status=200, read=lambda limit: json.dumps(state).encode()),
        close=lambda: None)
    out = io.StringIO()
    with patch('pathlib.Path', FakePath), patch('http.client.HTTPConnection', return_value=connection) as http:
        with contextlib.redirect_stdout(out):
            exec(compile(probe.remote_source(PIN, BOOT), '<synthetic-remote>', 'exec'), {})
    return json.loads(out.getvalue()), http.call_count


class MetadataContract(unittest.TestCase):
    def test_actual_clean_collapses_errors_but_keeps_fixed_metadata(self):
        clean = actual_clean()
        for code in ('model_failed', 'candidate_rejected', 'cancelled', 'deadline_exceeded',
                     'database_busy', 'compaction_failed', 'clock_unverified'):
            value = fixture(); value['board_business']['memory']['error'] = code
            value['board_business']['memory']['retry_backoff']['last_failure_code'] = code
            sanitized = clean(value)
            self.assertEqual('operation_failed', sanitized['board_business']['memory']['error'])
            output = probe.extract_memory_reason(sanitized)
            self.assertEqual(code, output['retry']['last_failure_code'])
            self.assertTrue(output['worker']['error_is_presentation_redaction'])
            self.assertEqual('full_source_validation', output['summary']['stage'])

    def test_summary_fixed_metadata_and_seven_reasons_preserved(self):
        value = fixture()
        reasons = ['protected_name_missing', 'protected_number_missing_or_changed', 'negation_missing',
                   'planned_status_missing', 'completed_status_missing', 'cancelled_status_missing',
                   'observation_evidence_missing']
        value['board_business']['memory']['summary_diagnostics']['rejection_reasons'] = reasons
        output = probe.extract_memory_reason(actual_clean()(value))
        self.assertEqual(reasons, output['summary']['rejection_reasons'])
        self.assertEqual('CandidateRejected', output['summary']['error_class'])
        self.assertEqual(0, output['unknown_counts']['unknown_enum_values'])

    def test_unknown_strings_body_ids_and_models_never_exported(self):
        value = fixture(); sentinel = 'PRIVATE_SENTINEL_TEMPLATE_ID_TEXT'
        value.update(text=sentinel, arbitrary=sentinel)
        memory = value['board_business']['memory']
        memory.update(error=sentinel, source_id=sentinel, result=dict(text=sentinel))
        memory['retry_backoff']['last_failure_code'] = sentinel
        memory['summary_diagnostics'] = dict(state=sentinel, stage=sentinel, code=sentinel,
            error_class=sentinel, method=sentinel, rejection_reasons=[sentinel, {'template': sentinel}])
        out = probe.extract_memory_reason(value)
        self.assertNotIn(sentinel, json.dumps(out))
        self.assertEqual('unknown', out['summary']['stage'])
        self.assertGreater(out['unknown_counts']['unknown_enum_values'], 0)
        self.assertEqual(2, out['unknown_counts']['unknown_rejection_reasons'])

    def test_nonfinite_bool_and_oversized_numbers_not_exported(self):
        value = fixture(); memory = value['board_business']['memory']
        memory['completed'] = float('nan'); memory['discarded'] = True
        memory['retry_backoff']['failure_streak'] = 2 ** 4096
        out = probe.extract_memory_reason(value)
        self.assertIsNone(out['worker']['completed']); self.assertIsNone(out['worker']['discarded'])
        self.assertIsNone(out['retry']['failure_streak'])
        self.assertEqual(3, out['unknown_counts']['invalid_numeric_values'])

    def test_missing_diagnostics_explicitly_unavailable(self):
        out = probe.extract_memory_reason({})
        self.assertEqual('unavailable', out['summary']['code'])
        self.assertEqual('unavailable', out['retry']['last_failure_code'])
        self.assertGreater(out['unknown_counts']['missing_fields'], 0)

    def test_remote_one_http_read_no_store_or_model_calls(self):
        out, count = run_remote(actual_clean()(fixture()))
        self.assertEqual(1, count); self.assertEqual('metadata_read', out['status'])
        self.assertEqual('candidate_rejected', out['retry']['last_failure_code'])
        self.assertFalse(out['snapshot_atomicity_verified'])
        self.assertNotIn(BOOT, json.dumps(out)); self.assertNotIn(PIN, json.dumps(out))

    def test_boot_mismatch_rejects_before_http(self):
        out, count = run_remote(boot='00000000-0000-0000-0000-000000000002')
        self.assertEqual(0, count); self.assertEqual('boot_mismatch', out['code'])

    def test_config_changes_across_read_rejects(self):
        out, count = run_remote(configs=[CONFIG, b'changed synthetic config'])
        self.assertEqual(1, count); self.assertEqual('configuration_pin_mismatch', out['code'])
        self.assertNotIn('summary', out)


if __name__ == '__main__':
    unittest.main()
