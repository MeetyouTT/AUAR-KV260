"""Actual refresh_runtime inside actual tick; only widgets/services are fake."""
import ast
from collections import defaultdict, deque
import contextlib
import copy
import io
import json
from pathlib import Path
import queue
import sys
import time
from types import SimpleNamespace, ModuleType, MethodType
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[4] / 'aura'))
SOURCE = ROOT / 'after/tools/board_avatar_gtk.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))
STAGE = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == 'BoardAvatarStage')
NAMES = {'_finite_display_number', '_runtime_fault_metadata', 'avatar_rate_text', 'voice_host_display'}
nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in NAMES]
nodes.extend(n for n in STAGE.body if isinstance(n, ast.FunctionDef) and n.name in {'tick', 'refresh_runtime'})
ENV = dict(time=time, queue=queue, deque=deque, json=json)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), ENV)


class Style:
    def __init__(self): self.names = set()
    def has_class(self, name): return name in self.names
    def remove_class(self, name): self.names.discard(name)
    def add_class(self, name): self.names.add(name)


class Widget:
    def __init__(self): self.text = ''; self.sensitive = True; self.tooltip = None; self.style = Style()
    def set_text(self, value):
        if not isinstance(value, str): raise TypeError('synthetic widget requires text')
        self.text = value
    def get_text(self): return self.text
    def set_tooltip_text(self, value): self.tooltip = value
    def get_tooltip_text(self): return self.tooltip
    def set_label(self, value): self.set_text(value)
    def set_sensitive(self, value): self.sensitive = bool(value)
    def get_sensitive(self): return self.sensitive
    def set_visible(self, value): pass
    def get_style_context(self): return self.style
    def get_buffer(self): return self


class Sink:
    def __init__(self, state): self.state = state; self.cancels = 0
    def read(self): return dict(rgb=b'', jpeg=b'', sequence=1, state=copy.deepcopy(self.state))
    def cancel(self): self.cancels += 1


