"""Small public synthetic rejection probes, never the CLI or a board operation.

Execute exact original Seed/Recovery class AST and pure original validators.
No NativeContext/CDLL class is extracted or instantiated. All checkpoint,
marker, /proc and archive I/O used by these probes is an in-memory stub.
"""
import ast
import copy
import ctypes
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import sys
import time
import types
import unittest
import uuid

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
spec = importlib.util.spec_from_file_location('fresh_final_candidate_for_pure_checks', HERE / 'validate_fresh_final_history_readonly.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class MemoryPath(PurePosixPath):
    def resolve(self, *args, **kwargs):
        return self

    def exists(self):
        return False


candidate.Path = MemoryPath
for constant in ('ROOT', 'CHECKPOINT', 'MANIFEST', 'ARCHIVES', 'LEGACY'):
    setattr(candidate, constant, MemoryPath(getattr(candidate, constant).as_posix()))
candidate.os = types.SimpleNamespace(path=types.SimpleNamespace(lexists=lambda path: False))


def exact_functions(path, expected_sha, namespace, names, classes=()):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_sha
    tree = ast.parse(raw)
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in names
             or isinstance(node, ast.ClassDef) and node.name in classes]
    assert len(nodes) == len(names) + len(classes)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<exact-original-pure-AST>', 'exec'), namespace)


binding = types.ModuleType('board.vision.native_binding')
binding.C = ctypes
exact_functions(BASE / 'parallel_platform_review/review_sources/native_binding.py', candidate.PINS['board/vision/native_binding.py'],
                binding.__dict__, (), ('Seed', 'Recovery'))
protection = types.ModuleType('original_native_protection_pure')
protection.__dict__.update(C=ctypes, uuid=uuid, Path=MemoryPath, time=time,
                          FEATURE_COUNTERS=candidate.FEATURES)
exact_functions(HERE / 'baseline/b8637c2aa387__native_protection.py', candidate.PINS['board/vision/native_protection.py'],
                protection.__dict__, ('integer', 'digest', '_boot', 'make_native_seed', 'load_business_checkpoint'))
boot_module = types.ModuleType('original_native_boot_pure')
boot_module.__dict__.update(hashlib=hashlib, json=json, Path=MemoryPath, MAX_CLOCK=2**63 - 1,
                           _boot=protection._boot, digest=protection.digest, integer=protection.integer,
                           make_native_seed=protection.make_native_seed, FEATURE_COUNTERS=candidate.FEATURES)
exact_functions(HERE / 'baseline/251e9660633c__native_boot.py', candidate.PINS['board/vision/native_boot.py'],
                boot_module.__dict__, ('_canonical', '_time', '_sealed_source', '_legacy_source'))


class MemorySnapshot:
    def __init__(self):
        self.files = {}

    def read(self, path):
        return self.files[str(path)]

    def pinned(self, value, fixed_path=None):
        path = candidate.pin(value, fixed_path)
        raw = self.read(path)
        candidate.require(candidate.sha(raw) == value['sha256'], 'Pinned input hash differs')
        return json.loads(raw)

    def put(self, path, value, raw=None):
        data = candidate.canonical(value) if raw is None else raw
        self.files[str(path)] = data
        return {'path': str(path), 'sha256': candidate.sha(data)}


CURRENT = '10000000-0000-4000-8000-000000000001'
OLD = '20000000-0000-4000-8000-000000000002'
LEGACY_BOOT = '30000000-0000-4000-8000-000000000003'


def clean_policy(captured):
    return dict(enabled=1, phase=0, reason=0, probe_successes=0, attempt_count=0,
                history_opaque=0, opaque_attempt_count=0, cooldown_until_ns=0,
                fault_primary_calls=0, fault_primary_overruns=0, faults=0, attempts=0,
                recoveries=0, observed_ns=captured, attempt_times_ns=[0, 0])


def optional_state(calls):
    return dict(calls=calls, native_completed=1, native_failures=0, not_submitted=0, overruns=0,
                pending_result_token=0, disabled=False, last_native_report={},
                recovery=dict(enabled=True, phase='RUNNING', faults=0, attempts=0, recoveries=0,
                              probe_successes=0, attempts_in_window=0, history_opaque=False))


