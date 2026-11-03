"""Public offline regression: execute pinned real submit/recording methods.

No device/HTTP/model/Store construction, recordings, photos or real identities.
The jobs worker is never started. All clip bytes and text are authored here.
"""
import __future__
import ast
from collections import deque
import copy
from dataclasses import dataclass, field
import hashlib
import importlib.util
import json
from pathlib import Path
import queue as public_queue
import sys
import threading
import types
from types import SimpleNamespace as NS
import unittest
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / 'SOURCE_PINS.json').read_text(encoding='utf-8'))
RELATIVE = 'tools/production_memory_presentation.py'
BEFORE_SHA = '984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502'
AFTER_SHA = 'de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2'
TRANSCRIPT = 'public authored transcript'
REPLY = 'public authored answer'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def source(component):
    pin = PINS['files'][component]
    data = (HERE / pin['public_fixture']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == pin['sha256']
    return data.decode('utf-8')


BEFORE = load('subtitle_before', HERE / 'before' / RELATIVE)
AFTER = load('subtitle_after', HERE / 'after' / RELATIVE)


class PublicClock:
    def __init__(self):
        self.now = 100.
    def monotonic(self):
        result = self.now
        self.now += .0001
        return result
    def __call__(self):
        return self.now
    def perf_counter(self):
        return self.now


def pinned_methods(clock):
    """Use actual method ASTs, not a hand-written reproduction of the order."""
    module = types.ModuleType('authored_public_fixture_' + uuid.uuid4().hex)
    ns = module.__dict__
    ns.update(threading=threading, queue=public_queue,
              dataclass=dataclass, field=field, copy=copy, uuid=uuid, hashlib=hashlib,
              ASR_PROTOCOL='authored-public-asr',
              time=NS(monotonic=clock.monotonic, perf_counter=clock.perf_counter))
    def execute(code):
        # dataclasses resolves deferred ClassVar/InitVar names via sys.modules.
        # Register only this unique public fixture during execution, then clean.
        assert module.__name__ not in sys.modules
        sys.modules[module.__name__] = module
        try:
            exec(code, ns)
        finally:
            sys.modules.pop(module.__name__, None)
    def validate_capture(meta, pcm):
        if pcm != b'\x00\x00' * 16:
            raise ValueError('authored public invalid clip')
    ns['validate_capture'] = validate_capture
    jobs_tree = ast.parse(source('board/runtime/audio/board_dialogue_jobs.py'))
    job = next(n for n in jobs_tree.body if isinstance(n, ast.ClassDef) and n.name == '_Job')
    cls = next(n for n in jobs_tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoardDialogueJobs')
    names = {'enabled', '_current', '_invalidate_presentation', '_queue_action',
             '_queue_cancel', '_invalidate', 'cancel', 'submit', 'poll'}
    cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    execute(compile(ast.fix_missing_locations(ast.Module(body=[job, cls], type_ignores=[])),
                    'pinned_public_jobs_methods', 'exec',
                    flags=__future__.annotations.compiler_flag, dont_inherit=True))
    recording_tree = ast.parse(source('tools/board_recording.py'))
    rec = next(n for n in recording_tree.body if isinstance(n, ast.ClassDef) and n.name == 'RecordingController')
    names = {'_reset_stream_diagnostics', '_empty_transcription', '_queue_transcription', '_poll_transcription'}
    rec.body = [n for n in rec.body if isinstance(n, ast.FunctionDef) and n.name in names]
    execute(compile(ast.fix_missing_locations(ast.Module(body=[rec], type_ignores=[])),
                    'pinned_public_recording_methods', 'exec',
                    flags=__future__.annotations.compiler_flag, dont_inherit=True))
    return ns['BoardDialogueJobs'], ns['RecordingController']


class PublicWidget:
    def __init__(self):
        self.value = self.tooltip = ''
    def get_text(self, *args):
        return self.value
    def set_text(self, value):
        self.value = value
    def get_tooltip_text(self):
        return self.tooltip
    def set_tooltip_text(self, value):
        self.tooltip = value
    def get_buffer(self):
        return self
    def get_bounds(self):
        return (0, len(self.value))


class PublicStore:
    def __init__(self):
        self.fail = False
        self.committed = True
    def operation(self, *args, **kwargs):
        if self.fail:
            raise ValueError('authored public failed transaction')
        return dict(committed=self.committed)
    correct = forget = clear = commit_compaction = operation


def public_state():
    return dict(reply=REPLY, local_transcription=dict(text=TRANSCRIPT,
        voice_reply=dict(reply_text=REPLY)), messages=[dict(content=REPLY)],
        numbers=dict(draws=12))


def fixture(mod=AFTER, *, after_real_submit=None, replacement_submit=None):
    clock = PublicClock()
    Jobs, Recording = pinned_methods(clock)
    jobs = Jobs()
    jobs.condition = threading.Condition(threading.RLock())
    jobs.config = dict(enabled=True, timeout_ms=30000)
    jobs.boot_id, jobs.session_id, jobs.generation = 'public-boot', 'public-session', 0
    jobs.waiting = jobs.active = jobs._active_job = jobs._playback = None
    jobs._stream_clock = None
    jobs.progress = deque()
    jobs.closed, jobs.cleanup_error = False, ''
    jobs.playback_invalidator = None
    jobs._actions = public_queue.Queue(maxsize=16)
    jobs._cancel_queued = set()
    jobs.profile_selection = jobs.conversation_selection = None
    jobs.capture_owners = {}
    jobs.wake_entry_capture = jobs.visual_entry_capture = None
    jobs.feedback_assets = {}
    jobs._scope = lambda meta: dict(kind='conversation', id='public-conversation')
    jobs.clock = clock
    submitted = []
    real_submit = jobs.submit
    def submit(clip):
        result = replacement_submit(clip) if replacement_submit else real_submit(clip)
        submitted.append(result)
        if after_real_submit:
            after_real_submit(result, jobs)
        return result
    jobs.submit = submit
    visual = NS(stream=None, channel_complete=lambda *args: None)
    original_results = []
    def original_event(header, pcm, owner, feedback_assets, requested_at):
        if header['kind'] == 'start':
            visual.stream = {'owner': owner}
        result = object()
        original_results.append(result)
        return result
    visual.channel_event = original_event
    recording = Recording()
    recording.controller, recording.transcriber = visual, jobs
    recording.tick, recording.public = lambda: 'tick-result', public_state
    recording.closed = False
    recording.utterance = NS(capture_id='public-capture', audio=NS(sample_count=16), pcm=b'\x00\x00' * 16)
    store = PublicStore()
    bridge = NS(lock=threading.Lock(), state=public_state(), frame=None)
    def publish(state, frame):
        with bridge.lock:
            bridge.state, bridge.frame = state, frame
    bridge.publish = publish
    runtime = NS(config=NS(data_origin='board'), jobs=jobs, store=store,
                 _foreground_idle=lambda: False)
    stage = NS(board_business=NS(runtime=runtime), bridge=bridge, closed=False,
               runtime_view=public_state(), controller=NS(read=lambda: dict(state=public_state())),
               services=NS(read=public_state), transcript_label=PublicWidget(),
               reply_view=PublicWidget(), reply=PublicWidget())
    life = mod.bind_presentation(stage, recording, clock=clock)
    mod.attach_presentation(stage)
    return NS(mod=mod, clock=clock, jobs=jobs, recording=recording, life=life,
              stage=stage, store=store, visual=visual, submitted=submitted,
              original_results=original_results, original_submit=real_submit)


def queue(f):
    f.recording._queue_transcription()
    return dict(f.jobs.waiting.meta) if f.jobs.waiting else None


def emit(f, owner, *, requested_at=None):
    requested = f.recording.requested_at if requested_at is None else requested_at
    for header in [dict(kind='start'), dict(kind='transcript', text=TRANSCRIPT),
                   dict(kind='text', text=REPLY)]:
        f.visual.channel_event(header, b'', owner, {}, requested)
    f.mod.project_presentation(f.stage, public_state())


def drain(f, owner):
    for header in [dict(kind='start'), dict(kind='transcript', text=TRANSCRIPT),
                   dict(kind='text', text=REPLY)]:
        f.jobs.progress.append(dict(context=owner, channel_event=header))
    f.recording._poll_transcription()
    f.mod.project_presentation(f.stage, public_state())


class SubmitLifecycleTests(unittest.TestCase):
    def test_real_union_annotations_are_deferred_and_fixture_module_is_cleaned(self):
        before = set(sys.modules)
        Jobs, Recording = pinned_methods(PublicClock())
        ns = Jobs.submit.__globals__
        annotation = ns['_Job'].__annotations__['entry']
        self.assertIsInstance(annotation, str)
        self.assertEqual(annotation.replace(' ', ''), 'str|None')
        self.assertIs(Recording._queue_transcription.__globals__, ns)
        self.assertNotIn(ns['__name__'], sys.modules)
        self.assertEqual(set(sys.modules) - before, set())

    def assert_blank(self, f):
        self.assertIsNone(f.life.current)
        self.assertEqual((f.life.transcript, f.life.reply), ('', ''))
        f.mod.project_presentation(f.stage, public_state())
        self.assertEqual(f.stage.transcript_label.value, '等待你的声音…')
        self.assertEqual(f.stage.reply_view.value, '')

    def assert_visible(self, f):
        self.assertEqual((f.life.transcript, f.life.reply), (TRANSCRIPT, REPLY))
        self.assertEqual(f.stage.transcript_label.value, TRANSCRIPT)
        self.assertEqual(f.stage.reply_view.value, REPLY)
        self.assertEqual(f.stage.reply.value, REPLY)

    def test_real_recording_submit_invalidate_poll_reproduces_both_missing_before(self):
        result = {}
        for label, mod in [('before', BEFORE), ('after', AFTER)]:
            f = fixture(mod)
            owner = queue(f)
            self.assertEqual(f.recording.transcription['state'], 'TRANSCRIBING')
            self.assertLess(f.recording.requested_at, f.life.invalidated_at)
            self.assertEqual(f.life.invalidations, 1)
            drain(f, owner)
            result[label] = dict(transcript_chars=len(f.life.transcript), reply_chars=len(f.life.reply),
                                 requested_at=f.recording.requested_at, invalidated_at=f.life.invalidated_at)
            self.assert_blank(f) if label == 'before' else self.assert_visible(f)
        self.assertEqual(result['before']['transcript_chars'], 0)
        self.assertGreater(result['after']['transcript_chars'], 0)
        (HERE / 'REPRODUCTION.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')

    def test_cancel_after_submit_rejects_delayed_start(self):
        f = fixture(); owner = queue(f)
        f.jobs.cancel(); emit(f, owner)
        self.assert_blank(f)
        self.assertIsNone(f.life.start_permit)

    def test_store_commit_after_submit_rejects_delayed_start(self):
        for name in ['correct', 'forget', 'clear', 'commit_compaction', 'history_delete']:
            with self.subTest(operation=name):
                f = fixture(); owner = queue(f)
                if name == 'history_delete':
                    f.store.notify_history_delete_committed(operation_turn_id=None)
                else:
                    getattr(f.store, name)()
                emit(f, owner)
                self.assert_blank(f)
                self.assertIsNone(f.life.start_permit)

    def test_store_commit_between_real_submit_return_and_receipt_cannot_reauthorize(self):
        for name in ['correct', 'forget', 'clear', 'commit_compaction']:
            box = {}
            def interleave(result, jobs):
                getattr(box['f'].store, name)()
            f = fixture(after_real_submit=interleave); box['f'] = f
            owner = queue(f); emit(f, owner)
            self.assert_blank(f)
            self.assertEqual(f.life.invalidations, 2)
            self.assertIsNone(f.life.start_permit)

    def test_concurrent_store_commit_before_receipt_is_not_revived(self):
        entered, release = threading.Event(), threading.Event()
        def interleave(result, jobs):
            entered.set()
            if not release.wait(2):
                raise TimeoutError('authored public interleave timeout')
        f = fixture(after_real_submit=interleave)
        submitter = threading.Thread(target=f.recording._queue_transcription, daemon=True)
        submitter.start()
        try:
            self.assertTrue(entered.wait(2))
            f.store.forget()
        finally:
            release.set()
        submitter.join(2)
        self.assertFalse(submitter.is_alive())
        emit(f, dict(f.jobs.waiting.meta))
        self.assert_blank(f)
        self.assertIsNone(f.life.start_permit)

    def test_concurrent_cancel_after_receipt_serializes_then_invalidates(self):
        entered, release, attempted, cancelled = [threading.Event() for _ in range(4)]
        def interleave(result, jobs):
            entered.set()
            if not release.wait(2):
                raise TimeoutError('authored public interleave timeout')
        f = fixture(after_real_submit=interleave)
        def cancel():
            attempted.set(); f.jobs.cancel(); cancelled.set()
        submitter = threading.Thread(target=f.recording._queue_transcription, daemon=True)
        canceller = threading.Thread(target=cancel, daemon=True)
        submitter.start()
        self.assertTrue(entered.wait(2))
        owner = dict(f.jobs.waiting.meta)
        canceller.start()
        try:
            self.assertTrue(attempted.wait(2))
            self.assertFalse(cancelled.is_set())
        finally:
            release.set()
        submitter.join(2); canceller.join(2)
        self.assertFalse(submitter.is_alive() or canceller.is_alive())
        emit(f, owner); self.assert_blank(f)
        self.assertIsNone(f.life.start_permit)

    def test_submit_failure_preserves_exception_and_creates_no_permit(self):
        failure = ValueError('authored public submit failure')
        def fail(clip):
            raise failure
        f = fixture(replacement_submit=fail)
        with self.assertRaises(ValueError) as caught:
            f.jobs.submit(f.recording.utterance)
        self.assertIs(caught.exception, failure)
        self.assertIsNone(f.life.start_permit)
        f = fixture(); f.recording.utterance.pcm = b'authored-public-invalid'
        self.assertIsNone(queue(f))
        self.assertEqual(f.recording.transcription['state'], 'ERROR')
        self.assertIsNone(f.life.start_permit)
        self.assertEqual(f.life.invalidations, 1)

    def test_submit_result_identity_and_original_event_return_are_preserved(self):
        f = fixture()
        result = f.jobs.submit(f.recording.utterance)
        self.assertIs(result, f.submitted[-1])
        event_result = f.visual.channel_event(dict(kind='start'), b'', result, {}, 99.)
        self.assertIs(event_result, f.original_results[-1])

    def test_new_submit_replaces_single_owner_permit_and_stale_owner_is_rejected(self):
        f = fixture(); old = queue(f); old_time = f.recording.requested_at
        f.clock.now += 1
        f.recording.utterance.capture_id = 'public-capture-two'
        new = queue(f)
        self.assertEqual(f.life.start_permit, (AFTER._owner(new), f.life.epoch))
        emit(f, old, requested_at=old_time); self.assert_blank(f)
        emit(f, new); self.assert_visible(f)
        self.assertIsNone(f.life.start_permit)

    def test_permit_binds_all_owner_fields_and_current_epoch(self):
        for key in ['board_boot_id', 'session_id', 'generation', 'request_id']:
            f = fixture(); owner = queue(f); bad = dict(owner)
            bad[key] = owner[key] + 1 if key == 'generation' else 'wrong-public-owner'
            emit(f, bad); self.assert_blank(f)
            emit(f, owner); self.assert_visible(f)
        f = fixture(); owner = queue(f)
        f.life.epoch += 1
        emit(f, owner); self.assert_blank(f)

    def test_submit_receipt_requires_waiting_job_current_owner_and_generation(self):
        for mutate in [lambda result, jobs: setattr(jobs, 'generation', jobs.generation + 1),
                       lambda result, jobs: jobs.waiting.cancelled.set(),
                       lambda result, jobs: setattr(jobs, 'waiting', None),
                       lambda result, jobs: result.update(request_id='public-wrong-receipt')]:
            f = fixture(after_real_submit=mutate)
            f.recording._queue_transcription()
            self.assertIsNone(f.life.start_permit)

    def test_original_request_deadline_remains_hard_across_delayed_start_and_repaint(self):
        f = fixture(); owner = queue(f); requested = f.recording.requested_at
        f.clock.now = requested + 250
        emit(f, owner); self.assert_visible(f)
        self.assertEqual(f.life.deadline, requested + 300)
        for now in [requested + 299.9, requested + 299.99]:
            f.clock.now = now
            f.mod.project_presentation(f.stage, public_state())
            f.stage.bridge.publish(public_state(), b'authored-public-frame')
            self.assertEqual(f.life.deadline, requested + 300)
        f.clock.now = requested + 300
        f.mod.project_presentation(f.stage, public_state()); self.assert_blank(f)
        emit(f, owner, requested_at=f.clock.now)
        self.assert_blank(f)

    def test_start_after_original_five_minute_deadline_never_shows_bodies(self):
        f = fixture(); owner = queue(f)
        f.clock.now = f.recording.requested_at + 300.1
        emit(f, owner); self.assert_blank(f)
        self.assertLessEqual(f.life.deadline, f.recording.requested_at + 300)

    def test_failed_store_and_uncommitted_compaction_do_not_erase_valid_current_turn(self):
        for name in ['correct', 'forget', 'clear', 'commit_compaction']:
            f = fixture(); owner = queue(f)
            f.store.fail = True
            with self.assertRaises(ValueError):
                getattr(f.store, name)()
            emit(f, owner); self.assert_visible(f)
        f = fixture(); owner = queue(f); f.store.committed = False
        f.store.commit_compaction(); emit(f, owner); self.assert_visible(f)

    def test_current_committed_command_keeps_confirmation_only_exception(self):
        f = fixture(); owner = queue(f)
        f.jobs._active_job, f.jobs.active = f.jobs.waiting, owner['request_id']
        f.store.forget(operation_turn_id=owner['request_id'])
        emit(f, owner)
        self.assertEqual(f.life.transcript, '')
        self.assertEqual(f.life.reply, REPLY)
        self.assertEqual(f.stage.reply_view.value, REPLY)

    def test_api_worker_service_and_old_publication_paths_keep_expected_privacy(self):
        f = fixture(); owner = queue(f); drain(f, owner)
        self.assert_visible(f)
        self.assertEqual(f.stage.controller.read()['state']['reply'], REPLY)
        self.assertNotIn(TRANSCRIPT, json.dumps(f.stage.services.read()))
        f.stage.bridge.publish(public_state(), b'authored-public-frame')
        api = json.dumps(f.stage.bridge.state)
        self.assertNotIn(TRANSCRIPT, api); self.assertNotIn(REPLY, api)
        self.assertTrue(f.stage.bridge.state['presentation_lifecycle']['showing'])
        f.store.clear()
        f.stage.bridge.publish(public_state(), b'authored-public-stale')
        self.assertNotIn(TRANSCRIPT, json.dumps(f.stage.bridge.state))
        self.assertNotIn(REPLY, json.dumps(f.stage.bridge.state))
        self.assertFalse(f.stage.bridge.state['presentation_lifecycle']['showing'])
        self.assert_blank(f)

    def test_close_clears_unused_permit_and_rejects_late_start(self):
        f = fixture(); owner = queue(f)
        f.mod.close_presentation(f.stage)
        emit(f, owner); self.assert_blank(f)
        self.assertIsNone(f.life.start_permit)

    def test_binding_is_instance_local_and_second_bind_is_rejected(self):
        first, second = fixture(), fixture()
        first_owner = queue(first)
        self.assertIsNone(second.life.start_permit)
        self.assertIsNone(second.jobs.waiting)
        with self.assertRaises(RuntimeError):
            AFTER.bind_presentation(first.stage, first.recording)
        emit(first, first_owner); self.assert_visible(first)


def main():
    assert hashlib.sha256((HERE/'before'/RELATIVE).read_bytes()).hexdigest() == BEFORE_SHA
    assert hashlib.sha256((HERE/'after'/RELATIVE).read_bytes()).hexdigest() == AFTER_SHA
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SubmitLifecycleTests))
    report = dict(schema='aura-public-subtitle-real-submit-regression-1',
        tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        passed=result.wasSuccessful(), before_sha256=BEFORE_SHA, after_sha256=AFTER_SHA,
        actual_pinned_methods=['RecordingController._queue_transcription', 'RecordingController._poll_transcription',
            'BoardDialogueJobs.submit', 'BoardDialogueJobs._invalidate', 'BoardDialogueJobs.poll'],
        public_fixture_only=True, real_store_or_device_constructed=False,
        network_model_private_data_access=False, source_files_modified=False)
    (HERE/'TEST_RESULT.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
