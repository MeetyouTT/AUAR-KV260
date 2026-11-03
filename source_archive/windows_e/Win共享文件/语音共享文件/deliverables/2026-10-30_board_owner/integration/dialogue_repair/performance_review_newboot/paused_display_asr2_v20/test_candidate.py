"""Normal refresh entry with fake services/wake, plus exact configuration tests."""
import ast
import copy
import hashlib
import importlib.util
import io
import itertools
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
BASE = REPAIR/'feature_trigger_collaboration/candidate_m03_v90_stage/public_runtime_v90'
sys.path.insert(0,str(BASE))
from tools.x11_display_activity import DisplayActivity


def load(slot):
    path = HERE/slot/'tools/board_avatar_gtk.py'
    name = 'public_paused_display_'+slot
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BEFORE, AFTER = load('before'), load('after')


class RefreshReachedNextStage(Exception):
    pass


class Harness:
    def __init__(self, module=AFTER, origin='board', wake=None):
        self.now = 10.
        self.wakes = []
        self.stage = module.BoardAvatarStage.__new__(module.BoardAvatarStage)
        self.stage.board_business = (SimpleNamespace(runtime=SimpleNamespace(config=SimpleNamespace(data_origin=origin)))
                                     if origin is not None else None)
        self.stage.services = SimpleNamespace(read=lambda:dict(snapshot=None,link='READY'))
        self.stage.preview_output = None
        self.stage.display_activity = DisplayActivity(wake=wake or (lambda:self.wakes.append(self.now)),
                                                     clock=lambda:self.now)
        self.stage.refresh_voice_face_dialog = self.next_stage
        self.stage.closed = False
        self.state = dict(phase='IDLE',playing=False,paused=False,
            handsfree_dialogue=dict(enabled=False,state='PAUSED',microphone_open=False),
            automatic_conversation=dict(enabled=False),local_transcription=dict(state='IDLE'))

    def next_stage(self, transcription):
        # Stop after the real display call, before unrelated GTK widget updates.
        raise RefreshReachedNextStage()

    def refresh(self):
        try:
            self.stage.refresh_runtime(self.state,'')
        except RefreshReachedNextStage:
            return
        raise AssertionError('The real refresh entry did not reach the display boundary')


class DisplayCandidateTests(unittest.TestCase):
    def test_baseline_paused_board_does_not_keep_display_active(self):
        h = Harness(BEFORE)
        for value in (10.,15.,20.):
            h.now = value
            h.refresh()
        self.assertEqual(h.wakes,[])

    def test_paused_production_uses_existing_five_second_cadence(self):
        h = Harness()
        for value in (10.,10.01,11.,14.999,15.,15.001,19.999,20.):
            h.now = value
            h.refresh()
        self.assertEqual(h.wakes,[10.,15.,20.])

    def test_legacy_and_synthetic_activity_truth_table_is_unchanged(self):
        for origin, flags in itertools.product((None,'synthetic'),itertools.product((False,True),repeat=3)):
            with self.subTest(origin=origin,flags=flags):
                results = []
                for module in (BEFORE,AFTER):
                    h = Harness(module,origin)
                    h.state['handsfree_dialogue']['enabled'] = flags[0]
                    h.state['automatic_conversation']['enabled'] = flags[1]
                    h.state['playing'] = flags[2]
                    for value in (10.,14.999,15.,20.):
                        h.now = value
                        h.refresh()
                    results.append(h.wakes)
                self.assertEqual(results[0],results[1])
                self.assertEqual(results[1],[10.,15.,20.] if any(flags) else [])

    def test_production_pause_keeps_listening_and_playback_state_unchanged(self):
        h = Harness()
        before = copy.deepcopy(h.state)
        h.refresh()
        self.assertEqual(h.state,before)
        self.assertFalse(h.state['handsfree_dialogue']['enabled'])
        self.assertFalse(h.state['handsfree_dialogue']['microphone_open'])

    def test_wake_error_is_contained_and_next_existing_interval_retries(self):
        calls = []
        def wake():
            calls.append(True)
            if len(calls) == 1:
                raise OSError('public synthetic wake failure')
        h = Harness(wake=wake)
        h.refresh()
        self.assertTrue(h.stage.display_activity.error)
        h.now = 14.999
        h.refresh()
        self.assertEqual(len(calls),1)
        h.now = 15.
        h.refresh()
        self.assertEqual(len(calls),2)
        self.assertEqual(h.stage.display_activity.error,'')

    def test_closed_existing_tick_exits_without_waking(self):
        h = Harness()
        h.stage.closed = True
        self.assertFalse(h.stage.tick())
        self.assertEqual(h.wakes,[])

    def test_releasing_board_owner_resumes_original_idle_behavior(self):
        h = Harness()
        h.refresh()
        h.stage.board_business = None
        h.now = 15.
        h.refresh()
        self.assertEqual(h.wakes,[10.])
        self.assertEqual(h.stage.display_activity.next_wake,0.)

    def test_gtk_other_functions_and_existing_tick_are_ast_identical(self):
        trees = []
        for slot in ('before','after'):
            tree = ast.parse((HERE/slot/'tools/board_avatar_gtk.py').read_bytes())
            cls = next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='BoardAvatarStage')
            cls.body = [node for node in cls.body if not (isinstance(node,ast.FunctionDef) and node.name=='refresh_runtime')]
            trees.append(ast.dump(tree,include_attributes=False))
        self.assertEqual(trees[0],trees[1])

    def test_existing_display_helper_is_still_exactly_pinned(self):
        path = BASE/'tools/x11_display_activity.py'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         'da318d5094a44bce9e62d57dda5c5c2f62ee06580d028e9cc08334737c9ceb97')