def checkpoint(boot_id, manifest_sha, calls, captured):
    seed = dict(abi_version=2, purpose='final_quiescent_business_checkpoint', checkpoint_kind=1,
                fenced=0, captured_mono_ns=captured, primary_calls=calls, primary_period_overruns=0,
                last_primary_ns=captured - 1, source_pid=900, source_birth_ticks=99, boot_id=boot_id,
                source_manifest_sha256=manifest_sha, admissions=[calls, calls, calls],
                overruns=[0, 0, 0], completed=[calls, 1, 1], native_failures=[0, 0, 0],
                not_submitted=[0, 0, 0], disabled=[0, 0, 0], recovery=[clean_policy(captured), clean_policy(captured)])
    auxiliary = dict(active=0, primary_waiting=0, fenced=0, pending_result_tokens=[0, 0, 0],
                     sface_counters={key: 1 for key in candidate.FEATURES},
                     inherited_optional={task: optional_state(calls) for task in ('yunet', 'sface')})
    return dict(schema='aura-native-protection-checkpoint-2', scope='final_quiescent_before_native_owner_close',
                seed=seed, auxiliary=auxiliary, source_unit_sha256=candidate.SOURCE_UNIT)


def legacy_document():
    manifest = {'public/legacy.py': 'a' * 64}
    manifest_sha = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    provenance = dict(source_pid=123, source_birth_ticks=45, captured_mono_ns=25,
                      source_unit_sha256='b' * 64, source_manifest_sha256=manifest_sha)
    policy = dict(enabled=True, phase='RUNNING', faults=0, attempts=0, recoveries=0, probe_successes=0, attempts_in_window=0)
    schedule = dict(owner_fenced=False, owner_fault_reason=None, guard_ms=5.0, budget_ms=20.0,
                    primary_calls=5000, primary_period_overruns=0,
                    optional_diagnostics={'enabled': True, 'diagnostic_errors': 0, 'fault_events': []}, diagnostic_failures=0,
                    optional={task: dict(calls=1, overruns=0, disabled=False) for task in ('yunet', 'sface')},
                    yunet_recovery=copy.deepcopy(policy), sface_recovery=copy.deepcopy(policy))
    payload = dict(schema='aura-legacy-health-prefix-1', boot=LEGACY_BOOT, schedule=schedule,
                   feature_inference=dict(kind='DPU_SFACE_INT8', **{key: 1 for key in candidate.FEATURES}), **provenance)
    return dict(schema='aura-native-legacy-boot-archive-1', prefix_scope='legacy_health_prefix_lower_bound',
                source_boot=LEGACY_BOOT, source_manifest=manifest, legacy_payload=payload,
                legacy_payload_sha256=hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                **provenance)


