"""Additional public regression paths, never construct a Store or service."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RELATIVE = Path('tools/production_memory_presentation.py')
PINS = {'baseline': '414ed67c68ad5f6ad3e0f89608e4f7ccef71d7b8765dfffc4f071eb806cc081a',
        'presentation_candidate': '984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502'}
BODY = 'authored-public-only-body'
OWNER = dict(board_boot_id='public-boot', session_id='public-session', generation=1, request_id='public-request')


def load(label, path):
    spec = importlib.util.spec_from_file_location(label, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


for folder, expected in PINS.items():
    assert hashlib.sha256((ROOT / folder / RELATIVE).read_bytes()).hexdigest() == expected
OLD = load('review_baseline', ROOT / 'baseline' / RELATIVE)
NEW = load('review_candidate', ROOT / 'presentation_candidate' / RELATIVE)


def state():
    return dict(reply=BODY, local_transcription=dict(text=BODY, voice_reply=dict(reply_text=BODY)),
                extra=dict(error={'secret': BODY}, messages=[BODY], opaque_number=17))


class PublicStore:
    def __init__(self):
        self.fail = False
        self.committed = True
    def operation(self, *args, **kwargs):
        if self.fail:
            raise ValueError('authored public failure')
        return {'committed': self.committed}
    correct = forget = clear = commit_compaction = operation


def setup(mod, lifecycle_type=None):
    clock = NS(now=10.)
    bridge = NS(lock=threading.Lock(), state=state(), frame=b'public-frame', published=0)
    def publish(value, frame):
        with bridge.lock:
            bridge.state, bridge.frame = dict(value), frame
            bridge.published += 1
    bridge.publish = publish
    jobs = NS(condition=threading.RLock(), active=OWNER['request_id'],
              _active_job=NS(meta=OWNER), _current=lambda job: True, playback_invalidator=None)
    store = PublicStore()
    runtime = NS(config=NS(data_origin='board'), jobs=jobs, store=store, _foreground_idle=lambda: False)
    stage = NS(bridge=bridge, runtime_view=state(), board_business=NS(runtime=runtime),
               controller=NS(read=lambda: dict(state=state())), closed=False)
    visual = NS(channel_event=lambda *args: None, stream={'owner': OWNER})
    recording = NS(controller=visual, tick=lambda: True, public=state)
    if lifecycle_type is None:
        life = mod.bind_presentation(stage, recording, clock=lambda: clock.now)
    else:
        life = lifecycle_type(stage, recording, clock=lambda: clock.now)
        stage.production_presentation = life
    mod.attach_presentation(stage)
    for header in [dict(kind='start'), dict(kind='transcript', text=BODY), dict(kind='text', text=BODY)]:
        life.channel(header, OWNER, clock.now)
    return life, clock, stage, store, jobs


class LifecyclePathTests(unittest.TestCase):
    def test_original_store_success_failure_and_history_commit_paths(self):
        for operation in ['correct', 'forget', 'clear', 'commit_compaction', 'history_delete']:
            outputs = []
            for mod in [OLD, NEW]:
                life, clock, stage, store, jobs = setup(mod)
                if operation == 'history_delete':
                    store.notify_history_delete_committed(operation_turn_id=OWNER['request_id'])
                else:
                    getattr(store, operation)(operation_turn_id=OWNER['request_id'])
                self.assertEqual(life.invalidations, 1)
                self.assertNotIn(BODY, json.dumps(stage.bridge.state))
                outputs.append((stage.bridge.state, life.confirmation_owner))
            self.assertEqual(*outputs, operation)
        for mod in [OLD, NEW]:
            life, clock, stage, store, jobs = setup(mod)
            store.committed = False
            store.commit_compaction()
            self.assertEqual(life.invalidations, 0)
            store.fail = True
            for name in ['correct', 'forget', 'clear', 'commit_compaction']:
                with self.assertRaises(ValueError):
                    getattr(store, name)()
            self.assertEqual(life.invalidations, 0)
            self.assertEqual(life.reply, BODY)

    def test_playback_invalidation_and_close_keep_late_publish_metadata_only(self):
        for reason in ['playback_cancelled', 'generation_changed', 'stream_failed', 'token_published', 'close']:
            outputs = []
            for mod in [OLD, NEW]:
                life, clock, stage, store, jobs = setup(mod)
                if reason == 'close':
                    mod.close_presentation(stage)
                    clock.now += 1
                    life.channel(dict(kind='start'), OWNER, clock.now)
                    life.channel(dict(kind='text', text=BODY), OWNER, clock.now)
                    self.assertEqual(life.reply, '')
                else:
                    jobs.playback_invalidator(reason, OWNER)
                stage.bridge.publish(state(), b'new-public-frame')
                self.assertNotIn(BODY, json.dumps(stage.bridge.state))
                outputs.append(stage.bridge.state)
            self.assertEqual(*outputs, reason)

    def test_malformed_publication_or_purge_does_not_replace_bridge_state(self):
        malformed_states = [None, [], 7, {'local_transcription': None},
                            {'local_transcription': ()}, {'local_transcription': 'bad'},
                            {'local_transcription': False}]
        for bad in malformed_states:
            for path in ['publish', 'purge']:
                outcomes = []
                for mod in [OLD, NEW]:
                    life, clock, stage, store, jobs = setup(mod)
                    initial = stage.bridge.state
                    if path == 'purge':
                        stage.bridge.state = initial = bad
                    try:
                        stage.bridge.publish(bad, b'bad') if path == 'publish' else life.invalidate()
                    except Exception as exc:
                        outcome = type(exc).__name__
                    else:
                        outcome = 'no_exception'
                    self.assertIs(stage.bridge.state, initial)
                    self.assertEqual(stage.bridge.published, 0)
                    self.assertTrue(life.lock.acquire(blocking=False))
                    life.lock.release()
                    self.assertTrue(stage.bridge.lock.acquire(blocking=False))
                    stage.bridge.lock.release()
                    outcomes.append(outcome)
                self.assertEqual(*outcomes, (bad, path))

    def test_publish_and_invalidation_serialize_without_old_body_reappearing(self):
        outputs = []
        for mod in [OLD, NEW]:
            life, clock, stage, store, jobs = setup(mod)
            entered, release, attempted = threading.Event(), threading.Event(), threading.Event()
            failures, order = [], []
            # Reattach around a controlled RAM bridge. Neither closure starts a service.
            def slow_publish(value, frame):
                entered.set()
                if not release.wait(2):
                    raise TimeoutError('public test synchronization')
                with stage.bridge.lock:
                    stage.bridge.state = dict(value)
                order.append('publish_done')
            stage.bridge.publish = slow_publish
            mod.attach_presentation(stage)
            def publishing():
                try:
                    stage.bridge.publish(state(), b'public')
                except Exception as exc:
                    failures.append(type(exc).__name__)
            def invalidating():
                attempted.set()
                try:
                    life.invalidate()
                    order.append('invalidate_done')
                except Exception as exc:
                    failures.append(type(exc).__name__)
            pub = threading.Thread(target=publishing, daemon=True)
            inv = threading.Thread(target=invalidating, daemon=True)
            pub.start()
            try:
                self.assertTrue(entered.wait(2))
                inv.start()
                self.assertTrue(attempted.wait(2))
            finally:
                release.set()
            pub.join(2)
            inv.join(2)
            self.assertFalse(pub.is_alive() or inv.is_alive())
            self.assertEqual(failures, [])
            self.assertEqual(order, ['publish_done', 'invalidate_done'])
            self.assertNotIn(BODY, json.dumps(stage.bridge.state))
            self.assertFalse(stage.bridge.state['presentation_lifecycle']['showing'])
            # Publish an old untrusted state after the invalidation has completed.
            stage.bridge.publish(state(), b'public-late')
            self.assertNotIn(BODY, json.dumps(stage.bridge.state))
            outputs.append(stage.bridge.state)
        self.assertEqual(*outputs)

    def test_persisted_diagnostics_are_equal_fixed_metadata_in_public_temporary_root(self):
        reports = []
        for mod in [OLD, NEW]:
            with tempfile.TemporaryDirectory(prefix='authored-public-diagnostics-', dir=HERE) as temp:
                root = Path(temp).resolve()
                life, clock, stage, store, jobs = setup(mod)
                stage.board_business.runtime.config.private_root = str(root)
                with patch.object(mod.time, 'monotonic_ns', return_value=987654321):
                    result = mod.save_production_evidence(stage)
                data = (root / 'diagnostics/latest_metadata.json').read_bytes()
                self.assertNotIn(BODY.encode(), data)
                report = json.loads(data)
                self.assertFalse(report['body_saved'] or report['images_saved'])
                self.assertTrue(result['metadata_only'])
                self.assertEqual(list(root.rglob('*.tmp')), [])
                reports.append(data)
        self.assertEqual(*reports)

    def test_subclass_override_compatibility_boundary_is_reproducible(self):
        outputs = {}
        for mod, label in [(OLD, 'baseline'), (NEW, 'candidate')]:
            class LegacyProjection(mod.PresentationLifecycle):
                def _projection(self, value):
                    return super()._projection(value)
            life, clock, stage, store, jobs = setup(mod, LegacyProjection)
            try:
                stage.bridge.publish(state(), b'public')
                legacy = 'published'
            except TypeError:
                legacy = 'TypeError'
            class BodyAddingProjection(mod.PresentationLifecycle):
                def _projection(self, value, **kwargs):
                    result = super()._projection(value, **kwargs)
                    result['extension'] = {'body': BODY}
                    return result
            life, clock, stage, store, jobs = setup(mod, BodyAddingProjection)
            stage.bridge.publish(state(), b'public')
            outputs[label] = dict(legacy_signature=legacy,
                                 extension_body_present=BODY in json.dumps(stage.bridge.state))
        self.assertEqual(outputs['baseline'], dict(legacy_signature='published', extension_body_present=False))
        self.assertEqual(outputs['candidate'], dict(legacy_signature='TypeError', extension_body_present=True))


def main():
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LifecyclePathTests))
    for folder, expected in PINS.items():
        assert hashlib.sha256((ROOT / folder / RELATIVE).read_bytes()).hexdigest() == expected
    report = dict(schema='aura-single-projection-independent-public-regressions-1', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful(),
        subclass_boundary_reproduced=True, public_temp_files_only=True,
        production_or_candidate_source_modified=False, device_network_model_or_database_access=False)
    (HERE / 'PUBLIC_TEST_RESULT.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
