"""Run the unchanged 8ebb observer and actual adapter REMOTE with public stand-ins."""
from pathlib import Path
import ast
import contextlib
import copy
import hashlib
import http.client
import importlib.util
import io
import json
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

class FakeClock:
    def __init__(self): self.now=0.
    def monotonic(self): return self.now
    def sleep(self, amount): self.now+=amount

class FakePath:
    def __init__(self,value): self.value=str(value)
    def __truediv__(self,other): return FakePath(self.value+'/'+other)
    def read_bytes(self): return b'public-startup'
    def read_text(self): return 'public-boot'

class FakeResponse:
    status=200
    def __init__(self,value): self.raw=json.dumps(value).encode()
    def read(self,limit): return self.raw[:limit]

HERE = Path(__file__).resolve().parents[1]
ORIGINAL = HERE.parent / 'joint_performance_20261101/remote/live_observer_caption_accepted.py'


def load_adapter():
    spec = importlib.util.spec_from_file_location('ec12_observer_adapter', HERE / 'tools/start_pause_resume_one_turn.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame(stage='IDLE', *, rid=None, rejected=False, complete=False):
    latency = dict(asr_completed=bool(rid), entry_rejected=rejected, ordinary_prepare=bool(rid), complete=complete)
    value = dict(phase='THINKING' if stage == 'GENERATING' else 'IDLE', playing=False,
                 handsfree_dialogue=dict(enabled=True, state='WAITING_SPEECH', microphone_open=True),
                 local_transcription=dict(state=stage, request_id=rid, text=''), reply='',
                 board_business=dict(dialogue=dict(latency=latency)),
                 presentation_lifecycle=dict(showing=False, epoch=1, invalidations=0, expirations=0))
    if complete:
        value['handsfree_dialogue'].update(state='CONVERSATION', microphone_open=False)
        value['board_business']['dialogue']['last_playback_ack'] = dict(request_id=rid, committed=True)
    return value


def execute_remote(frames, *, changed_scope=False, wrong_ack=False):
    adapter = load_adapter()
    sequence = iter(copy.deepcopy(frames))
    model = dict(enabled=False, current=None, commands=[], guard_calls=0, selection_calls=0)
    last = frames[-1]
    def get_state():
        if not model['enabled']:
            return dict(phase='IDLE', playing=False, local_transcription=dict(state='ANSWERED'),
                        handsfree_dialogue=dict(enabled=False, state='PAUSED', microphone_open=False),
                        manual_pan=dict(state='READY', automatic_following=False,
                                        readback=dict(flags=0, lease_left_ms=0, active=False, armed=False)))
        return model['current'] or frames[0]
    class Connection:
        def __init__(self, *args, **kwargs):
            self.method = None
        def request(self, method, path, body=None, headers=None):
            self.method = method
            self.path = path
            if method == 'POST':
                data = json.loads(body)
                assert data == dict(type='conversation_toggle')
                model['commands'].append(data)
                model['enabled'] = not model['enabled']
        def getresponse(self):
            assert self.path in ('/api/state', '/api/command')
            if self.method == 'POST':
                return FakeResponse(dict(ok=True))
            value = next(sequence, copy.deepcopy(last))
            if wrong_ack and value.get('board_business', {}).get('dialogue', {}).get('last_playback_ack'):
                value['board_business']['dialogue']['last_playback_ack']['request_id'] = 'another-public-answer'
            model['current'] = value
            return FakeResponse(value)
        def close(self):
            pass
    def scope():
        model['selection_calls'] += 1
        return dict(scope_token='b'*64 if changed_scope and model['selection_calls'] >= 2 else 'a'*64,
                    selection_file_sha256='c'*64, raw_identifier_exported=False,
                    saved_reference_is_not_a_new_profile_grant=True)
    def preflight():
        model['guard_calls'] += 1
        value = get_state()
        h = value['handsfree_dialogue']
        state = dict(listening_enabled=h['enabled'], listening_state=h['state'],
                     microphone_open=h['microphone_open'], playing=False)
        return dict(state=state), value, {}
    clock = FakeClock()
    output = io.StringIO()
    namespace = dict(json=json, time=time, http=http, STARTUP_SHA=hashlib.sha256(b'public-startup').hexdigest(),
                     BOOT='public-boot', preflight=preflight, selection_scope_metadata=scope,
                     get_json=lambda *args: get_state(), document=lambda *args: {'enabled': model['enabled']},
                     state=lambda: 'original-guard-helper', OBSERVER_SOURCE=ORIGINAL.read_text('utf-8'))
    with patch('http.client.HTTPConnection', Connection), patch('pathlib.Path', FakePath), \
         patch('time.monotonic', clock.monotonic), patch('time.sleep', clock.sleep), \
         contextlib.redirect_stdout(output):
        exec(adapter.REMOTE, namespace)
    rows = [json.loads(line) for line in output.getvalue().splitlines()]
    return rows, model, namespace


class Ec12ObserverTests(unittest.TestCase):
    def test_real_three_samples_accepted_ack_and_same_scope_pause(self):
        rows, model, ns = execute_remote([frame(), frame('GENERATING', rid='public-query'), frame('ANSWERED', rid='public-query', complete=True)])
        self.assertEqual(sum(r.get('kind') == 'sample' for r in rows), 3)
        self.assertTrue(any(r.get('kind') == 'ready' for r in rows))
        self.assertTrue(any(r.get('status') == 'ONE_NEW_TURN_COMPLETE' for r in rows))
        self.assertEqual(rows[-1]['kind'], 'final_guard')
        self.assertTrue(rows[-1]['one_new_turn_complete'])
        self.assertTrue(rows[-1]['scope_preserved'])
        self.assertEqual(model['commands'], [dict(type='conversation_toggle')] * 2)
        self.assertFalse(model['enabled'])
        self.assertTrue(callable(ns['state']))
        self.assertTrue(isinstance(ns['live_ns']['state'], dict))
        self.assertIsNot(ns, ns['live_ns'])

    def test_changed_scope_refuses_ready_and_still_normally_pauses(self):
        rows, model, _ = execute_remote([frame()], changed_scope=True)
        self.assertFalse(any(r.get('kind') == 'ready' for r in rows))
        self.assertTrue(any(r.get('kind') == 'observer_exception' for r in rows))
        self.assertFalse(rows[-1]['one_new_turn_complete'])
        self.assertFalse(rows[-1]['scope_preserved'])
        self.assertFalse(model['enabled'])

    def test_rejected_entry_does_not_replace_first_accepted_target(self):
        rows, _, _ = execute_remote([frame(), frame('GENERATING', rid='public-rejected', rejected=True),
                                    frame('GENERATING', rid='public-accepted'), frame('ANSWERED', rid='public-accepted', complete=True)])
        complete = next(r for r in rows if r.get('status') == 'ONE_NEW_TURN_COMPLETE')
        self.assertEqual(complete['request_token'], hashlib.sha256(b'public-accepted').hexdigest())

    def test_other_ack_never_passes(self):
        rows, model, _ = execute_remote([frame(), frame('GENERATING', rid='public-query'),
                                        frame('ANSWERED', rid='public-query', complete=True)], wrong_ack=True)
        self.assertFalse(any(r.get('status') == 'ONE_NEW_TURN_COMPLETE' for r in rows))
        self.assertTrue(any(r.get('status') == 'WINDOW_TIMEOUT' for r in rows))
        self.assertFalse(rows[-1]['one_new_turn_complete'])
        self.assertFalse(model['enabled'])

    def test_real_source_bytes_and_python39_syntax(self):
        self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(), '8ebb76746cb87bd3608671848cc8087d724e24d4282f2933a3c15b4879bd4819')
        ast.parse(load_adapter().REMOTE, feature_version=(3, 9))
        ast.parse((HERE / 'remote/selection_scope_metadata.py').read_text('utf-8'), feature_version=(3, 9))

    def test_nonready_receipt_refuses_before_any_ssh_process(self):
        adapter = load_adapter()
        with tempfile.TemporaryDirectory(prefix='aura-public-ready-') as directory:
            proof = Path(directory) / 'public_pending.json'
            proof.write_text(json.dumps({'result': {'status': 'READINESS_PENDING_GUARD_RETAINED'}}), encoding='utf-8')
            with patch.object(sys, 'argv', ['adapter', '--ready-evidence', str(proof)]), \
                 patch.object(adapter.subprocess, 'Popen', side_effect=AssertionError('SSH must not be reached')) as transport:
                with self.assertRaises(AssertionError):
                    adapter.main()
                transport.assert_not_called()


def main():
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(unittest.defaultTestLoader.loadTestsFromTestCase(Ec12ObserverTests))
    report = dict(schema='aura-ec12-real-8ebb-adapter-public-tests-1', tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful(),
                  real_source_multi_sample_full_ack_cleanup_guard=True,
                  scope_change_refuses_before_ready=True, rejected_entry_and_foreign_ack_checked=True,
                  pending_readiness_cannot_start_ssh=True, device_or_private_data_accessed=False,
                  adapter_sha256=hashlib.sha256((HERE / 'tools/start_pause_resume_one_turn.py').read_bytes()).hexdigest())
    path = HERE / 'evidence/ec12_observer_combined_public_tests.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
    if not result.wasSuccessful():
        print(output.getvalue())
        raise SystemExit(1)


if __name__ == '__main__':
    main()