def fixture(archive_mutator=None, archive_schema=None):
    snapshot = MemorySnapshot()
    manifest_pin = snapshot.put(candidate.MANIFEST, {'public/current.py': 'c' * 64})
    legacy = legacy_document()
    # Deliberately noncanonical bytes: the terminal anchor must use its original
    # hash, never the canonical reserialization hash of its embedded document.
    legacy_raw = (json.dumps(legacy, indent=2) + '\n').encode()
    legacy_pin = snapshot.put(candidate.LEGACY, legacy, legacy_raw)

    def archive(current_boot, source_boot, cp, lower):
        source_sha = legacy_pin['sha256'] if lower else candidate.sha(candidate.canonical(cp))
        path = candidate.ARCHIVES / (current_boot + '-' + source_sha + '.json')
        value = dict(schema='aura-native-previous-kernel-archive-1', current_boot=current_boot,
                     source_boot=source_boot, source_checkpoint_sha256=source_sha,
                     source_checkpoint_path=str(candidate.LEGACY if lower else candidate.CHECKPOINT),
                     source_manifest_sha256=cp['source_manifest_sha256'] if lower else cp['seed']['source_manifest_sha256'],
                     history_is_lower_bound=lower, unknown_tail=lower, checkpoint=cp)
        if archive_schema and not lower:
            value['schema'] = archive_schema
        pinned = snapshot.put(path, value)
        link = dict(archive_path=str(path), archive_sha256=pinned['sha256'], source_checkpoint_sha256=source_sha,
                    source_boot=source_boot, history_is_lower_bound=lower,
                    scope='Persistent archive links predecessor history; not part of current counters')
        row = dict(path=str(path), sha256=pinned['sha256'], current_boot=current_boot, source_boot=source_boot,
                   source_checkpoint_sha256=source_sha, history_is_lower_bound=lower)
        return link, row

    legacy_link, legacy_row = archive(OLD, LEGACY_BOOT, legacy, True)
    prior = checkpoint(OLD, 'd' * 64, 1000, 50)
    prior['previous_kernel_history'] = legacy_link
    if archive_mutator:
        archive_mutator(prior)
    head, first_row = archive(CURRENT, OLD, prior, False)
    document = checkpoint(CURRENT, manifest_pin['sha256'], 10, 200)
    document['previous_kernel_history'] = head
    checkpoint_pin = snapshot.put(candidate.CHECKPOINT, document)
    current_owner = dict(pid=900, birth_ticks='99', command_sha256='e' * 64)
    startup = snapshot.put('/synthetic/startup/config.json', {'public': True})
    run_pin = snapshot.put('/synthetic/ops/native-run-' + CURRENT + '-900/config.json', {
        'native_execution': dict(source_manifest=manifest_pin['path'], source_manifest_sha256=manifest_pin['sha256'],
                                 source_unit_sha256=candidate.SOURCE_UNIT)})
    intent = dict(schema='aura-original-camera-stop-intent-2', boot_id=CURRENT, source_owner=current_owner,
                  source_pid=900, source_birth_ticks=99, startup=startup, stop_intent_mono_ns=150,
                  primary_calls_lower_bound=5, primary_period_overruns_lower_bound=0,
                  prestop_bounds=dict(sface=copy.deepcopy(document['auxiliary']['sface_counters']),
                                      optional=copy.deepcopy(document['auxiliary']['inherited_optional'])),
                  all_other_writers_frozen=True, action='systemctl stop --no-block aura-camera-ui.service')
    result = dict(schema='aura-original-camera-normal-stop-2', status='CAMERA_STOPPED_NEW_FINAL_PRESENT',
                  intent=copy.deepcopy(intent), normal_stop_submitted_once=True, forced_action=False,
                  checkpoint_or_marker_written_by_this_script=False, fresh_checkpoint=checkpoint_pin, captured_mono_ns=200)
    history = dict(observed_mono_ns=100, archive_count=2, archives=[first_row, legacy_row], head=head, legacy_pin=legacy_pin)
    receipt = snapshot.put('/synthetic/previous-accepted-history.json', {'archives': [legacy_row]})
    current_receipt = snapshot.put('/synthetic/current-prestop-history.json', dict(boot_id=CURRENT,
        source_owner=current_owner, observed_mono_ns=100, head=head, archive_prefix=[first_row]))
    def reference(pinned, pointer):
        return {'pin': pinned, 'pointer': pointer}
    proof = dict(schema='aura-prestop-native-history-manifest-1', boot_id=CURRENT,
                 source_owner=current_owner, history=copy.deepcopy(history), source_bindings={
                     **{name: reference(current_receipt, '/' + name) for name in ('boot_id', 'source_owner', 'observed_mono_ns', 'head')},
                     'archive_segments': [reference(current_receipt, '/archive_prefix'), reference(receipt, '/archives')]})
    history['provenance_pin'] = snapshot.put('/synthetic/prestop-history.json', proof)
    expected = dict(schema='aura-fresh-final-history-expected-1', all_other_writers_frozen=True, boot_id=CURRENT,
                    camera_owner=current_owner, stopped_gui_owners=[dict(pid=801, birth_ticks='88', command_sha256='f' * 64)],
                    startup=startup, checkpoint_pin=checkpoint_pin, source_manifest_pin=manifest_pin,
                    owner_run_config_pin=run_pin, source_unit_sha256=candidate.SOURCE_UNIT,
                    stop_intent_pin=snapshot.put('/synthetic/stop/camera-stop-intent.json', intent),
                    stop_result_pin=snapshot.put('/synthetic/stop/camera-stop-result.json', result), history=history)
    return snapshot, expected, intent, result, document


class FreshHistoryChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_modules = {name: sys.modules.get(name) for name in ('board', 'board.vision', 'board.vision.native_binding')}
        for name in ('board', 'board.vision'):
            value = types.ModuleType(name); value.__path__ = []; sys.modules[name] = value
        sys.modules['board.vision.native_binding'] = binding

    @classmethod
    def tearDownClass(cls):
        for name, original in cls.old_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def current(self, snapshot, expected, intent, result):
        protection._read_pinned = lambda value: (candidate.CHECKPOINT, snapshot.pinned(value))
        return candidate.validate_current(expected, intent, result, snapshot, protection, boot_module)[0]

    def test_original_functions_accept_two_boot_domains_and_exact_legacy_bytes(self):
        snapshot, expected, intent, result, _ = fixture()
        current = self.current(snapshot, expected, intent, result)
        records = candidate.validate_chain(current, expected['history'], snapshot, protection, boot_module)
        self.assertEqual(len(records), 2)
        self.assertEqual(current['seed']['primary_calls'], 10)
        # Archived predecessor1000 and legacy5000 do not constrain current10.
        self.assertNotEqual(candidate.sha(candidate.canonical(legacy_document())), expected['history']['legacy_pin']['sha256'])

    def test_contract_uses_root_intent_prestop_bounds_and_independent_history(self):
        snapshot, expected, intent, result, _ = fixture()
        original_legacy_sha = candidate.LEGACY_SHA
        candidate.LEGACY_SHA = expected['history']['legacy_pin']['sha256']
        try:
            a, b = candidate.validate_inputs(expected, snapshot)
            self.assertEqual(a['prestop_bounds'], intent['prestop_bounds'])
            self.assertEqual(b, result)
        finally:
            candidate.LEGACY_SHA = original_legacy_sha

    def test_required_history_cannot_be_guessed_or_omitted(self):
        snapshot, expected, _, _, _ = fixture()
        expected.pop('history')
        with self.assertRaises(KeyError):
            candidate.validate_inputs(expected, snapshot)

    def test_claimed_history_head_must_match_its_referenced_source_value(self):
        snapshot, expected, _, _, _ = fixture()
        proof = snapshot.pinned(expected['history']['provenance_pin'])
        proof['source_bindings']['head']['pointer'] = '/source_owner'
        expected['history']['provenance_pin'] = snapshot.put('/synthetic/prestop-history.json', proof)
        old = candidate.LEGACY_SHA; candidate.LEGACY_SHA = expected['history']['legacy_pin']['sha256']
        try:
            with self.assertRaisesRegex(ValueError, 'History source field differs: head'):
                candidate.validate_inputs(expected, snapshot)
        finally:
            candidate.LEGACY_SHA = old

    def test_ordered_accepted_history_segments_cannot_drop_the_prior_chain(self):
        snapshot, expected, _, _, _ = fixture()
        proof = snapshot.pinned(expected['history']['provenance_pin'])
        proof['source_bindings']['archive_segments'].pop()
        expected['history']['provenance_pin'] = snapshot.put('/synthetic/prestop-history.json', proof)
        old = candidate.LEGACY_SHA; candidate.LEGACY_SHA = expected['history']['legacy_pin']['sha256']
        try:
            with self.assertRaisesRegex(ValueError, 'ordered accepted source segments'):
                candidate.validate_inputs(expected, snapshot)
        finally:
            candidate.LEGACY_SHA = old

    def test_same_boot_final_rejects_wrong_source_owner(self):
        snapshot, expected, intent, result, _ = fixture()
        expected['camera_owner']['birth_ticks'] = '100'
        with self.assertRaisesRegex(ValueError, 'owner differs'):
            self.current(snapshot, expected, intent, result)

    def test_current_sface_noncompleted_counter_regression_is_rejected(self):
        snapshot, expected, intent, result, _ = fixture()
        intent['prestop_bounds']['sface']['slot_denials'] = 2
        with self.assertRaisesRegex(ValueError, 'SFace counter regressed: slot_denials'):
            self.current(snapshot, expected, intent, result)

    def test_current_optional_native_counter_regression_is_rejected(self):
        snapshot, expected, intent, result, document = fixture()
        intent['prestop_bounds']['optional']['yunet']['not_submitted'] = 1
        document['auxiliary']['inherited_optional']['yunet']['not_submitted'] = 1
        expected['checkpoint_pin'] = snapshot.put(candidate.CHECKPOINT, document)
        with self.assertRaisesRegex(ValueError, 'Native task counter regressed'):
            self.current(snapshot, expected, intent, result)

    def test_archived_semantic_error_is_rejected_even_with_consistent_fresh_hashes(self):
        snapshot, expected, _, _, document = fixture(lambda cp: cp['seed']['completed'].__setitem__(1, 1001))
        with self.assertRaisesRegex(ValueError, 'Archived completion exceeds admitted work'):
            candidate.validate_chain(document, expected['history'], snapshot, protection, boot_module)

    def test_archived_pending_result_is_rejected(self):
        snapshot, expected, _, _, document = fixture(lambda cp: cp['auxiliary']['pending_result_tokens'].__setitem__(2, 1))
        with self.assertRaisesRegex(ValueError, 'Archived owner was not confirmed quiescent'):
            candidate.validate_chain(document, expected['history'], snapshot, protection, boot_module)

    def test_unknown_archive_schema_is_rejected_with_matching_hash(self):
        snapshot, expected, _, _, document = fixture(archive_schema='unknown-archive')
        with self.assertRaisesRegex(ValueError, 'Unknown archive schema'):
            candidate.validate_chain(document, expected['history'], snapshot, protection, boot_module)

    def test_v2_chain_cannot_silently_omit_previous_history(self):
        snapshot, expected, _, _, document = fixture(lambda cp: cp.pop('previous_kernel_history'))
        with self.assertRaisesRegex(ValueError, 'truncated before legacy'):
            candidate.validate_chain(document, expected['history'], snapshot, protection, boot_module)

    def test_declared_short_length_does_not_truncate_traversal_successfully(self):
        snapshot, expected, _, _, document = fixture()
        expected['history']['archive_count'] = 1
        expected['history']['archives'] = expected['history']['archives'][:1]
        with self.assertRaisesRegex(ValueError, 'truncated or bounded traversal'):
            candidate.validate_chain(document, expected['history'], snapshot, protection, boot_module)

    def test_declared_extra_length_does_not_accept_early_legacy(self):
        snapshot, expected, _, _, document = fixture()
        expected['history']['archive_count'] = 3
        expected['history']['archives'].append(copy.deepcopy(expected['history']['archives'][-1]))
        with self.assertRaisesRegex(ValueError, 'Early terminal'):
            candidate.validate_chain(document, expected['history'], snapshot, protection, boot_module)

    def test_repeated_boot_cycle_is_rejected_with_consistent_edge_pins(self):
        snapshot, expected, _, _, document = fixture()
        head = document['previous_kernel_history']
        original = json.loads(snapshot.read(head['archive_path']))
        original['source_boot'] = CURRENT
        data = candidate.canonical(original)
        snapshot.files[head['archive_path']] = data
        head.update(source_boot=CURRENT, archive_sha256=candidate.sha(data))
        expected['history']['archives'][0].update(source_boot=CURRENT, sha256=candidate.sha(data))
        with self.assertRaisesRegex(ValueError, 'Boot cycle'):
            candidate.validate_chain(document, expected['history'], snapshot, protection, boot_module)

    def test_probe_progress_reset_requires_new_fault_or_attempt_generation(self):
        _, _, intent, _, document = fixture()
        for task in ('yunet', 'sface'):
            intent['prestop_bounds']['optional'][task]['recovery']['probe_successes'] = 3
        with self.assertRaisesRegex(ValueError, 'Same-generation'):
            candidate.current_bounds(document['seed'], document['auxiliary'], intent, protection)
        for index, task in enumerate(('yunet', 'sface')):
            document['seed']['recovery'][index]['faults'] = 1
            document['auxiliary']['inherited_optional'][task]['recovery']['faults'] = 1
        candidate.current_bounds(document['seed'], document['auxiliary'], intent, protection)


if __name__ == '__main__':
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FreshHistoryChecks))
    (HERE / 'FRESH_FINAL_HISTORY_TESTS.log').write_text(output.getvalue(), encoding='utf-8')
    report = dict(tests_run=result.testsRun, passed=result.wasSuccessful(), failures=len(result.failures), errors=len(result.errors),
                  candidate_sha256=hashlib.sha256((HERE / 'validate_fresh_final_history_readonly.py').read_bytes()).hexdigest(),
                  exact_original_pure_validators_used=['load_business_checkpoint', 'make_native_seed', '_sealed_source', '_legacy_source'],
                  real_board_cli_or_original_modules_loader_run=False, real_checkpoint_marker_proc_or_service_io=False,
                  native_context_or_aura_cdll_created=False, synthetic_metadata_only=True)
    (HERE / 'FRESH_FINAL_HISTORY_TESTS.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
    if not result.wasSuccessful():
        print(output.getvalue())
        raise SystemExit(1)
