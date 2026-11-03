"""Pure fake-stage/clock contracts: no GUI, DB, socket, model or devices."""
import ast
import copy
import importlib.util
import json
import gc
from pathlib import Path
import queue
import sys
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
import weakref

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT/'aura'))
sys.path.insert(0, str(HERE))
from tools import production_memory_presentation as presentation
import build_patch

SECRET = 'private-asr-and-reply-sentinel'
OWNER = dict(board_boot_id='boot', session_id='session', generation=1, request_id='request')


class Clock:
    value = 10.
    def __call__(self): return self.value


class Label:
    def __init__(self): self.text = self.tooltip = SECRET
    def set_text(self, text): self.text = text
    def set_tooltip_text(self, text): self.tooltip = text
    def get_buffer(self): return self


class Bridge:
    def __init__(self): self.lock = threading.Lock(); self.state = {'reply': SECRET}
    def publish(self, state, frame):
        with self.lock: self.state = copy.deepcopy(state)


class Worker:
    def __init__(self):
        self.condition = threading.Condition()
        self.packet = {'state': {'reply': SECRET}, 'jpeg': b'public-portrait'}
        self.cancelled = 0
    def read(self):
        with self.condition: return copy.deepcopy(self.packet)
    def cancel(self): self.cancelled += 1
    def close(self): pass


class Store:
    def __init__(self): self.failure = False; self.committed = True; self.calls = 0
    def operation(self, *args, **kwargs):
        self.calls += 1
        if self.failure: raise ValueError('synthetic rollback')
        return {'unchanged_return': True}
    correct = forget = clear = operation
    def commit_compaction(self, *args, **kwargs): return {'committed': self.committed}


class Visual:
    def __init__(self):
        self.stream = self.pending = self.ready = self.audio_waiting = None
        self.core = NS(reply_text=SECRET)
        self.output = NS(active=False, paused=False)
        self.phase = 'IDLE'
        self.reply = SECRET; self.turns = [{'text': SECRET}]; self.log = [{'text': SECRET}]
        self.events = []
    def channel_event(self, header, pcm, owner, feedback_assets, requested_at):
        self.events.append((header['kind'], pcm))
        if header['kind'] == 'start': self.stream = {'owner': owner}


class Recording:
    def __init__(self):
        self.controller = Visual()
        self.transcription = dict(state='ANSWERED', text=SECRET, request_id='request', capture_id='capture', voice_reply={'reply_text': SECRET})
        self.utterance = self._public_utterance = object()
        self._public_metadata = {'text': SECRET}
        self.ticks = 0
    def tick(self): self.ticks += 1; return 'original-tick-result'
    def public(self):
        return dict(reply=self.controller.reply, turns=copy.deepcopy(self.controller.turns),
                    log=copy.deepcopy(self.controller.log), local_transcription=dict(self.transcription),
                    error=SECRET, phase=self.controller.phase)


def fixture(directory):
    clock, recording = Clock(), Recording()
    idle = NS(value=True)
    runtime = NS(config=NS(data_origin='board', private_root=directory), store=Store(),
                 jobs=NS(playback_invalidator=None),
                 _foreground_idle=lambda: idle.value)
    glib_queue = []
    stage = NS(board_business=NS(runtime=runtime), controller=Worker(), bridge=Bridge(),
               transcript_label=Label(), reply_view=Label(), reply=Label(), reply_text=SECRET,
               runtime_view={'snapshot': {'modules': {'interaction': {'transcript': SECRET, 'reply': SECRET}}}},
               services=NS(read=lambda: {'snapshot': {'modules': {'interaction': {'reply': SECRET}}}}),
               GLib=NS(idle_add=lambda fn: glib_queue.append(fn)), closed=False)
    lifecycle = presentation.bind_presentation(stage, recording, clock=clock)
    presentation.attach_presentation(stage)
    return stage, recording, lifecycle, clock, idle, glib_queue


