"""R2 regression executes the actual combined observer against public fake HTTP."""
from pathlib import Path
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import time
import unittest
from unittest.mock import patch
from test_manual_one_turn import ManualEntryTests, FakeClock, idle, recording, namespace

HERE = Path(__file__).resolve().parents[1]


def load_driver():
    spec = importlib.util.spec_from_file_location('manual_r2', HERE / 'tools/start_manual_one_turn_r2.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_literal():
    tree = ast.parse((HERE / 'remote/live_observer_manual_accepted.py').read_text('utf-8'))
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'SOURCE' for t in n.targets))


class FakePath:
    def __init__(self, value):
        self.value = str(value)

    def __truediv__(self, other):
        return FakePath(self.value + '/' + other)

    def read_bytes(self):
        return b'public-startup'

    def read_text(self):
        return 'public-boot'


class FakeResponse:
    status = 200
    def __init__(self, value):
        self.raw = json.dumps(value).encode()

    def read(self, limit):
        return self.raw[:limit]


def fake_http(frames, commands):
    values = iter(frames)
    last = frames[-1]
    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, method, path, body=None, headers=None):
            self.method, self.path = method, path
            if method == 'POST':
                data = json.loads(body)
                assert path == '/api/command'
                assert data in (dict(type='service_action', action='record_start'), dict(type='service_action', action='record_stop'))
                commands.append(data)

        def getresponse(self):
            if self.method == 'POST':
                return FakeResponse({'ok': True})
            assert self.method == 'GET' and self.path == '/api/state'
            return FakeResponse(next(values, last))

        def close(self):
            pass
    return Connection


class ManualR2Tests(ManualEntryTests):
    def test_reproduces_both_r1_namespace_collisions(self):
        shared, _ = namespace([recording()])
        shared.update(state=lambda: 'public-guard', sys=type('System', (), {'stdin': io.StringIO('')}),
                      select=type('Select', (), {'select': staticmethod(lambda *a: ([], [], []))}))
        with patch('http.client.HTTPConnection', fake_http([recording()], [])), patch('pathlib.Path', FakePath):
            exec(source_literal(), shared)
        with self.assertRaises(AttributeError):
            shared['poll_manual_control']()
        with self.assertRaises(TypeError):
            shared['state']()

    def test_actual_r2_remote_runs_three_samples_ack_cleanup_and_final_guard(self):
        driver = load_driver()
        rid = 'public-manual-query'
        latency = dict(asr_completed=True, entry_rejected=False, ordinary_prepare=True, complete=False)
        thinking = idle()
        thinking['phase'] = 'THINKING'
        thinking['local_transcription'].update(state='GENERATING', request_id=rid)
        thinking['board_business'] = {'dialogue': {'latency': latency}}
        answered = idle()
        answered['local_transcription'].update(state='ANSWERED', request_id=rid)
        answered['board_business'] = {'dialogue': {'latency': dict(latency, complete=True),
                                                'last_playback_ack': dict(request_id=rid, committed=True)}}
        control_values = iter([idle(), recording(), idle()])
        controls = []
        guard_calls = []
        shared = dict(json=json, time=time, get_json=lambda *args: next(control_values, idle()),
                      state=lambda: 'public-guard', STARTUP_SHA=hashlib.sha256(b'public-startup').hexdigest(),
                      BOOT='public-boot', MANUAL_CONTROL_SOURCE=(HERE / 'remote/manual_one_turn_control.py').read_text('utf-8'),
                      OBSERVER_SOURCE=(HERE / 'remote/live_observer_manual_accepted.py').read_text('utf-8'))
        import http.client
        shared['http'] = http
        def preflight():
            self.assertEqual(shared['state'](), 'public-guard')
            guard_calls.append(True)
            return dict(state=dict(listening_state='PAUSED', microphone_open=False, playing=False)), idle(), {}
        shared['preflight'] = preflight
        clock = FakeClock()
        output = io.StringIO()
        with patch('http.client.HTTPConnection', fake_http([recording(), thinking, answered], controls)), \
             patch('pathlib.Path', FakePath), patch('select.select', lambda *args: ([], [], [])), \
             patch('time.monotonic', clock.monotonic), patch('time.sleep', clock.sleep), \
             contextlib.redirect_stdout(output):
            exec(driver.REMOTE, shared)
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(sum(r.get('kind') == 'sample' for r in rows), 3)
        self.assertEqual(sum(r.get('kind') == 'ready' for r in rows), 1)
        self.assertTrue(any(r.get('status') == 'ONE_NEW_TURN_COMPLETE' for r in rows))
        self.assertTrue(rows[-1]['one_new_turn_complete'])
        self.assertEqual(rows[-1]['kind'], 'final_guard')
        self.assertEqual(rows[-2]['status'], 'MANUAL_NATURALLY_PAUSED')
        self.assertEqual(guard_calls, [True, True])
        self.assertEqual(controls, [dict(type='service_action', action='record_start')])
        self.assertTrue(callable(shared['state']))
        self.assertTrue(callable(shared['control_ns']['select'].select))
        ast.parse(driver.build_source()[0].decode('utf-8'), feature_version=(3, 9))


def main():
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(unittest.defaultTestLoader.loadTestsFromTestCase(ManualR2Tests))
    report = dict(schema='aura-manual-r2-combined-public-fake-tests-1', tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful(),
                  device_accessed=False, private_data_used=False,
                  old_attributeerror_and_typeerror_reproduced=True,
                  actual_combined_remote_three_samples_full_ack_cleanup_final_guard=True,
                  driver_sha256=hashlib.sha256((HERE / 'tools/start_manual_one_turn_r2.py').read_bytes()).hexdigest())
    path = HERE / 'evidence/manual_entry_r2_public_tests.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
    if not result.wasSuccessful():
        print(output.getvalue())
        raise SystemExit(1)


if __name__ == '__main__':
    main()
