"""API/field and one guard compatibility check, with no history traversal."""
import ast
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import types

HERE = Path(__file__).resolve().parent
OPT = HERE.parent
R5 = OPT / 'boot_review_inputs/observed_revision5/candidate'
R4 = OPT / 'boot_review_inputs/observed_revision4/candidate'
ADAPTER = OPT / 'camera/validate_fresh_final_history_readonly.py'
NATIVE_BOOT = OPT / 'camera/baseline/251e9660633c__native_boot.py'
NATIVE_PROTECTION = OPT / 'camera/baseline/b8637c2aa387__native_protection.py'
STARTUP = OPT / 'camera/baseline/4a729a29c6e4__native_startup.py'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, expected=None):
    raw = path.read_bytes()
    if expected:
        assert sha(raw) == expected
    return raw


adapter_raw = pinned(ADAPTER, '5ca99d4231c686de0f89dac5792299bec13af517a5c6e2b8f73c4cc66b9285c9')
gate_raw = pinned(R5 / 'original_history_gate.py', '735b0fb2f9bf696765c781f8f8573e8a368dacf916c58f5b0e556d1cde0e16d8')
r4_raw = pinned(R4 / 'original_history_gate.py', '3d61597400fec5506c94645d4bdc1ec1ae0aa4531e886619a1c50b06a11c32d6')
runtime_raw = pinned(R5 / 'boot_recovery.py', '36970f82a694da89c42189f315047b8e9a1f8f877b5ffdc15b71543c376c8c0b')
capture_raw = pinned(R5 / 'capture_contract.py', 'bce6d4d1b2f7547827f9f886014297d1483c1eb8a8b99ef6cf04421cd1b5562c')
rules_raw = pinned(R5 / 'recovery_rules.py', '55bfc4db498be172beb040605dcae351c6f972e0df1371cecb48b7d1034ed268')
native_boot_raw = pinned(NATIVE_BOOT, '251e9660633cd6c50d0874e263899155895372d8b8e0db4d6ecdbfca7901d4a7')
native_protection_raw = pinned(NATIVE_PROTECTION, 'b8637c2aa387915a49ef0fd7a1c7cb9d015fb71802c4eaa11539a64466db1faa')
pinned(STARTUP, '4a729a29c6e4c5d8e89c084867f8c7b972e38e4cf1a74177250cbb31a0396fcf')


def function(raw, name):
    return next(n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name == name)


def require(value, message):
    if not value:
        raise ValueError(message)


BOOT = '10000000-0000-4000-8000-000000000001'
PREVIOUS = '20000000-0000-4000-8000-000000000002'
OLDER = '30000000-0000-4000-8000-000000000003'
checkpoint_pin = {'path': '/synthetic/final.json', 'sha256': '8' * 64}
source_owner = {'pid': 700, 'birth_ticks': '111', 'command_sha256': 'a' * 64}
head = {'archive_path': '/synthetic/archive/previous.json', 'archive_sha256': '1' * 64,
        'source_boot': OLDER, 'source_checkpoint_sha256': '2' * 64, 'history_is_lower_bound': True}
history = {'head': head, 'archive_count': 1, 'archives': [{'path': head['archive_path'], 'sha256': head['archive_sha256'],
           'current_boot': BOOT, 'source_boot': OLDER, 'source_checkpoint_sha256': '2' * 64, 'history_is_lower_bound': True}],
           'legacy_pin': {'path': '/synthetic/legacy.json', 'sha256': '3' * 64}}
expected_pin = {'path': '/synthetic/expected.json', 'sha256': '7' * 64}
expected = dict(boot_id=BOOT, checkpoint_pin=checkpoint_pin, camera_owner=source_owner,
                owner_run_config_pin={'path': '/synthetic/run/config.json', 'sha256': '4' * 64},
                source_manifest_pin={'path': '/synthetic/manifest.json', 'sha256': '5' * 64},
                history=dict(copy.deepcopy(history), observed_mono_ns=100,
                             provenance_pin={'path': '/synthetic/provenance.json', 'sha256': '6' * 64}))

