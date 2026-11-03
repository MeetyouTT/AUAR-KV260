"""Actual GUI methods with public fake widgets/clock; no GTK, DB or devices."""
import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
import queue
import sys
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / 'before/tools/board_avatar_gtk.py'
AFTER = ROOT / 'after/tools/board_avatar_gtk.py'
REFERENCE = ROOT / 'reference/production_memory_presentation.py'
BEFORE_SHA = '4c3e692acf23f78c9ce9c66f75f6f95f14c08b34ec371ff09842ffbdd911951a'
LIFECYCLE_SHA = '8c0cddcdcd91c44eccfd73240826f7b08b8a118c367e15e26295942b9b7ba4aa'
assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == LIFECYCLE_SHA
spec = importlib.util.spec_from_file_location('public_lifecycle', REFERENCE)
presentation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(presentation)
OWNER = dict(board_boot_id='public-boot', session_id='public-session', generation=1,
             request_id='public-request')


class Clock:
    now = 10.0
    def __call__(self): return self.now


class Widget:
    def __init__(self):
        self.text = self.tooltip = ''
        self.writes = self.tooltip_writes = 0
        self.sensitive = True
        self.classes = set()
    def set_text(self, text): self.text = text; self.writes += 1
    def get_text(self, *args): return self.text
    def set_tooltip_text(self, text): self.tooltip = text; self.tooltip_writes += 1
    def get_tooltip_text(self): return self.tooltip
    def set_label(self, text): self.text = text
    def set_sensitive(self, value): self.sensitive = value
    def get_sensitive(self): return self.sensitive
    def set_visible(self, value): self.visible = value
    def get_buffer(self): return self
    def get_bounds(self): return 0, len(self.text)
    def get_style_context(self): return self
    def has_class(self, value): return value in self.classes
    def add_class(self, value): self.classes.add(value)
    def remove_class(self, value): self.classes.discard(value)


class Worker:
    def __init__(self, state): self.state = state; self.reads = self.cancelled = 0
    def read(self):
        self.reads += 1
        return dict(state=copy.deepcopy(self.state), sequence=42, image=None,
                    rgb=None, jpeg=b'')
    def cancel(self): self.cancelled += 1


class Bridge:
    def __init__(self): self.commands = queue.Queue(); self.lock = threading.Lock(); self.state = {}; self.publishes = 0
    def publish(self, state, frame): self.state = copy.deepcopy(state); self.publishes += 1


class Store:
    failure = False
    calls = 0
    def operation(self, *args, **kwargs):
        self.calls += 1
        if self.failure: raise ValueError('public synthetic commit failure')
        return {'committed': True, 'result': 'public fake commit'}
    forget = clear = correct = commit_compaction = operation


def methods(path, clock):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in
                 ('_finite_display_number', '_runtime_fault_metadata', 'voice_host_display', 'avatar_rate_text')]
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoardAvatarStage')
    functions += [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('tick', 'refresh_runtime')]
    from collections import deque
    scope = dict(time=NS(monotonic=clock, perf_counter=clock), queue=queue, deque=deque)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), scope)
    return scope


