"""Independent, device-free review of exact enrollment-start AST and public fixtures."""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import threading
import types
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
FIX = HERE.parent
OUT = HERE.parents[3]
BASE = OUT / 'identity_dialogue_collaboration/baseline'
ORIGINAL = BASE / 'board/identity/voice_enrollment.py'
V1 = HERE / 'reviewed_candidate_v1.py'
V2 = FIX / 'candidate_v2/board/identity/voice_enrollment.py'
EXPECTED = {
    'original': '83796dd78c57555ea66eeb2b745a89f8b3670945a4406176cb3486111d9466b8',
    'v1': '4a93a7d86b9cd6f52d0dcc9b9844767c684a276592b1d63fa0c43a099170e65d',
    'v2': 'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'}
for label, path in [('original', ORIGINAL), ('v1', V1), ('v2', V2)]:
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED[label]
(HERE / 'reviewed_candidate_v2.py').write_bytes(V2.read_bytes())


class ImmediateThread:
    def __init__(self, target, args=(), **kwargs): self.target, self.args = target, args
    def start(self): self.target(*self.args)


class Speech:
    @staticmethod
    def result(code, name=''): return {'code': code}


def namespace(path, fixture):
    space = {'copy': copy, 'math': math, 'uuid': uuid, 'speech': Speech,
             'threading': types.SimpleNamespace(RLock=threading.RLock, Thread=ImmediateThread),
             'time': types.SimpleNamespace(monotonic=fixture.clock, sleep=fixture.sleep),
             'millis': fixture.now_ms}
    contract = ast.parse((BASE / 'board/interaction/ui_contract.py').read_text(encoding='utf-8'))
    for node in contract.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in ('PROTOCOL', 'MODULE_STATES', 'ACTIONS')):
            space[node.targets[0].id] = ast.literal_eval(node.value)
    methods = [copy.deepcopy(n) for n in contract.body if isinstance(n, ast.FunctionDef)
               and n.name in ('integer', 'text', 'require', 'target_key', 'validate_snapshot', 'validate_ack')]
    exec(compile(ast.Module(body=methods, type_ignores=[]), '<original-contract>', 'exec'), space)
    fixture_source = ast.parse((BASE / 'tests/framework/test_simple_enrollment.py').read_text(encoding='utf-8'))
    snapshot = copy.deepcopy(next(n for n in fixture_source.body if isinstance(n, ast.FunctionDef) and n.name == 'snapshot'))
    exec(compile(ast.Module(body=[snapshot], type_ignores=[]), '<public-synthetic-fixture>', 'exec'), space)
    klass = copy.deepcopy(next(n for n in ast.parse(path.read_text(encoding='utf-8')).body
                               if isinstance(n, ast.ClassDef) and n.name == 'VoiceEnrollment'))
    retained = {'__init__', 'reset', '_send', '_cancel_sample', '_start_simple',
                'selected_target', 'single_target', 'owner_of'}
    klass.body = [n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name in retained]
    exec(compile(ast.Module(body=[klass], type_ignores=[]), '<exact-reviewed-methods>', 'exec'), space)
    return space


class Case:
    def __init__(self, path, *, stage='failed', observed=1050, ack_delay=0.,
                 no_publish=False, cancel_on=None, wrong_target=False, same_old_sid=False,
                 authorize_remaining=120.):
        self.now = 1.1
        self.commands, self.sleeps = [], []
        self.no_publish, self.cancel_on = no_publish, cancel_on
        self.wrong_target, self.same_old_sid = wrong_target, same_old_sid
        self.stage, self.observed, self.ack_delay = stage, observed, ack_delay
        self.current_checks = 0
        self.space = namespace(path, self)
        self.view = self.space['snapshot']()
        self.view['modules']['identity']['enrollment_sampling'].update(stage='failed', session_id='synthetic-A')
        self.flow = self.space['VoiceEnrollment']('boot', self.read, self.command,
            simple=True, clock=self.clock, now_ms=self.now_ms)
        self.flow.stage = 'authorize'
        self.flow.owner = copy.deepcopy(self.flow.owner_of(self.view))
        self.flow.until = self.now + authorize_remaining
        self.backend_stage = 'idle'

    def clock(self): return self.now
    def now_ms(self): return round(self.now * 1000)
    def read(self): return copy.deepcopy(self.view)
    def current(self):
        self.current_checks += 1
        return self.cancel_on is None or self.current_checks < self.cancel_on

    def command(self, value):
        self.commands.append(copy.deepcopy(value))
        if value['action'] == 'identity_sample_start':
            self.backend_stage = 'collect'
            self.now += self.ack_delay
            self.view['sequence'] = 2
            self.view['observed_mono_ms'] = self.observed
            self.view['modules']['identity']['enrollment_sampling'].update(
                stage=self.stage, session_id='synthetic-B', bound_target=copy.deepcopy(self.flow.owner[2]))
        elif value['action'] == 'identity_sample_cancel' and value['params']['session_id'] == 'synthetic-C':
            self.backend_stage = 'idle'
        ack = {k: value[k] for k in ('protocol_version', 'board_boot_id', 'service_epoch',
                                    'command_id', 'ui_epoch', 'ui_generation')}
        ack.update(accepted=True, detail='synthetic acknowledgement')
        return ack

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.now += duration
        if not self.no_publish:
            self.view['sequence'] = 3
            self.view['observed_mono_ms'] = self.now_ms()
            target = copy.deepcopy(self.flow.owner[2])
            if self.wrong_target: target['track_id'] += 1
            self.view['modules']['identity']['enrollment_sampling'].update(
                stage='collect', session_id='synthetic-A' if self.same_old_sid else 'synthetic-C', bound_target=target)

    def run(self):
        captured = copy.deepcopy(self.view)
        try:
            value = self.flow._start_simple(captured, is_current=self.current)
            code = value['code']
        except InterruptedError:
            code = 'INTERRUPTED'
        cancels = [c['params']['session_id'] for c in self.commands if c['action'] == 'identity_sample_cancel']
        return {'result': code, 'local_stage': self.flow.stage,
                'bound_to_current_C': self.flow.sampling_id == 'synthetic-C',
                'bound_to_old_B': self.flow.sampling_id == 'synthetic-B',
                'start_count': sum(c['action'] == 'identity_sample_start' for c in self.commands),
                'cancel_count': len(cancels), 'cancelled_old_B': 'synthetic-B' in cancels,
                'cancelled_current_C': 'synthetic-C' in cancels,
                'backend_stage': self.backend_stage, 'sleep_count': len(self.sleeps),
                'elapsed_s': round(self.now - 1.1, 6), 'until_s': self.flow.until}


