"""Local public fixtures for v20 binding, pause, and owned child cleanup."""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import frontend_v20_common as common
import run_frontend_abba as runner
import test_frontend_budget as original


def state():
    return dict(phase='IDLE', playing=False, manual_pan=dict(automatic_following=False),
        handsfree_dialogue=dict(enabled=False, state='PAUSED', microphone_open=False,
            diagnostics=dict(armed=0, speech_starts=0, submitted=0)),
        avatar_display=dict(visible=True, frames=10, age_ms=1.),
        board_business=dict(dialogue=dict(pending=False), speaker=dict(queued_or_active=0),
                            memory=dict(completed=1, discarded=0)),
        private_transcript='PUBLIC_SENTINEL_MUST_NOT_EXPORT')


@contextlib.contextmanager
def guarded_fixture(value=None, *, wrong_owner=False, preference=False):
    mapping = common.baseline()
    calls = []
    value = state() if value is None else value
    def read(path, expected=None, maximum=None):
        calls.append((str(path), expected))
        path = Path(path)
        if path == common.ROOT / 'startup/config.json':
            return json.dumps(dict(component_sha256=mapping['component_pins'])).encode()
        if path.name == 'production_source_manifest.json':
            return json.dumps(dict(component_pins=mapping['component_pins'])).encode()
        if path.name == 'board_avatar_gtk.json':
            return json.dumps(dict(board_business=dict(asr_variant='paraformer_small', asr_threads=3,
                asr_directory='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6'))).encode()
        if path.name == 'listening_preference.json':
            return json.dumps(dict(version=1, enabled=preference)).encode()
        return b''
    def identity(pid):
        row = copy.deepcopy(next(mapping[role] for role in ('supervisor', 'gtk', 'camera') if mapping[role]['pid'] == pid))
        if wrong_owner and pid == mapping['gtk']['pid']:
            row['birth_ticks'] += 1
        return row
    def unit(name):
        role = 'camera' if name == 'aura-camera-ui.service' else 'supervisor'
        return dict(MainPID=str(mapping[role]['pid']), ActiveState='active', SubState='running')
    with patch.object(common, 'read_pinned', read), patch.object(common, 'boot_id', lambda: common.BOOT), \
            patch.object(common, 'process_identity', identity), \
            patch.object(common, 'process_parent', lambda pid: mapping['supervisor']['pid']), \
            patch.object(common, 'unit', unit), patch.object(common, 'metadata',
                lambda port, route: value if port == 8783 else dict(pid=mapping['camera']['pid'])):
        yield mapping, calls


class BaselineGuards(unittest.TestCase):
    def test_actual_mapping_has_380_and_exact_current_owners(self):
        value = common.baseline()
        self.assertEqual(len(value['component_pins']), 380)
        self.assertEqual([value[role]['pid'] for role in ('supervisor', 'gtk', 'camera')], [121485, 121489, 1335])

    def test_valid_empty_init_requires_its_exact_sha(self):
        with tempfile.TemporaryDirectory(prefix='public-empty-pin-') as temp:
            path = Path(temp).resolve() / '__init__.py'
            path.write_bytes(b'')
            self.assertEqual(common.read_pinned(path, common.sha(b'')), b'')
            with self.assertRaisesRegex(common.Refused, 'SOURCE_PIN'):
                common.read_pinned(path, '0' * 64)

    def test_full_guard_checks_every_component_including_empty_initializers(self):
        with guarded_fixture() as (mapping, calls):
            result = common.guard(mapping, full=True)
        expected = {(str(common.ROOT / 'runtime/aura' / key), pin) for key, pin in mapping['component_pins'].items()}
        self.assertEqual(len(expected), 380)
        self.assertTrue(expected.issubset(set(calls)))
        self.assertNotIn('PUBLIC_SENTINEL', json.dumps(result))

    def test_reused_pid_or_changed_saved_pause_is_rejected(self):
        for options in (dict(wrong_owner=True), dict(preference=True)):
            with self.subTest(options=options), guarded_fixture(**options) as (mapping, _):
                with self.assertRaises(common.Refused):
                    common.guard(mapping)

    def test_active_capture_playback_or_background_job_is_rejected(self):
        for case in ('capture', 'playback', 'speaker', 'dialogue', 'following'):
            value = state()
            if case == 'capture':
                value['handsfree_dialogue']['microphone_open'] = True
            elif case == 'playback':
                value['playing'] = True
            elif case == 'speaker':
                value['board_business']['speaker']['queued_or_active'] = 1
            elif case == 'dialogue':
                value['board_business']['dialogue']['pending'] = True
            else:
                value['manual_pan']['automatic_following'] = True
            with self.subTest(case=case), self.assertRaises(common.Refused):
                common.paused_metadata(value)

    def test_missing_capture_counters_are_not_accepted_as_quiet(self):
        value = state()
        value['handsfree_dialogue']['diagnostics'].pop('submitted')
        with self.assertRaisesRegex(common.Refused, 'CAPTURE_COUNTERS'):
            common.paused_metadata(value)

    def test_original_measurement_functions_are_ast_identical(self):
        path = common.HERE.parent / 'frontend_budget/public_frontend_budget.py'
        before = ast.parse(path.read_text(encoding='utf-8'))
        after = ast.parse((common.HERE / 'public_frontend_budget.py').read_text(encoding='utf-8'))
        names = {'selected_session_policy', 'TimedDenoiser', 'TimedVad', 'throughput'}
        def selected(tree):
            return {node.name: ast.dump(node, include_attributes=False) for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names}
        self.assertEqual(len(selected(before)), 4)
        self.assertEqual(selected(before), selected(after))

    def test_default_dry_does_not_read_devices_or_start_child(self):
        digest = common.sha((common.HERE / 'PACKAGE_MANIFEST.json').read_bytes())
        with patch('sys.argv', ['run_frontend_abba.py', '--package-sha256', digest]), \
                patch.object(common, 'guard', side_effect=AssertionError('device access')), \
                patch.object(runner.subprocess, 'Popen', side_effect=AssertionError('child started')):
            result = runner.main()
        self.assertEqual(result['status'], 'DRY_V20_PUBLIC_PACKAGE_VALIDATED')