def admit(recording, clock, owner=OWNER):
    visual = recording.controller
    for header in ({'kind': 'start'}, {'kind': 'transcript', 'text': SECRET}, {'kind': 'text', 'text': SECRET}):
        visual.channel_event(header, b'pcm-pass-through', owner, {}, clock())


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stage, self.rec, self.life, self.clock, self.idle, self.glib = fixture(self.tmp.name)
        admit(self.rec, self.clock)
    def tearDown(self): self.tmp.cleanup()

    def test_expiry_is_admission_based_and_cannot_repaint_renew_or_revive(self):
        self.clock.value = 309.9
        self.assertEqual(self.rec.public()['reply'], SECRET)
        presentation.project_presentation(self.stage, self.rec.public())
        self.clock.value = 310.
        for _ in range(2):
            projected = presentation.project_presentation(self.stage, {'reply': SECRET})
            self.assertEqual(projected['reply'], '')
            self.assertEqual(self.stage.reply_view.text, '')
        self.rec.controller.channel_event({'kind': 'text', 'text': SECRET}, b'', OWNER, {}, 10.)
        self.assertEqual(self.rec.public()['reply'], '')
        self.assertEqual(self.life.expirations, 1)

    def test_active_generation_playback_and_pending_ack_keep_required_buffers(self):
        self.idle.value = False
        self.rec.controller.output.active = True
        original = self.rec.utterance
        self.clock.value = 400.
        self.assertEqual(self.rec.tick(), 'original-tick-result')
        self.assertEqual(self.rec.controller.reply, SECRET)
        self.assertEqual(self.rec.controller.core.reply_text, SECRET)
        self.assertIs(self.rec.utterance, original)
        self.assertEqual(self.rec.public()['reply'], '')
        self.assertEqual(self.rec.controller.events[0][1], b'pcm-pass-through')

    def test_paused_playback_remains_even_if_business_gate_accidentally_idle(self):
        self.rec.controller.stream = None
        self.rec.controller.output.paused = True
        self.rec.tick()
        self.assertEqual(self.rec.controller.reply, SECRET)

    def test_retire_after_canonical_commit_and_all_ack_actions(self):
        self.rec.controller.stream = None
        self.idle.value = False
        self.rec.tick()
        self.assertEqual(self.rec.controller.turns[0]['text'], SECRET)
        self.idle.value = True
        self.rec.tick()
        self.assertEqual(self.rec.controller.turns, [])
        self.assertEqual(self.rec.controller.log, [])
        self.assertEqual(self.rec.controller.reply, '')
        self.assertEqual(self.rec.controller.core.reply_text, '')
        self.assertIsNone(self.rec.utterance)
        self.assertEqual(self.rec.transcription['request_id'], 'request')
        self.assertEqual(self.rec.transcription['capture_id'], 'capture')
        self.assertEqual(self.rec.public()['reply'], SECRET)  # one bounded display slot

    def test_unsubmitted_manual_recording_is_not_discarded(self):
        self.rec.controller.stream = None
        self.rec.transcription['state'] = 'IDLE'
        original = self.rec.utterance
        self.rec.tick()
        self.assertIs(self.rec.utterance, original)

    def test_forget_invalidates_ui_worker_bridge_and_blocks_stale_stream(self):
        result = self.stage.board_business.runtime.store.forget({'kind': 'device'})
        self.assertEqual(result, {'unchanged_return': True})
        self.assertEqual(self.stage.bridge.state['reply'], '')
        self.assertEqual(self.stage.controller.read()['state']['reply'], '')
        for fn in self.glib: fn()
        self.assertEqual(self.stage.reply_view.text, '')
        self.rec.controller.channel_event({'kind': 'text', 'text': SECRET}, b'', OWNER, {}, 10.)
        self.assertEqual(self.rec.public()['reply'], '')
        self.assertEqual(self.rec.controller.reply, SECRET)  # no active audio mutation
        newer = dict(OWNER, request_id='new', generation=2)
        self.clock.value += 1.
        admit(self.rec, self.clock, newer)
        self.assertEqual(self.rec.public()['reply'], SECRET)

    def test_precommit_queued_start_cannot_create_fresh_epoch(self):
        self.clock.value = 11.
        self.stage.board_business.runtime.store.clear({})
        queued = dict(OWNER, request_id='queued-before-clear')
        for event in ({'kind': 'start'}, {'kind': 'transcript', 'text': SECRET}, {'kind': 'text', 'text': SECRET}):
            self.rec.controller.channel_event(event, b'', queued, {}, 10.5)
        self.assertEqual(self.rec.public()['reply'], '')
        self.assertEqual(self.rec.public()['local_transcription']['text'], '')

    def test_cancel_invalidates_without_audio_action_and_token_publication_does_not(self):
        hook = self.stage.board_business.runtime.jobs.playback_invalidator
        hook('playback_token_changed', OWNER)
        self.assertEqual(self.rec.public()['reply'], SECRET)
        hook('playback_cancelled', OWNER)
        self.assertEqual(self.rec.public()['reply'], '')
        self.assertEqual(self.rec.controller.reply, SECRET)

    def test_invalidation_never_takes_worker_condition_inverted_by_public(self):
        class ForbiddenCondition:
            def __enter__(self): raise AssertionError('worker condition acquired from presenter')
            def __exit__(self, *args): pass
        self.stage.controller.condition = ForbiddenCondition()
        self.stage.board_business.runtime.store.forget({})
        self.assertEqual(self.rec.public()['reply'], '')
        self.assertEqual(self.stage.bridge.state['reply'], '')

    def test_failed_transaction_and_uncommitted_compaction_do_not_invalidate(self):
        store = self.stage.board_business.runtime.store
        store.failure = True
        with self.assertRaises(ValueError): store.correct({}, 'key', 'value')
        self.assertEqual(self.rec.public()['reply'], SECRET)
        store.committed = False
        self.assertEqual(store.commit_compaction('', '', {})['committed'], False)
        self.assertEqual(self.rec.public()['reply'], SECRET)
        store.committed = True
        store.commit_compaction('', '', {})
        self.assertEqual(self.rec.public()['reply'], '')

    def test_bridge_never_exposes_subtitles_and_read_masks_stale_packet(self):
        self.stage.bridge.publish(self.rec.public(), b'public-portrait')
        self.assertNotIn(SECRET, json.dumps(self.stage.bridge.state))
        self.assertNotIn(SECRET, json.dumps(self.stage.services.read()))
        self.stage.controller.packet['state'] = {'reply': 'stale-raw', 'log': [{'text': 'stale-raw'}]}
        self.clock.value = 310.
        self.assertNotIn('stale-raw', json.dumps(self.stage.controller.read()['state']))

    def test_manual_evidence_is_single_metadata_file_without_text_or_images(self):
        first = presentation.save_production_evidence(self.stage)
        presentation.save_production_evidence(self.stage)
        self.assertTrue(first['metadata_only'])
        files = [p for p in Path(self.tmp.name).rglob('*') if p.is_file()]
        self.assertEqual([p.name for p in files], ['latest_metadata.json'])
        raw = files[0].read_text()
        self.assertNotIn(SECRET, raw)
        payload = json.loads(raw)
        self.assertFalse(payload['images_saved'])
        self.assertFalse(payload['body_saved'])

    def test_real_patched_save_and_close_never_reach_legacy_archive(self):
        source = (build_patch.DEFAULT_CANDIDATE/'tools/board_avatar_gtk.py').read_text(encoding='utf-8')
        tree = ast.parse(build_patch.gtk_patch(source))
        methods = []
        for item in tree.body:
            if isinstance(item, ast.ClassDef):
                methods += [fn for fn in item.body if isinstance(fn, ast.FunctionDef) and fn.name in ('save_evidence', 'close')]
        self.assertEqual(len(methods), 2)
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])), '<patched-methods>', 'exec'), namespace)
        stage = self.stage
        stage.config = {'handsfree_dialogue': False}
        stage.timer = stage.foreground_timer = None
        stage.close_identity_face_dialog = lambda: None
        stage.cleanup = lambda: presentation.close_presentation(stage)
        stage.window = NS(destroy=lambda: None)
        stage.Gtk = NS(main_quit=lambda: None)
        stage.save_evidence = lambda: namespace['save_evidence'](stage)
        self.assertTrue(stage.save_evidence()['metadata_only'])
        self.assertTrue(namespace['close'](stage))
        self.assertTrue(stage.closed)
        self.assertEqual(stage.controller.cancelled, 1)
        files = [p for p in Path(self.tmp.name).rglob('*') if p.is_file()]
        self.assertEqual([p.name for p in files], ['latest_metadata.json'])
        self.assertNotIn(SECRET, files[0].read_text())

    def test_nonproduction_evidence_path_unchanged_and_bad_ttl_rejected(self):
        self.stage.board_business.runtime.config.data_origin = 'synthetic'
        self.assertIsNone(presentation.save_production_evidence(self.stage))
        with self.assertRaises(ValueError): presentation.PresentationLifecycle(self.stage, self.rec, ttl=301)

    def test_builder_seams_fail_closed_and_python39_parse(self):
        for name, transform in ((build_patch.FILES[0], build_patch.gtk_patch), (build_patch.FILES[1], build_patch.jobs_patch)):
            text = (build_patch.DEFAULT_CANDIDATE/name).read_text(encoding='utf-8')
            result = transform(text)
            ast.parse(result, feature_version=(3, 9))
            with self.assertRaises(ValueError): transform(result)

    def test_actual_action_worker_drops_consumed_plan_while_idle(self):
        source = (build_patch.DEFAULT_CANDIDATE/build_patch.FILES[1]).read_text(encoding='utf-8')
        tree = ast.parse(build_patch.jobs_patch(source))
        methods = [fn for cls in tree.body if isinstance(cls, ast.ClassDef) for fn in cls.body
                   if isinstance(fn, ast.FunctionDef) and fn.name == '_action_worker']
        namespace = {'queue': queue}
        exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])), '<actual-worker>', 'exec'), namespace)
        waiting = threading.Event()
        class ObservedQueue(queue.Queue):
            def get(self, *args, **kwargs):
                if self.empty(): waiting.set()
                return super().get(*args, **kwargs)
        class Plan: pass
        plan = Plan(); plan.text = SECRET
        ref = weakref.ref(plan)
        actions = ObservedQueue(); actions.put(('ack', plan)); del plan
        jobs = NS(_actions=actions, closed=False, _perform_action=lambda value: None)
        thread = threading.Thread(target=namespace['_action_worker'], args=(jobs,))
        thread.start()
        try:
            self.assertTrue(waiting.wait(1.))
            gc.collect()
            self.assertIsNone(ref())
        finally:
            jobs.closed = True
            thread.join(1.)
        self.assertFalse(thread.is_alive())


if __name__ == '__main__': unittest.main()