class RuntimeStatusTests(unittest.TestCase):
    def make(self, recording=None, transcription=None, timings=None):
        state = dict(phase='IDLE', paused=False, playing=False, error='', reply='', visual_time=10.,
            state='IDLE', asset=None, index=0, speech_gain=0., mouth_level=0., blink_active=False,
            audio_time=0., avatar_command_pending=False, ui_settings=dict(available=False),
            local_recording=recording or dict(state='READY', result=None, can_start=True),
            local_transcription=transcription or dict(state='IDLE', service={}))
        modules = dict(interaction=dict(state='IDLE', timings_ms=timings))
        view = dict(snapshot=dict(modules=modules, source_kind='actual', capabilities={}, preview=None),
            link='READY', pending_count=0, error='', results=[])
        sink = Sink(state); bridge = SimpleNamespace(commands=queue.Queue(), records=[])
        bridge.publish = lambda state, frame: bridge.records.append(copy.deepcopy(state))
        stage = SimpleNamespace(closed=False, last_tick=None, diagnostic_result=None, diagnostic_job=None,
            native_video=None, character_pair=None, last_runtime_refresh=-1000., character='public',
            displayed_frames=0, last_avatar_sequence=0, controller=sink, bridge=bridge,
            samples=[], board_business=None, errors=[], services=SimpleNamespace(read=lambda: copy.deepcopy(view)),
            preview_output=None, display_activity=SimpleNamespace(tick=lambda active: None),
            config={}, ui_layer='presentation', page='avatar', page_names=('avatar', 'vision', 'settings'),
            large_preview=None, lines=[],
            controls=defaultdict(Widget), device_cards=defaultdict(Widget), insight_labels=defaultdict(Widget),
            device_inventory=dict(camera_present=False, lan=True), touch_inputs=[],
            connection_store=SimpleNamespace(error=''), last_service_result=None, toast_until=0., toast='',
            refresh_voice_face_dialog=lambda tx: None)
        for name in ('mode_label', 'status', 'record_button', 'ask_button', 'interaction_cancel',
                     'transcript_label', 'reply_view', 'latency_label', 'preview_image', 'preview_expand',
                     'preview_placeholder', 'vision_note', 'vision_summary', 'device_note',
                     'connection_label', 'host_status_label', 'footer', 'demo_status', 'reply'):
            setattr(stage, name, Widget())
        stage.reply_text = ''
        stage.refresh_settings = lambda value: 'settings'
        stage.refresh_runtime = MethodType(ENV['refresh_runtime'], stage)
        business = ModuleType('tools.production_business_ui'); business.project_business_ui = lambda stage, state: None
        presentation = ModuleType('tools.production_memory_presentation'); presentation.project_presentation = lambda stage, state: state
        patcher = mock.patch.dict(sys.modules, {'tools.production_business_ui': business,
            'tools.production_memory_presentation': presentation})
        patcher.start(); self.addCleanup(patcher.stop)
        return stage, state, view

    def run_normal(self, stage):
        self.assertTrue(ENV['tick'](stage))
        self.assertEqual(stage.controller.cancels, 0)
        self.assertFalse(stage.errors)
        self.assertEqual(stage.bridge.records[-1]['runtime_faults']['count'], 0)

    def test_ready_missing_or_invalid_result_never_cancels_the_listener(self):
        for result in (None, {}, [], dict(duration_seconds=None), dict(duration_seconds=float('nan')),
                       dict(duration_seconds=float('inf')), dict(duration_seconds=True), dict(duration_seconds=-1)):
            with self.subTest(result=result):
                stage, state, view = self.make(recording=dict(state='READY', result=result, can_start=True))
                self.run_normal(stage)
                self.assertEqual(stage.status.text, '录音已完成')
                self.assertEqual(state['local_recording']['state'], 'READY')
                if result is None: self.assertIsNone(state['local_recording']['result'])

    def test_ready_valid_duration_preserves_existing_display(self):
        stage, state, _ = self.make(recording=dict(state='READY', result=dict(duration_seconds=1.236), can_start=True))
        self.run_normal(stage)
        self.assertEqual(stage.status.text, '录音已完成 · 1.24 秒')
        self.assertEqual(state['local_recording']['result']['duration_seconds'], 1.236)

    def test_original_ready_none_reproduces_same_outer_typeerror_cancel(self):
        original = ROOT.parent / 'runtime_fault_candidate/after/tools/board_avatar_gtk.py'
        tree = ast.parse(original.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoardAvatarStage')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'refresh_runtime')
        old = dict(ENV)
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(original), 'exec'), old)
        stage, _, _ = self.make()
        stage.refresh_runtime = MethodType(old['refresh_runtime'], stage)
        with contextlib.redirect_stdout(io.StringIO()): ENV['tick'](stage)
        self.assertEqual(stage.controller.cancels, 1)
        self.assertEqual(stage.runtime_faults['last']['error_class'], 'TypeError')
        self.assertTrue(any(f['function'] == 'refresh_runtime' for f in stage.runtime_faults['last']['frames']))

    def test_recognition_none_is_complete_without_invented_zero_ms(self):
        stage, state, _ = self.make(transcription=dict(state='READY', recognition_ms=None, service={}))
        self.run_normal(stage)
        self.assertEqual(stage.status.text, '转写完成')
        self.assertIsNone(state['local_transcription']['recognition_ms'])

    def test_recognition_valid_milliseconds_preserves_rounding(self):
        stage, _, _ = self.make(transcription=dict(state='READY', recognition_ms=32.6, service={}))
        self.run_normal(stage)
        self.assertEqual(stage.status.text, '转写完成 · 33 ms')

    def test_null_nan_and_valid_latency_entries_are_display_only(self):
        timings = dict(first_audio=None, asr=float('nan'), vlm=0., tts=19.6)
        stage, _, view = self.make(timings=timings)
        self.run_normal(stage)
        self.assertEqual(stage.latency_label.text, '首声 — · ASR — · VLM 0ms · TTS 20ms')
        self.assertIsNone(view['snapshot']['modules']['interaction']['timings_ms']['first_audio'])
        self.assertNotEqual(view['snapshot']['modules']['interaction']['timings_ms']['asr'],
                            view['snapshot']['modules']['interaction']['timings_ms']['asr'])

    def test_whole_timings_none_and_recording_duration_none_do_not_cancel(self):
        stage, _, _ = self.make(recording=dict(state='RECORDING', duration_seconds=None, can_stop=True), timings=None)
        self.run_normal(stage)
        self.assertEqual(stage.status.text, '正在录音')
        self.assertEqual(stage.latency_label.text, '首声 — · ASR — · VLM — · TTS —')

    def test_formatter_rejects_bad_types_without_mutating_or_caching_input(self):
        fmt = ENV['_finite_display_number']
        for value in (None, True, False, '12', {}, [], float('nan'), float('inf'), -1, 10 ** 500):
            with self.subTest(kind=type(value).__name__): self.assertIsNone(fmt(value))
        self.assertEqual(fmt(0), '0')
        self.assertEqual(fmt(1.236, 2), '1.24')


if __name__ == '__main__': unittest.main()