# Evaluate only the exact success-output dictionary expression from original main.
# No original main, guard, loader, reader or archive traversal is called here.
main_node = function(adapter_raw, 'main')
printed = next(n for n in ast.walk(main_node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'print')
output_dict = printed.args[0].args[0]
literal_globals = {}
for node in ast.parse(adapter_raw).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('SOURCE_UNIT', 'FEATURES', 'OPTIONAL_COUNTERS', 'RECOVERY_TOTALS'):
        literal_globals[node.targets[0].id] = ast.literal_eval(node.value)
success = eval(compile(ast.Expression(copy.deepcopy(output_dict)), '<exact-original-success-fields>', 'eval'),
               dict(expected=expected, args=types.SimpleNamespace(expected_sha256=expected_pin['sha256']), records=history['archives'], **literal_globals))
calls = []


class Snapshot:
    def pinned(self, pin):
        assert pin == expected_pin
        return copy.deepcopy(expected)

    def unchanged(self):
        calls.append('unchanged')


def main_output_fixture():
    assert sys.argv[1:] == ['--expected', expected_pin['path'], '--expected-sha256', expected_pin['sha256']]
    calls.append('output-projection-only')
    print(json.dumps(success))


facade = types.SimpleNamespace(Snapshot=Snapshot, main=main_output_fixture)
request = dict(schema='aura-original-history-gate-request-1', boot_id=BOOT, kind='same_boot_resume', history_expected=history,
               checkpoint_pin=checkpoint_pin, source_owner=source_owner, normal_stop_expected_pin=expected_pin)
scope = dict(require=require, sys=sys, io=io, contextlib=contextlib, json=json, Path=Path,
             ADAPTER_SHA=sha(adapter_raw))
exec(compile(ast.Module(body=[copy.deepcopy(function(gate_raw, 'execute_request'))], type_ignores=[]), '<exact-r5-execute-request>', 'exec'), scope)
result = scope['execute_request'](facade, request, '9' * 64, BOOT)
assert result['original_same_boot_result'] == success
r4_scope = dict(scope)
exec(compile(ast.Module(body=[copy.deepcopy(function(r4_raw, 'execute_request'))], type_ignores=[]), '<exact-r4-execute-request>', 'exec'), r4_scope)
r4_reason = None
try:
    r4_scope['execute_request'](facade, request, '9' * 64, BOOT)
except ValueError as exc:
    r4_reason = str(exc)
assert r4_reason == 'Same-boot proof is not bound to the exact final/owner/history'

# Exact existing guard, failing before any owner scan or file read beyond boot.
seen_units = []


class BootPath:
    def __init__(self, path):
        assert path == '/proc/sys/kernel/random/boot_id'

    def read_text(self):
        return BOOT


def show(name):
    seen_units.append(name)
    value = dict(MainPID='0', ActiveState='inactive', SubState='dead', Job='', Result='success', ExecMainStatus='0',
                 Restart='no', SendSIGKILL='no', TimeoutStopUSec='infinity', KillMode='process')
    if name == 'aura-camera-ui.service':
        value.update(ActiveState='activating', SubState='start-pre', Job='77')
    return value


guard_scope = dict(require=require, Path=BootPath, show=show)
exec(compile(ast.Module(body=[copy.deepcopy(function(adapter_raw, 'guard'))], type_ignores=[]), '<exact-existing-guard>', 'exec'), guard_scope)
guard_reason = None
try:
    guard_scope['guard']({'boot_id': BOOT})
except ValueError as exc:
    guard_reason = str(exc)
assert guard_reason == 'Original service not normally stopped'
assert seen_units == ['aura-avatar-ui.service', 'aura-camera-ui.service']

# Exact two marker payload expressions from the original writers, with no writes.
consume = function(native_protection_raw, 'consume_checkpoint')
same_marker_expression = next(n.value for n in ast.walk(consume) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'raw' for t in n.targets))
same_marker = eval(compile(ast.Expression(copy.deepcopy(same_marker_expression)), '<original-consume-payload>', 'eval'), {'loaded': {'sha256': checkpoint_pin['sha256']}})
commit = function(native_boot_raw, 'commit_new_boot')
new_record_expression = next(n.value for n in ast.walk(commit) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'record' for t in n.targets))
rules_scope = dict(copy=copy, require=require)
exec(compile(ast.Module(body=[copy.deepcopy(function(rules_raw, 'next_history_expected'))], type_ignores=[]), '<exact-next-history>', 'exec'), rules_scope)
runtime_class = next(n for n in ast.parse(runtime_raw).body if isinstance(n, ast.ClassDef) and n.name == 'Recovery')
accepted = next(n for n in runtime_class.body if isinstance(n, ast.FunctionDef) and n.name == 'accepted_live_history')
marker_cases = []
for mode in ('same_boot', 'new_kernel'):
    previous = copy.deepcopy(history)
    predecessor_boot = BOOT if mode == 'same_boot' else PREVIOUS
    previous['archives'][0]['current_boot'] = predecessor_boot
    gate = dict(predecessor={'boot_id': predecessor_boot}, checkpoint_sha256=checkpoint_pin['sha256'], history_proof={'history_expected': previous})
    handoff = {'previous_kernel_history': copy.deepcopy(previous['head'])}
    marker_path = '/synthetic/domain-marker'
    if mode == 'new_kernel':
        new_head = dict(archive_path='/synthetic/archive/current.json', archive_sha256='c' * 64, source_boot=PREVIOUS,
                        source_checkpoint_sha256=checkpoint_pin['sha256'], history_is_lower_bound=False)
        handoff.update(previous_kernel_history=new_head, archive_path=new_head['archive_path'], archive_sha256=new_head['archive_sha256'])
        marker_record = eval(compile(ast.Expression(copy.deepcopy(new_record_expression)), '<original-newboot-marker-record>', 'eval'),
            dict(boot=BOOT, loaded={'sha256': checkpoint_pin['sha256'], 'seed': {'captured_mono_ns': 100}},
                 archive=PurePosixPath(new_head['archive_path']), archive_sha=new_head['archive_sha256']))
        marker_bytes = json.dumps(marker_record).encode()
    else:
        marker_bytes = same_marker
    cp = PurePosixPath('/synthetic/final.json')
    target = marker_path if mode == 'new_kernel' else str(cp) + '.native-consumed-' + checkpoint_pin['sha256']

    def regular(path, limit=67108864):
        assert str(path) == target and len(marker_bytes) <= limit
        return marker_bytes

    accepted_scope = dict(require=require, json=json, CHECKPOINT=cp, regular=regular,
                          time=types.SimpleNamespace(monotonic_ns=lambda: 500), next_history_expected=rules_scope['next_history_expected'])
    exec(compile(ast.Module(body=[copy.deepcopy(accepted)], type_ignores=[]), '<exact-r5-accepted-live-history>', 'exec'), accepted_scope)
    traces = []
    self = types.SimpleNamespace(boot=BOOT, verify_gate_history=lambda g: traces.append('upstream-proof-placeholder'),
        kernel_marker_path=lambda: marker_path, run_history_gate=lambda kind, hist: {'kind': kind, 'history_expected': copy.deepcopy(hist)})
    accepted_history, proof = accepted_scope['accepted_live_history'](self, gate, handoff)
    assert proof['kind'] == 'running_archive_chain'
    if mode == 'same_boot':
        assert accepted_history == previous
    else:
        assert accepted_history['archive_count'] == previous['archive_count'] + 1
        assert accepted_history['archives'][1:] == previous['archives'] and accepted_history['legacy_pin'] == previous['legacy_pin']
    marker_cases.append({'mode': mode, 'original_writer_payload_accepted': True,
                         'accepted_archive_count': accepted_history['archive_count'], 'complete_old_rows_preserved': True})

evidence = dict(schema='aura-history-gate-r5-api-probes-1', gate_sha256=sha(gate_raw), adapter_sha256=sha(adapter_raw),
                same_boot_output_fields_from_exact_original_main_dictionary=True, R5_four_field_projection_accepts_original_bounds_keys=True,
                R4_extra_history_keys_mismatch_reproduced=r4_reason, original_guard_camera_start_pre_rejection=guard_reason,
                marker_cases=marker_cases, original_archive_traversal_executed=False, original_main_or_native_loader_executed=False,
                board_or_production_IO=False, candidate_modified=False)
with (HERE / 'BOOT_HISTORY_GATE_API_PROBES_R5.json').open('x', encoding='utf-8') as handle:
    json.dump(evidence, handle, indent=2)
    handle.write('\n')
print(json.dumps(evidence))
