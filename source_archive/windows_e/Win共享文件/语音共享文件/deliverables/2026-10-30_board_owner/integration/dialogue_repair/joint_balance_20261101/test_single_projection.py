"""Compare actual old/new presentation paths with public RAM fixtures only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RELATIVE = 'tools/production_memory_presentation.py'


def module(label, root):
    spec = importlib.util.spec_from_file_location(label, root / RELATIVE)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


OLD = module('baseline_presentation', HERE / 'baseline')
NEW = module('candidate_presentation', HERE / 'presentation_candidate')
OWNER = dict(board_boot_id='public-boot', session_id='public-session', generation=1, request_id='public-request')
BODY = 'public-body-sentinel'


def fixture():
    return dict(reply=BODY, local_transcription=dict(text=BODY, voice_reply=dict(reply_text=BODY)),
                error=BODY, turns=[dict(text=BODY)], log=[BODY], metrics=dict(p50=1.2, p95=4.5),
                nested=[dict(detail=BODY, source=dict(messages=[dict(content=BODY)], ready=True))])


def lifecycle(mod):
    clock = NS(now=10.)
    stage = NS(runtime_view=fixture())
    life = mod.PresentationLifecycle(stage, NS(), clock=lambda: clock.now, ttl=300.)
    life.channel(dict(kind='start'), OWNER, clock.now)
    life.channel(dict(kind='transcript', text=BODY), OWNER, clock.now)
    life.channel(dict(kind='text', text=BODY), OWNER, clock.now)
    return life, clock, stage


def old_metadata(life, state):
    return OLD._clean(life._projection(state))


def new_metadata(life, state):
    return life._projection(state, metadata_only=True)


class SingleProjectionTests(unittest.TestCase):
    def test_default_current_display_projection_remains_equal(self):
        before, _, _ = lifecycle(OLD)
        after, _, _ = lifecycle(NEW)
        self.assertEqual(before.project(fixture()), after.project(fixture()))
        self.assertEqual(after.project(fixture())['reply'], BODY)

    def test_metadata_is_equal_and_cannot_contain_bodies(self):
        before, _, _ = lifecycle(OLD)
        after, _, _ = lifecycle(NEW)
        left, right = old_metadata(before, fixture()), new_metadata(after, fixture())
        self.assertEqual(left, right)
        self.assertNotIn(BODY, json.dumps(right))

    def test_expiry_boundary_and_repeated_publication_never_renew_ttl(self):
        before, a, _ = lifecycle(OLD)
        after, b, _ = lifecycle(NEW)
        deadline = after.deadline
        for now in (10., 100., 309.999, 310., 311.):
            a.now = b.now = now
            self.assertEqual(old_metadata(before, fixture()), new_metadata(after, fixture()))
            self.assertEqual(before.deadline, after.deadline)
        self.assertEqual(after.deadline, deadline)
        self.assertIsNone(after.current)
        self.assertEqual(after.expirations, 1)

    def test_nested_tuple_lists_errors_and_existing_lifecycle_fields(self):
        state = fixture()
        state.update(extra=(dict(error={'body': BODY}, text=BODY), [None, False, 0, 1.2]),
                     presentation_lifecycle=dict(reply=BODY, error=BODY),
                     context=dict(detail='', bytes=b'public-bytes'))
        before, _, _ = lifecycle(OLD)
        after, _, _ = lifecycle(NEW)
        self.assertEqual(old_metadata(before, state), new_metadata(after, state))

    def test_outputs_are_detached_and_source_is_not_modified(self):
        state = fixture()
        original = copy.deepcopy(state)
        life, _, _ = lifecycle(NEW)
        projected = new_metadata(life, state)
        projected['metrics']['p50'] = 1000
        projected['nested'][0]['source']['ready'] = False
        self.assertEqual(state, original)
        self.assertEqual(new_metadata(life, state)['metrics']['p50'], 1.2)

    def test_invalidation_purges_old_bridge_state_identically(self):
        outputs = []
        for mod in (OLD, NEW):
            life, _, stage = lifecycle(mod)
            stage.bridge = NS(lock=threading.Lock(), state=fixture())
            life.invalidate()
            outputs.append(stage.bridge.state)
            self.assertIsNone(life.current)
            self.assertNotIn(BODY, json.dumps(stage.bridge.state))
        self.assertEqual(*outputs)

    def test_delayed_start_after_invalidation_cannot_revive_subtitles(self):
        states = []
        for mod in (OLD, NEW):
            life, clock, _ = lifecycle(mod)
            life.invalidate()
            clock.now = 11.
            life.channel(dict(kind='start'), OWNER, 9.)
            life.channel(dict(kind='text', text=BODY), OWNER, 9.)
            states.append(life.project(fixture()))
            self.assertEqual(life.reply, '')
        self.assertEqual(*states)

    def test_publication_path_keeps_lock_and_projects_one_tree_once(self):
        life, _, stage = lifecycle(NEW)
        captured = []
        stage.production_presentation = life
        stage.bridge = NS(publish=lambda state, frame: captured.append((state, frame)))
        stage.controller = NS(read=lambda: dict(state=fixture()))
        life.repaint = lambda: None
        NEW.attach_presentation(stage)
        original_clean = NEW._clean
        roots = []
        def count(value):
            if value is state:
                roots.append(value)
            return original_clean(value)
        state = fixture()
        with patch.object(NEW, '_clean', count):
            stage.bridge.publish(state, b'public-frame')
        self.assertEqual(len(roots), 1)
        self.assertEqual(captured[0][0], old_metadata(lifecycle(OLD)[0], state))
        self.assertEqual(captured[0][1], b'public-frame')

    def test_seeded_nested_json_equivalence_500_cases(self):
        rng = random.Random(20261101)
        keys = ['text', 'reply', 'reply_text', 'transcript', 'turns', 'log', 'messages', 'prompt',
                'content', 'body', 'error', 'detail', 'count', 'value', 'nested', 'state']
        def tree(depth):
            if depth == 0 or rng.randrange(4) == 0:
                return rng.choice([BODY, '', None, True, False, 0, 123, 1.5])
            if rng.randrange(2):
                return {key: tree(depth - 1) for key in rng.sample(keys, rng.randrange(1, 7))}
            return [tree(depth - 1) for _ in range(rng.randrange(5))]
        for _ in range(500):
            state = dict(payload=tree(4), reply=BODY, local_transcription=dict(text=BODY))
            before, _, _ = lifecycle(OLD)
            after, _, _ = lifecycle(NEW)
            self.assertEqual(old_metadata(before, state), new_metadata(after, state))

    def test_same_exception_for_invalid_existing_local_transcription_shape(self):
        for malformed in (None, 1, '', []):
            errors = []
            for mod, call in ((OLD, old_metadata), (NEW, new_metadata)):
                life, _, _ = lifecycle(mod)
                try:
                    call(life, dict(local_transcription=malformed))
                except Exception as exc:
                    errors.append(type(exc))
            self.assertEqual(len(errors), 2)
            self.assertEqual(*errors)

    def test_source_changes_are_exactly_five_frozen_replacements(self):
        spec = importlib.util.spec_from_file_location('candidate_builder', HERE / 'prepare_presentation_candidate.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        actual = (HERE / 'presentation_candidate' / RELATIVE).read_bytes()
        for old, new in reversed(builder.REPLACEMENTS):
            self.assertEqual(actual.count(new), 1)
            actual = actual.replace(new, old, 1)
        self.assertEqual(actual, (HERE / 'baseline' / RELATIVE).read_bytes())


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SingleProjectionTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    proof = dict(schema='aura-single-projection-tests-1', tests=result.testsRun,
                 failures=len(result.failures), errors=len(result.errors),
                 passed=result.wasSuccessful(), randomized_equivalence_cases=500,
                 source_sha256=hashlib.sha256((HERE / 'presentation_candidate' / RELATIVE).read_bytes()).hexdigest(),
                 device_or_network_or_model_or_database=False)
    (HERE / 'presentation_test_result.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