class OwnedChildTests(unittest.TestCase):
    def fixture(self, *, reused=False):
        process = SimpleNamespace(pid=500, returncode=None)
        command = runner.worker_command('A1', 'baseline_1', 'f' * 64)
        identity = dict(pid=500, birth_ticks=123, command_sha256=common.sha(
            b'\0'.join(part.encode() for part in command) + b'\0'))
        reads, signals, timeouts = [], [], []
        def process_identity(pid):
            reads.append(pid)
            value = dict(identity)
            if reused and len(reads) >= 3:
                value['birth_ticks'] += 1
            return value
        def communicate(timeout):
            timeouts.append(timeout)
            if len(timeouts) == 1:
                raise subprocess.TimeoutExpired(command, timeout)
            process.returncode = -15
            return '', ''
        def killpg(pid, value):
            signals.append((pid, value))
            if value == 0:
                raise ProcessLookupError()
        process.communicate = communicate
        process.poll = lambda: process.returncode
        return process, process_identity, killpg, signals, timeouts

    def run_fixture(self, reused=False):
        process, identity, killpg, signals, timeouts = self.fixture(reused=reused)
        with patch.object(runner.subprocess, 'Popen', return_value=process), \
                patch.object(common, 'process_identity', identity), \
                patch.object(common, 'process_parent', lambda pid: runner.os.getpid()), \
                patch.object(runner.os, 'getpgid', lambda pid: pid, create=True), \
                patch.object(runner.os, 'getpgrp', lambda: 42, create=True), \
                patch.object(runner.os, 'killpg', killpg, create=True), \
                patch.object(runner.time, 'monotonic', lambda: 0.):
            with self.assertRaises(common.Refused if reused else subprocess.TimeoutExpired):
                runner.run_child('A1', 'baseline_1', 'f' * 64, 420.)
        return signals, timeouts

    def test_timeout_targets_only_owned_group_with_cleanup_inside_90_seconds(self):
        signals, timeouts = self.run_fixture()
        self.assertEqual(signals, [(500, runner.signal.SIGTERM), (500, 0)])
        self.assertEqual(timeouts, [82., 3.])

    def test_reused_birth_never_receives_a_signal(self):
        signals, _ = self.run_fixture(reused=True)
        self.assertEqual(signals, [])


class ComparisonGuards(unittest.TestCase):
    def test_old_379_sample_cannot_be_used_as_current_v20(self):
        rows = original.records()
        rows[0]['source_components_verified'] = 379
        self.assertEqual(original.COMPARE.compare(rows)['status'], 'CURRENT_SOURCE_PROOF_REQUIRED')

    def test_birth_or_background_counter_change_prevents_promotion(self):
        for case in ('birth', 'memory', 'capture'):
            rows = original.records()
            target = rows[1]['live_guard_after']
            if case == 'birth':
                target['owners']['gtk']['birth_ticks'] += 1
            elif case == 'memory':
                target['memory_completed'] += 1
            else:
                target['capture_stats']['submitted'] += 1
            with self.subTest(case=case):
                self.assertEqual(original.COMPARE.compare(rows)['status'], 'DO_NOT_DEPLOY')


if __name__ == '__main__':
    unittest.main()