def fixture(path=AFTER, *, production=True):
    clock = Clock()
    state = dict(phase='IDLE', playing=False, paused=False, reply='', error='',
        avatar_command_pending=0, automatic_conversation={},
        handsfree_dialogue=dict(enabled=True, state='WAITING_SPEECH'),
        local_recording=dict(state='RECORDING', can_stop=True, can_start=False),
        local_transcription=dict(state='IDLE', text='', service=dict(enabled=True, conversation=True)),
        ui_settings=dict(available=True), visual_time=0.0, state='IDLE', asset=None,
        index=None, speech_gain=0.0, mouth_level=0.0, blink_active=False, audio_time=0.0)
    view = dict(snapshot=dict(source_kind='actual', modules={}, capabilities={}),
                pending_count=0, link='READY', error='', results=[])
    stage = NS(closed=False, diagnostic_result=None, last_tick=None, last_runtime_refresh=0.,
        bridge=Bridge(), controller=Worker(state), native_video=None,
        character_pair=NS(status=lambda: dict(target_fps=16)), native_yuki=NS(ready=True),
        last_avatar_sequence=0, displayed_frames=0, preview_output=None,
        services=NS(read=lambda: copy.deepcopy(view)), display_activity=NS(tick=lambda *a: None),
        refresh_voice_face_dialog=lambda *a: None, config={}, ui_layer='presentation',
        page='conversation', page_names=['conversation'], reply_text=None, lines=[],
        large_preview=None, device_inventory=dict(camera_present=True, lan=True),
        touch_inputs=True, connection_store=NS(error=''), last_service_result=None,
        toast='', toast_until=0., runtime_view={}, samples=[], character='public-character',
        diagnostic_job=None, errors=[], refresh_count=0, business_count=0)
    widget_names = ('mode_label status transcript_label reply_view reply latency_label record_button '
        'interaction_cancel ask_button preview_image preview_expand preview_placeholder '
        'vision_note vision_summary device_note connection_label host_status_label footer demo_status').split()
    for name in widget_names: setattr(stage, name, Widget())
    stage.controls = {k: Widget() for k in ('target_select', 'identity_enroll', 'identity_delete',
                      'vision_target_select', 'vision_identity')}
    stage.insight_labels = {k: Widget() for k in ('people', 'target', 'identity')}
    stage.device_cards = {k: Widget() for k in ('camera', 'vision', 'target', 'identity', 'motion',
                         'host', 'audio', 'touch', 'network')}
    stage.refresh_settings = lambda state: 'public settings'
    scope = methods(path, clock)
    def refresh(state, text):
        stage.refresh_count += 1
        return scope['refresh_runtime'](stage, state, text)
    stage.refresh_runtime = refresh
    if production:
        jobs = NS(playback_invalidator=None, condition=threading.RLock(), _active_job=None, active=None)
        jobs._current = lambda job: jobs._active_job is job
        runtime = NS(config=NS(data_origin='board'), store=Store(), jobs=jobs,
                     _foreground_idle=lambda: False, public=lambda: dict(metadata_only=True))
        stage.board_business = NS(runtime=runtime)
        visual = NS(channel_event=lambda *a: None, stream=None)
        recording = NS(controller=visual, tick=lambda: None, public=lambda: {})
        life = presentation.bind_presentation(stage, recording, clock=clock)
        presentation.attach_presentation(stage)
    else:
        stage.board_business = None
        life = None
    def project_business(s, current):
        s.business_count += 1
        current['business_checked'] = True
    modules = {
        'board.interaction.ui_contract': NS(STATE_TEXT={}, display_state=lambda name, value: value or '待接入'),
        'tools.formal_native_yuki': NS(display_status=lambda box: dict(kind='native_yuki_egl', target_fps=16)),
        'tools.production_business_ui': NS(project_business_ui=project_business),
        'tools.production_memory_presentation': presentation,
    }
    def tick():
        clock.now += .2
        with patch.dict(sys.modules, modules):
            assert scope['tick'](stage) is True
        assert not stage.errors and stage.controller.cancelled == 0, stage.errors
    return stage, life, clock, tick


def admit(life, clock, *, owner=OWNER, reply='公开回答'):
    life.channel(dict(kind='start'), owner, clock.now)
    life.channel(dict(kind='transcript', text='公开问题'), owner, clock.now)
    if reply is not None: life.channel(dict(kind='text', text=reply), owner, clock.now)


def displayed(stage):
    return (stage.transcript_label.text, stage.transcript_label.tooltip,
            stage.reply_view.text, stage.reply.text, stage.reply_text)


def writes(stage):
    return (stage.transcript_label.writes, stage.transcript_label.tooltip_writes,
            stage.reply_view.writes, stage.reply.writes)


