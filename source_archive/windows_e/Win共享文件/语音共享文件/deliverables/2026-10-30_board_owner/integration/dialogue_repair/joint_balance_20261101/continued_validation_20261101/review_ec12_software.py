"""Independent local review and public in-memory fixtures; never run a live entry."""
import ast
import hashlib
import io
import json
from pathlib import Path
import types
import unittest

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[5]
REVIEWS = PROJECT / 'deliverables/2026-10-31_visual_axis_maintenance/reviews'
RET = REVIEWS / 'summary_retention_acceptance_20261101'
JOINT = REVIEWS / 'joint_performance_20261101'
NEW = RET / 'probe_ec12'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def assignments(tree):
    return {node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body if isinstance(node, ast.Assign)
            and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ('EXPECTED_STARTUP', 'SOURCE_PINS', 'REMOTE')}


def without_pins(tree):
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.Assign) and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in ('EXPECTED_STARTUP', 'SOURCE_PINS'))]
    return ast.dump(tree, include_attributes=False)


spec_raw = (RET/'package/pause_resume/candidate_spec.json').read_bytes()
assert sha(spec_raw) == 'a7a68059b48540268d40cd233b51bb0df5cd5d3406cba97c1599c79317f8366e'
spec = json.loads(spec_raw)
old_raw = (HERE/'memory_probe/read_target_memory_metadata.py').read_bytes()
new_raw = (NEW/'read_target_memory_metadata.py').read_bytes()
assert sha(old_raw) == 'cbe23506be5c5a5864814537f8cb0770592803437358d31a8e3a9e072052ae6c'
assert sha(new_raw) == 'e0ae0a807db2bdecf6cae166924704d55f5a9b95a9972a8bfb0d96376ebac3df'
old_tree = ast.parse(old_raw.decode(), feature_version=(3, 9))
new_tree = ast.parse(new_raw.decode(), feature_version=(3, 9))
old_values, new_values = assignments(old_tree), assignments(new_tree)
assert new_values['EXPECTED_STARTUP'] == spec['startup_sha256']
assert len(new_values['SOURCE_PINS']) == 8
assert new_values['SOURCE_PINS'] == dict(old_values['SOURCE_PINS'], **{
    'tools/voice_first_recording.py': '54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc'})
assert all(spec['component_sha256'][name] == pin
           for name, pin in new_values['SOURCE_PINS'].items())
assert without_pins(old_tree) == without_pins(new_tree)
frozen_raw = (NEW/'FROZEN_MANIFEST.json').read_bytes()
assert sha(frozen_raw) == '2833afb6e1db6217d9dae1127c44f95293dde0110e3eefda9991f0c9878818ca'
for name, expected in json.loads(frozen_raw)['files'].items():
    data = (NEW/name).read_bytes()
    assert len(data) == expected['bytes'] and sha(data) == expected['sha256']

# The original six tests import the new probe, but only call inspect_connection
# on newly authored :memory: fixtures. __main__ and all hardware paths stay off.
test_raw = (HERE/'memory_probe/test_public_probe.py').read_bytes()
frozen_tests = json.loads((HERE/'memory_probe/FROZEN_HANDOFF_R2.json').read_bytes())
assert sha(test_raw) == frozen_tests['files']['test_public_probe.py']['sha256']
module = types.ModuleType('root_ec12_public_tests')
module.__file__ = str(NEW/'test_public_probe.py')
exec(compile(test_raw, '<frozen-public-metadata-tests>', 'exec'), module.__dict__)
suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.PublicMetadataTests)
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
assert result.testsRun == 6 and result.wasSuccessful(), stream.getvalue()

adapter_raw = (RET/'tools/start_pause_resume_one_turn.py').read_bytes()
assert sha(adapter_raw) == 'e1e8269abea6da9ab021e9c4cae34c1ddb1646f4dbbd65e181e6472a63e1e49b'
base_raw = (JOINT/'tools/start_live_one_turn.py').read_bytes()
adapter_tree = ast.parse(adapter_raw.decode())
base_tree = ast.parse(base_raw.decode())
remote = assignments(adapter_tree)['REMOTE']
base_remote = assignments(base_tree)['REMOTE']
def function_bodies(source):
    result = {}
    for node in ast.parse(source, feature_version=(3, 9)).body:
        if isinstance(node, ast.FunctionDef):
            result.setdefault(node.name, []).append(ast.dump(node, include_attributes=False))
    return result
