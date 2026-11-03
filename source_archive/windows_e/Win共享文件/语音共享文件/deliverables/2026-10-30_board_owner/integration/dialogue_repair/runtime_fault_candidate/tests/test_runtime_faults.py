"""Actual helper/tick AST, fake widgets and sinks; no GTK, device or model."""
import ast
from collections import deque
import contextlib
import copy
import io
import json
from pathlib import Path
import queue
import sys
import time
from types import SimpleNamespace, ModuleType
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'after/tools/board_avatar_gtk.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))
STAGE = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == 'BoardAvatarStage')
HELPER = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == '_runtime_fault_metadata')
TICK = next(n for n in STAGE.body if isinstance(n, ast.FunctionDef) and n.name == 'tick')
ENV = dict(deque=deque, time=time, queue=queue, json=json)
exec(compile(ast.Module(body=[HELPER, TICK], type_ignores=[]), str(SOURCE), 'exec'), ENV)
metadata = ENV['_runtime_fault_metadata']


class Label:
    def __init__(self): self.text = ''
    def set_text(self, value): self.text = value


class Sink:
    def __init__(self): self.cancels = 0
    def read(self):
        return dict(rgb=b'', jpeg=b'', sequence=1, state=dict(phase='IDLE', paused=False,
            playing=False, error='', reply='', visual_time=10., state='IDLE', asset=None,
            index=0, speech_gain=0., mouth_level=0., blink_active=False, audio_time=0.))
    def cancel(self): self.cancels += 1