class CandidateTests(unittest.TestCase):
    def test_unchanged_idle_repeated_ticks_stop_duplicate_writes_and_keep_business(self):
        old, _, _, old_tick = fixture(BEFORE)
        new, _, _, new_tick = fixture()
        old_tick(); new_tick()
        new_count = writes(new)
        for _ in range(20): old_tick(); new_tick()
        self.assertEqual(displayed(old), displayed(new))
        self.assertEqual(writes(new), new_count)
        self.assertGreater(sum(writes(old)), sum(writes(new)))
        self.assertEqual(new.refresh_count, 21)
        self.assertEqual(new.business_count, 21)
        self.assertEqual(new.bridge.publishes, 21)
        self.assertFalse(new.controls['identity_delete'].sensitive)
        self.assertTrue(new.bridge.state['business_checked'])

    def test_pending_and_incremental_reply_match_original_final_display(self):
        old, old_life, old_clock, old_tick = fixture(BEFORE)
        new, life, clock, tick = fixture()
        for obj, lc in ((old_life, old_clock), (life, clock)): admit(obj, lc, reply=None)
        for obj in (old, new): obj.controller.state['local_transcription']['state'] = 'TRANSCRIBING'
        old_tick(); tick()
        self.assertEqual(displayed(old), displayed(new))
        self.assertEqual(displayed(new), ('公开问题', '公开问题', '', '', ''))
        for text in ('第一句。', '第二句。'):
            old_life.channel(dict(kind='text', text=text), OWNER, old_clock.now)
            life.channel(dict(kind='text', text=text), OWNER, clock.now)
            old_tick(); tick()
            self.assertEqual(displayed(old), displayed(new))
        self.assertEqual(new.reply_text, '第一句。第二句。')
        self.assertEqual(new.bridge.state['reply'], '')
        self.assertEqual(new.bridge.state['local_transcription']['text'], '')

    def test_expiry_clears_at_original_deadline_and_stale_text_cannot_return(self):
        stage, life, clock, tick = fixture(); admit(life, clock); tick()
        deadline = life.deadline
        clock.now = deadline - .3; tick()
        self.assertEqual(stage.reply_text, '公开回答')
        clock.now = deadline; tick()
        self.assertEqual(life.deadline, deadline)
        self.assertEqual(life.expirations, 1)
        self.assertEqual(displayed(stage), ('等待你的声音…', '等待你的声音…', '', '', ''))
        life.channel(dict(kind='text', text='公开过期事件'), OWNER, clock.now)
        stage.controller.state['reply'] = '公开旧副本'
        tick()
        self.assertEqual(stage.reply_text, '')

    def test_committed_forget_clear_correct_mask_slots_and_queued_stale_start(self):
        for operation in ('forget', 'clear', 'correct', 'commit_compaction'):
            with self.subTest(operation=operation):
                stage, life, clock, tick = fixture(); admit(life, clock); tick()
                requested_at = clock.now; clock.now += 1.
                result = getattr(stage.board_business.runtime.store, operation)({})
                self.assertEqual(result['result'], 'public fake commit')
                queued = dict(OWNER, request_id='public-precommit-queue')
                life.channel(dict(kind='start'), queued, requested_at)
                life.channel(dict(kind='text', text='公开旧内容'), queued, requested_at)
                tick()
                self.assertEqual(displayed(stage), ('等待你的声音…', '等待你的声音…', '', '', ''))
                self.assertEqual(stage.bridge.state['reply'], '')
                self.assertEqual(life.invalidations, 1)

    def test_failed_forget_preserves_subtitle_and_postcommit_confirmation_is_shown(self):
        stage, life, clock, tick = fixture(); admit(life, clock); tick()
        store = stage.board_business.runtime.store
        store.failure = True
        with self.assertRaises(ValueError): store.forget({})
        tick(); self.assertEqual(stage.reply_text, '公开回答')
        self.assertEqual(life.invalidations, 0)
        store.failure = False
        jobs = stage.board_business.runtime.jobs
        jobs.active = OWNER['request_id']; jobs._active_job = NS(meta=OWNER)
        store.forget({}, operation_turn_id=OWNER['request_id'])
        life.channel(dict(kind='text', text='已忘记公开测试内容。'), OWNER, 10.)
        tick()
        self.assertEqual(stage.reply_text, '已忘记公开测试内容。')
        self.assertEqual(stage.transcript_label.text, '等待你的声音…')

    def test_cancelled_generation_clears_and_new_owner_can_paint(self):
        stage, life, clock, tick = fixture(); admit(life, clock); tick()
        stage.board_business.runtime.jobs.playback_invalidator('generation_changed', OWNER)
        tick(); self.assertEqual(stage.reply_text, '')
        clock.now += 1.
        newer = dict(OWNER, generation=2, request_id='public-next')
        admit(life, clock, owner=newer, reply='公开新回答'); tick()
        self.assertEqual(stage.reply_text, '公开新回答')
        stage.reply_view.text = '公开外部覆盖'
        tick(); self.assertEqual(stage.reply_view.text, '公开新回答')

    def test_no_lifecycle_keeps_legacy_display_and_cache_updates(self):
        for state_name in ('IDLE', 'TRANSCRIBING', 'CANCELLED', 'ERROR', 'READY'):
            with self.subTest(state=state_name):
                old, _, _, old_tick = fixture(BEFORE, production=False)
                new, _, _, tick = fixture(production=False)
                for stage in (old, new):
                    stage.controller.state['local_transcription'].update(state=state_name, text='公开旧模式')
                    stage.controller.state['local_recording']['state'] = 'READY'
                    stage.controller.state['reply'] = '公开旧回复'
                old_tick(); tick()
                self.assertEqual(displayed(old), displayed(new))
                self.assertEqual(writes(old), writes(new))

    def test_native_16fps_and_unrelated_methods_are_byte_semantically_unchanged(self):
        self.assertEqual(hashlib.sha256(BEFORE.read_bytes()).hexdigest(), BEFORE_SHA)
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), LIFECYCLE_SHA)
        def stripped(path):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoardAvatarStage')
            cls.body = [n for n in cls.body if not isinstance(n, ast.FunctionDef) or n.name not in ('refresh_runtime', 'tick')]
            return ast.dump(tree, include_attributes=False)
        self.assertEqual(stripped(BEFORE), stripped(AFTER))
        self.assertIn('visual_fps=16 if self.character_pair is not None', AFTER.read_text(encoding='utf-8'))


if __name__ == '__main__': unittest.main()