old_functions, new_functions = function_bodies(base_remote), function_bodies(remote)
assert set(new_functions) == set(old_functions) | {'isolated_observer_print'}
assert all(new_functions[name] == body for name, body in old_functions.items())
observer_raw = (JOINT/'remote/live_observer_caption_accepted.py').read_bytes()
assert sha(observer_raw) == '8ebb76746cb87bd3608671848cc8087d724e24d4282f2933a3c15b4879bd4819'
assert "live_ns={'EXPECTED_STARTUP':STARTUP_SHA,'EXPECTED_BOOT':BOOT,'print':isolated_observer_print}" in remote
assert "'exec'),live_ns)" in remote
assert 'ANSWER_STILL_ACTIVE_CLEANUP_PENDING' in remote
assert 'deadline=time.monotonic()+120' in remote
assert "p.add_argument('--ready-evidence',type=Path,required=True)" in adapter_raw.decode()
assert '--context-evidence' not in adapter_raw.decode()
assert "assert match,'CONTINUE_CHANGED_SCOPE'" in remote
helper_raw = (RET/'remote/selection_scope_metadata.py').read_bytes()
helper_tree = ast.parse(helper_raw.decode(), feature_version=(3, 9))
assert not any(isinstance(node, (ast.ImportFrom, ast.ClassDef)) for node in helper_tree.body)
assert 'os.O_RDONLY | os.O_NOFOLLOW' in helper_raw.decode()
assert "scope_token=hashlib.sha256(('conversation:' + cid).encode()).hexdigest()" in helper_raw.decode()
composition_raw = (RET/'evidence/ec12_observer_combined_public_tests.json').read_bytes()
composition = json.loads(composition_raw)
assert composition['adapter_sha256'] == sha(adapter_raw)
assert composition['tests'] == 6 and composition['passed'] is True
assert composition['failures'] == 0 and composition['errors'] == 0

review = dict(
    schema='aura-root-ec12-local-software-review-1',
    status='LOCAL_SOFTWARE_CHECKS_PASS_LIVE_REQUIRES_AUDIO_HARDWARE_AND_READY',
    spec_sha256=sha(spec_raw), startup_sha256=spec['startup_sha256'],
    probe_sha256=sha(new_raw), probe_manifest_sha256=sha(frozen_raw),
    probe_source_pins=8, probe_only_allowed_constants_changed=True,
    sql_scope_clock_privacy_and_vm_budget_unchanged=True,
    public_probe_tests=dict(tests=result.testsRun, failures=len(result.failures),
                            errors=len(result.errors), passed=result.wasSuccessful(),
                            only_authored_inmemory_sqlite=True),
    observer_adapter_sha256=sha(adapter_raw), observer_sha256=sha(observer_raw),
    original_remote_control_and_graceful_cleanup_unchanged=True,
    hash_only_selection_observation_sha256=sha(helper_raw),
    observer_composition_tests=dict(tests=6, failures=0, errors=0,
        passed=True, evidence_sha256=sha(composition_raw)),
    future_live_observer_conditions=[
        'Only the exclusive existing device owner operates the hardware.',
        'Require a fresh actual READY receipt for ec12 and fresh exact process owners.',
        'Only the frozen accepted-caption observer is available; --ready-evidence is mandatory.',
        'New public seed only after normal current-scope admission; verify the same scope on resume.',
        'Pause after matching full-playback ACK or natural idle; never cancel on sampling timeout.',
        'A new explicit seed request hash is required before authorizing the read-only probe.'],
    hardware_or_model_or_private_database_access=False,
    live_ready_accepted=False, same_scope_recall_accepted=False)
(HERE/'ROOT_EC12_SOFTWARE_REVIEW.json').write_text(
    json.dumps(review, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(HERE/'EC12_PUBLIC_PROBE_TEST_OUTPUT.txt').write_text(stream.getvalue(), encoding='utf-8')
print(json.dumps(review, ensure_ascii=False))