class FaultTests(unittest.TestCase):
    def make(self):
        sink = Sink()
        bridge = SimpleNamespace(commands=queue.Queue(), records=[])
        bridge.publish = lambda state, frame: bridge.records.append(copy.deepcopy(state))
        obj = SimpleNamespace(closed=False, last_tick=None, diagnostic_result=None,
            diagnostic_job=None, native_video=None, character_pair=None, last_runtime_refresh=-1000.,
            character='public-fixture', displayed_frames=0, last_avatar_sequence=0,
            controller=sink, bridge=bridge, demo_status=Label(),
            reply=Label(), status=Label(), samples=[], board_business=None, errors=[])
        obj.refresh_settings = lambda state: 'settings'
        obj.refresh_runtime = lambda state, text: None
        business = ModuleType('tools.production_business_ui')
        business.project_business_ui = lambda stage, state: None
        presentation = ModuleType('tools.production_memory_presentation')
        presentation.project_presentation = lambda stage, state: state
        patcher = mock.patch.dict(sys.modules, {
            'tools.production_business_ui': business,
            'tools.production_memory_presentation': presentation})
        patcher.start()
        self.addCleanup(patcher.stop)
        return obj

    def test_no_exception_body_locals_prefix_or_exception_object_survives(self):
        secret = 'PRIVATE_MESSAGE_PCM_OR_PROFILE_ID_397431'
        namespace = {}
        exec(compile('def fail():\n    private_local = "' + secret + '"\n    raise TypeError(private_local)\n',
            'C:\\private_prefix_secret\\safe_fixture.py', 'exec'), namespace)
        try: namespace['fail']()
        except Exception as exc: report = metadata(exc, 1)
        encoded = json.dumps(report)
        self.assertNotIn(secret, encoded)
        self.assertNotIn('private_prefix_secret', encoded)
        self.assertNotIn('private_local', encoded)
        self.assertEqual(report['last']['error_class'], 'TypeError')
        self.assertTrue(any(frame['file'] == 'safe_fixture.py' and frame['function'] == 'fail'
            for frame in report['last']['frames']))
        self.assertTrue(all(set(f) == {'file', 'function', 'line'} for f in report['last']['frames']))
        self.assertTrue(all('/' not in f['file'] and '\\' not in f['file'] for f in report['last']['frames']))

    def test_unknown_class_and_large_stack_are_bounded(self):
        failure = type('PRIVATE_SECRET_EXCEPTION_CLASS', (Exception,), {})
        def recurse(left):
            if left: return recurse(left - 1)
            raise failure('private message')
        try: recurse(45)
        except Exception as exc: report = metadata(exc, 999999999999999999999999)
        self.assertEqual(report['count'], 9007199254740991)
        self.assertEqual(report['last']['error_class'], 'other')
        self.assertEqual(len(report['last']['frames']), 6)
        self.assertTrue(report['last']['frames_truncated'])
        self.assertNotIn('PRIVATE_SECRET', json.dumps(report))

    def test_actual_tick_counts_repeated_faults_keeps_cancel_and_deduplicates_log(self):
        obj = self.make()
        def fail(state): raise TypeError('PRIVATE_FAULT_MESSAGE')
        obj.refresh_settings = fail
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            for _ in range(3):
                obj.last_runtime_refresh = -1000.
                self.assertTrue(ENV['tick'](obj))
        self.assertEqual(obj.controller.cancels, 3)
        self.assertEqual(obj.runtime_faults['count'], 3)
        self.assertEqual(log.getvalue().count('STAGE RUNTIME_FAULT '), 1)
        self.assertNotIn('PRIVATE_FAULT_MESSAGE', log.getvalue())
        self.assertEqual(obj.status.text, 'TypeError')
        self.assertFalse(any(isinstance(v, BaseException) for v in vars(obj).values()))
        obj.refresh_settings = lambda state: 'settings'
        obj.last_runtime_refresh = -1000.
        self.assertTrue(ENV['tick'](obj))
        published = obj.bridge.records[-1]['runtime_faults']
        self.assertEqual(published, obj.runtime_faults)
        published['last']['frames'][0]['line'] = -1
        self.assertGreater(obj.runtime_faults['last']['frames'][0]['line'], 0)

    def test_new_static_position_logs_once_without_retaining_history(self):
        obj = self.make()
        def fail_one(state): raise TypeError('SECRET_ONE')
        def fail_two(state): raise TypeError('SECRET_TWO')
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            for fail in (fail_one, fail_two, fail_two):
                obj.refresh_settings = fail
                obj.last_runtime_refresh = -1000.
                ENV['tick'](obj)
        self.assertEqual(obj.runtime_faults['count'], 3)
        self.assertEqual(log.getvalue().count('STAGE RUNTIME_FAULT '), 2)
        self.assertNotIn('SECRET_', log.getvalue())
        self.assertFalse(any(frame['function'] == 'fail_one' for frame in obj.runtime_faults['last']['frames']))

    def test_normal_tick_publishes_zero_without_cancel(self):
        obj = self.make()
        self.assertTrue(ENV['tick'](obj))
        self.assertEqual(obj.controller.cancels, 0)
        self.assertEqual(obj.bridge.records[-1]['runtime_faults'],
            dict(metadata_only=True, count=0, last=None))


class DisplayActivityTests(unittest.TestCase):
    def test_audio_listener_keeps_display_awake_and_paused_idle_does_not(self):
        refresh = next(n for n in STAGE.body if isinstance(n, ast.FunctionDef) and n.name == 'refresh_runtime')
        call = next(n for n in refresh.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'tick')
        for listening, visual, automatic, playing, expected in (
            (True, False, False, False, True),
            (False, False, False, False, False),
            (False, False, True, False, True),
            (False, False, False, True, True),
            (False, True, False, False, False)):
            with self.subTest(listening=listening, automatic=automatic, playing=playing):
                received = []
                env = dict(self=SimpleNamespace(display_activity=SimpleNamespace(tick=received.append)),
                    handsfree=dict(enabled=listening, visual_bound=visual),
                    automatic=dict(enabled=automatic), state=dict(playing=playing))
                exec(compile(ast.Module(body=[call], type_ignores=[]), str(SOURCE), 'exec'), env)
                self.assertEqual(received, [expected])


if __name__ == '__main__': unittest.main()