class ConfigCandidateTests(unittest.TestCase):
    def test_only_asr_threads_changes_and_raw_diff_is_one_byte(self):
        before_raw = (HERE/'before/config/board_avatar_gtk.json').read_bytes()
        after_raw = (HERE/'after/config/board_avatar_gtk.json').read_bytes()
        self.assertEqual(hashlib.sha256(before_raw).hexdigest(),
                         '5518b6705083eb9e2fae7e19a47c003182995fe8660cbc6031860c9905da9786')
        expected = json.loads(before_raw)
        expected['board_business']['asr_threads'] = 2
        self.assertEqual(json.loads(after_raw),expected)
        self.assertEqual(len(before_raw),len(after_raw))
        self.assertEqual(sum(a!=b for a,b in zip(before_raw,after_raw)),1)

    def test_current_asr_selector_consumes_configured_thread_count(self):
        path = BASE/'tools/production_board_business_gui.py'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         'b01f6edb9efe88cf95da60900e5ccc32eec93a24ef3f515ab08f51ae2ee6ada8')
        tree = ast.parse(path.read_bytes())
        selections = [keyword.value for node in ast.walk(tree) if isinstance(node,ast.Call)
                      for keyword in node.keywords if keyword.arg=='num_threads']
        configured = [node for node in selections if ast.dump(node,include_attributes=False)==
                      ast.dump(ast.parse("value.get('asr_threads', 2)",mode='eval').body,include_attributes=False)]
        self.assertEqual(len(configured),1)
        value = json.loads((HERE/'after/config/board_avatar_gtk.json').read_bytes())['board_business']
        self.assertEqual(eval(compile(ast.Expression(configured[0]),'<public-selected-thread-expression>','eval'),
                              {'value':value}),2)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    for cls in (DisplayCandidateTests,ConfigCandidateTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report = dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),log=stream.getvalue(),
        normal_refresh_entry_executed_until_next_ui_stage=True,
        devices_models_microphone_audio_or_X11_accessed=False)
    path = HERE/'LOCAL_TESTS.json'
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if result.wasSuccessful():
        handoff_path = HERE/'HANDOFF.json'
        handoff = json.loads(handoff_path.read_bytes())
        handoff['status'] = 'LOCAL_READY_FOR_INDEPENDENT_REVIEW_AND_PUBLICATION_FRAMEWORK'
        handoff['local_tests'] = dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),passed=result.testsRun)
        handoff['source_manifest_sha256'] = hashlib.sha256((HERE/'SOURCE_MANIFEST.json').read_bytes()).hexdigest()
        handoff_path.write_text(json.dumps(handoff,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)