results = {}
for stage in ('failed', 'ready', 'collect'):
    # Exact previous V1 counterexample, extended to all three old-B phases.
    v1 = Case(V1, stage=stage).run()
    v2 = Case(V2, stage=stage).run()
    assert v1['start_count'] == 1 and (v1['cancelled_old_B'] or v1['bound_to_old_B'])
    assert v2['result'] == 'sample_auto' and v2['bound_to_current_C']
    assert v2['start_count'] == 1 and v2['cancel_count'] == 0
    assert v2['until_s'] == 91.1
    results['precommand_B_' + stage] = {'v1': v1, 'v2': v2}

for label, options, expected in [
    ('B_between_issued_and_ack', {'stage': 'collect', 'observed': 1150, 'ack_delay': .1}, 'sample_auto'),
    ('B_equal_ack', {'stage': 'collect', 'observed': 1100}, 'sample_auto'),
    ('B_post_ack_ready', {'stage': 'ready', 'observed': 1101}, 'sample_auto'),
    ('wrong_bound_target', {'wrong_target': True}, 'sample_failed'),
    ('old_A_republished', {'same_old_sid': True}, 'sample_failed'),
    ('never_published', {'no_publish': True}, 'sample_failed'),
    ('cancel_before_start', {'cancel_on': 1}, 'INTERRUPTED'),
    ('cancel_before_trust', {'cancel_on': 2}, 'INTERRUPTED'),
    ('cancel_after_trusted_C', {'cancel_on': 3}, 'INTERRUPTED'),
    ('original_authorization_earlier_deadline', {'no_publish': True, 'authorize_remaining': .075}, 'sample_failed'),
]:
    case = Case(V2, **options)
    r = case.run()
    assert r['result'] == expected, (label, r)
    assert r['start_count'] <= 1 and not r['cancelled_old_B'], (label, r)
    if expected == 'sample_auto': assert r['bound_to_current_C'] and r['cancel_count'] == 0
    if label == 'cancel_after_trusted_C': assert r['cancelled_current_C'] and r['cancel_count'] == 1
    else: assert r['cancel_count'] == 0
    if label == 'never_published': assert r['elapsed_s'] <= 2.5 and r['sleep_count'] <= 50
    if label == 'original_authorization_earlier_deadline': assert r['elapsed_s'] <= .075001
    results[label] = r

trees = {}
for label, path in [('original', ORIGINAL), ('v2', V2)]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'VoiceEnrollment')
    trees[label] = {n.name: n for n in klass.body if isinstance(n, ast.FunctionDef)}
changed = [name for name, method in trees['original'].items()
           if ast.dump(method) != ast.dump(trees['v2'][name])]
assert set(changed) == {'_start_simple', 'handle'}
before_handle, after_handle = copy.deepcopy(trees['original']['handle']), copy.deepcopy(trees['v2']['handle'])
call = next(n for n in ast.walk(after_handle) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == '_start_simple')
assert len(call.keywords) == 1 and call.keywords[0].arg == 'is_current'
assert isinstance(call.keywords[0].value, ast.Name) and call.keywords[0].value.id == 'is_current'
call.keywords = []
assert ast.dump(before_handle) == ast.dump(after_handle)
assert sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'command'
           for n in ast.walk(trees['v2']['_start_simple'])) == 1

xmls = {}
for name in ('RACE_V2_CANDIDATE_FINAL.xml', 'ORIGINAL_BASELINE_V2_FINAL.xml', 'ORIGINAL_CANDIDATE_V2_FINAL.xml'):
    path = FIX / name
    suites = list(ET.fromstring(path.read_bytes()).iter('testsuite'))
    xmls[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                 **{key: sum(int(s.attrib.get(key, 0)) for s in suites)
                    for key in ('tests', 'failures', 'errors', 'skipped')}}

output = {'schema': 'aura-enrollment-start-sync-independent-review-2',
          'source_hashes': EXPECTED, 'focused_case_count': len(results), 'all_focused_cases_pass': True,
          'exact_original_snapshot_and_ack_validators': True, 'exact_reviewed_start_methods': True,
          'changed_methods': changed, 'handle_only_passes_original_is_current': True,
          'unmodified_methods': sorted(set(trees['original']) - set(changed)),
          'one_command_call_site_inside_start': True, 'cases': results,
          'author_xml_receipts_at_review_time': xmls,
          'devices_network_models_real_databases_accessed': False,
          'candidate_or_production_sources_changed': False}
(HERE / 'V2_INDEPENDENT_RESULTS.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'all_focused_cases_pass': True, 'cases': len(results), 'changed_methods': changed,
                  'candidate_sha256': EXPECTED['v2'], 'author_xml_counts': xmls}))
