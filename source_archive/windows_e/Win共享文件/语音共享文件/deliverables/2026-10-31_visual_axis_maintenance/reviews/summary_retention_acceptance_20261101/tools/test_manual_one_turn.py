"""Public fake-state tests. This file never accesses a device or real user data."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import time
import unittest

HERE = Path(__file__).resolve().parents[1]
CONTROL = HERE / 'remote/manual_one_turn_control.py'


class FakeClock:
    def __init__(self):
        self.now = 0.

    def monotonic(self):
        return self.now

    def sleep(self, amount):
        self.now += amount


def idle():
    return dict(handsfree_dialogue=dict(enabled=False, state='PAUSED', conversation_entered=False, microphone_open=False),
                automatic_conversation=dict(enabled=False), phase='IDLE', playing=False, paused=False,
                pending_job=None, audio_output_state='IDLE_READY',
                local_recording=dict(state='READY', can_stop=False, can_start=True, max_seconds=20),
                local_transcription=dict(state='ANSWERED', service=dict(pending=False, feedback_ready=True)),
                manual_pan=dict(automatic_following=False, state='READY',
                                readback=dict(flags=0, lease_left_ms=0, active=False, armed=False)),
                ui_runtime=dict(pending_count=0, snapshot=dict(capabilities=dict(record_start=False),
                               modules=dict(audio=dict(state='IDLE'), interaction=dict(state='IDLE')))))


def recording():
    value = idle()
    value['handsfree_dialogue']['microphone_open'] = True
    value['local_recording'].update(state='RECORDING', can_stop=True, can_start=False)
    return value


def namespace(sequence):
    calls = []
    values = iter(copy.deepcopy(sequence))
    last = None
    def get_json(*args):
        nonlocal last
        last = next(values, last)
        return last
    ns = dict(json=json, time=FakeClock(), get_json=get_json, ui_command=lambda data: calls.append(data))
    source = CONTROL.read_text('utf-8')
    tree = ast.parse(source)
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.Assign))]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CONTROL), 'exec'), ns)
    return ns, calls


class ManualEntryTests(unittest.TestCase):
    def test_starts_only_public_local_recording(self):
        ns, calls = namespace([idle(), recording()])
        result = ns['manual_start']()
        self.assertEqual(calls, [dict(type='service_action', action='record_start')])
        self.assertEqual(result['local_recording_state'], 'RECORDING')
        self.assertIs(result['monitor_owned_directly_observable'], False)

    def test_refuses_automatic_owner_before_command(self):
        for owner in ('handsfree_dialogue', 'automatic_conversation'):
            value = idle()
            value[owner]['enabled'] = True
            ns, calls = namespace([value])
            with self.assertRaises(AssertionError):
                ns['manual_start']()
            self.assertEqual(calls, [])

    def test_refuses_inflight_answer_before_record_start_can_cancel(self):
        for field, value in [('phase', 'SPEAKING'), ('playing', True), ('pending_job', 1), ('paused', True)]:
            state = idle()
            state[field] = value
            ns, calls = namespace([state])
            with self.assertRaises(AssertionError):
                ns['manual_start']()
            self.assertEqual(calls, [])

    def test_refuses_remote_route_or_remote_work(self):
        values = []
        value = idle()
        value['ui_runtime']['snapshot']['capabilities']['record_start'] = True
        values.append(value)
        value = idle()
        value['ui_runtime']['snapshot']['modules']['audio']['state'] = 'PLAYING'
        values.append(value)
        value = idle()
        value['ui_runtime']['snapshot']['modules']['interaction']['state'] = 'PROCESSING'
        values.append(value)
        value = idle()
        value['ui_runtime']['snapshot'] = None
        values.append(value)
        for value in values:
            ns, calls = namespace([value])
            with self.assertRaises(AssertionError):
                ns['manual_start']()
            self.assertEqual(calls, [])

    def test_no_ready_without_local_recording(self):
        ns, calls = namespace([idle()])
        with self.assertRaises(RuntimeError):
            ns['manual_start']()
        self.assertEqual(len(calls), 1)
        self.assertGreaterEqual(ns['time'].now, 3.)

    def test_stop_uses_only_existing_public_ui(self):
        ns, calls = namespace([recording()])
        self.assertTrue(ns['manual_stop_from_public_ui']()['stop_sent'])
        self.assertEqual(calls, [dict(type='service_action', action='record_stop')])

    def test_no_duplicate_stop_after_manual_limit(self):
        for stage in ('TRANSCRIBING', 'GENERATING', 'PLAYING', 'ANSWERED'):
            value = idle()
            value['local_transcription']['state'] = stage
            ns, calls = namespace([value])
            self.assertFalse(ns['manual_stop_from_public_ui']()['stop_sent'])
            self.assertEqual(calls, [])

    def test_control_exactly_one_stop(self):
        ns, calls = namespace([recording()])
        ns['select'] = type('Select', (), {'select': staticmethod(lambda *args: ([1], [], []))})
        ns['sys'] = type('System', (), {'stdin': io.StringIO('{"command":"stop"}\n{"command":"stop"}\n')})
        ns['poll_manual_control']()
        ns['poll_manual_control']()
        self.assertEqual(calls, [dict(type='service_action', action='record_stop')])

    def test_sampling_refuses_unexpected_motion_or_automatic_enable(self):
        for section, key, val in [('manual_pan', 'automatic_following', True), ('automatic_conversation', 'enabled', True)]:
            value = idle()
            value[section][key] = val
            ns, _ = namespace([value])
            with self.assertRaises(AssertionError):
                ns['require_manual_sample'](value)

    def test_cleanup_drains_and_never_sends_commands(self):
        busy = idle()
        busy.update(phase='SPEAKING', playing=True)
        busy['local_transcription']['state'] = 'PLAYING'
        ns, calls = namespace([busy, busy, idle()])
        self.assertEqual(ns['settle_manual_without_cancel']()['status'], 'MANUAL_NATURALLY_PAUSED')
        self.assertEqual(calls, [])

    def test_timeout_preserves_inflight_answer_and_reports_pending(self):
        busy = idle()
        busy['local_transcription']['state'] = 'GENERATING'
        ns, calls = namespace([busy])
        result = ns['settle_manual_without_cancel']()
        self.assertEqual(result['status'], 'ANSWER_OR_CAPTURE_STILL_ACTIVE_CLEANUP_PENDING')
        self.assertFalse(result['cancel_sent'])
        self.assertFalse(result['pause_sent'])
        self.assertEqual(calls, [])

    def test_observer_privacy_and_target_logic_unchanged(self):
        original = (HERE.parent / 'joint_performance_20261101/remote/live_observer_caption_accepted.py').read_text('utf-8')
        manual = (HERE / 'remote/live_observer_manual_accepted.py').read_text('utf-8')
        def source_literal(text):
            tree = ast.parse(text)
            return next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == 'SOURCE' for t in node.targets))
        self.assertEqual(source_literal(original), source_literal(manual))
        self.assertEqual(original[original.index(' token=observed['):], manual[manual.index(' token=observed['):])
        for file in (CONTROL, HERE / 'remote/live_observer_manual_accepted.py'):
            ast.parse(file.read_text('utf-8'), feature_version=(3, 9))

    def test_length_prefix_preserves_followup_control_stream(self):
        source = b"import sys,json\nprint(json.dumps({'kind':'ready'}),flush=True)\nprint(json.dumps({'control':sys.stdin.readline(129)}),flush=True)\n"
        bootstrap = "import sys; n=int(sys.stdin.buffer.readline(16)); assert 0<n<200000; s=sys.stdin.buffer.read(n); assert len(s)==n; exec(compile(s,'<public-framing-test>','exec'))"
        process = subprocess.Popen([sys.executable, '-u', '-B', '-c', bootstrap], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.stdin.write(str(len(source)).encode() + b'\n' + source)
        process.stdin.flush()
        self.assertEqual(json.loads(process.stdout.readline()), {'kind': 'ready'})
        process.stdin.write(b'{"command":"stop"}\n')
        process.stdin.flush()
        self.assertEqual(json.loads(process.stdout.readline())['control'], '{"command":"stop"}\n')
        self.assertEqual(process.wait(timeout=3), 0)
        process.stdin.close()
        self.assertEqual(process.stderr.read(), b'')


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ManualEntryTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
    report = dict(schema='aura-manual-entry-public-fake-tests-1', tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful(),
                  device_accessed=False, private_data_used=False,
                  control_sha256=hashlib.sha256(CONTROL.read_bytes()).hexdigest())
    path = HERE / 'evidence/manual_entry_public_tests.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
    if not result.wasSuccessful():
        print(output.getvalue())
        raise SystemExit(1)


if __name__ == '__main__':
    main()
