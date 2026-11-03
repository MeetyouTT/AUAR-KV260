"""Targeted RAM-only checks of the frozen observed_revision2 Native boundary.
Never import the recovery runtime, run65 tests, or use HTTP/proc/services/DSOs.
"""
import ast
import copy
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import types

HERE = Path(__file__).resolve().parent
FROZEN = HERE / 'boot_native_subreview_inputs/current_observed/candidate'
RULE_SHA = '72492c2d50c746b2f26b3292beff189bd76d7d39be04515baab13dbc881c7284'
RUNTIME_SHA = '15e4f53f981603dff3d10bb1c53272c479a9b97d557f539f8f9a31ffa6b601d7'
rule_bytes = (FROZEN / 'recovery_rules.py').read_bytes()
runtime_bytes = (FROZEN / 'boot_recovery.py').read_bytes()
assert hashlib.sha256(rule_bytes).hexdigest() == RULE_SHA
assert hashlib.sha256(runtime_bytes).hexdigest() == RUNTIME_SHA
rules = {}
exec(compile(ast.parse(rule_bytes), '<frozen-pure-recovery-rules>', 'exec'), rules)
spec = importlib.util.spec_from_file_location('boot_native_public_fixture_only', HERE / 'test_fresh_final_history_readonly.py')
fx = importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)
snapshot, expected, _, _, _ = fx.fixture()
archive = json.loads(snapshot.read(expected['history']['archives'][0]['path']))
old_final = copy.deepcopy(archive['checkpoint'])
prior = dict(boot_id=fx.OLD, camera_owner=dict(pid=old_final['seed']['source_pid'],
            birth_ticks=str(old_final['seed']['source_birth_ticks']), command_sha256='a' * 64))

boot_source = (HERE / 'baseline/251e9660633c__native_boot.py').read_bytes()
assert hashlib.sha256(boot_source).hexdigest() == '251e9660633cd6c50d0874e263899155895372d8b8e0db4d6ecdbfca7901d4a7'
api = dict(fx.boot_module.__dict__)
nodes = [node for node in ast.parse(boot_source).body if isinstance(node, ast.FunctionDef)
         and node.name in ('_fresh_seed', 'load_new_boot_checkpoint')]
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<exact-original-new-boot-pure-api>', 'exec'), api)
api.update(checked_boot=lambda value: value,
           marker_paths=lambda directory, boot: (fx.MemoryPath(directory), fx.MemoryPath(directory) / ('kernel-boot-' + boot + '.consumed')),
           time=time, os=types.SimpleNamespace(path=types.SimpleNamespace(lexists=lambda path: '.native-consumed-' in str(path))))
saved_modules = {name: sys.modules.get(name) for name in ('board', 'board.vision', 'board.vision.native_binding')}
for name in ('board', 'board.vision'):
    mod = types.ModuleType(name); mod.__path__ = []; sys.modules[name] = mod
sys.modules['board.vision.native_binding'] = fx.binding


def original_cold_load(document):
    api['_read_pinned'] = lambda pinned: (fx.MemoryPath('/synthetic/final.json'), document)
    return api['load_new_boot_checkpoint']({'path': '/synthetic/final.json', 'sha256': rules['digest'](fx.candidate.canonical(document))},
        boot_id=fx.CURRENT, marker_directory='/synthetic/kernel-history')


def pointer(document, predecessor, consumed=True):
    return rules['verify_final_pointer'](fx.candidate.canonical(document), consumed, predecessor,
        current_boot=fx.CURRENT, allow_new_kernel_boot=True, current_domain_consumed=False)


results = []
try:
    loaded = original_cold_load(old_final)
    normal_sha = pointer(old_final, prior)
    results.append(dict(case='v2_old_checkpoint_marker_route_is_fixed', original_new_boot_loader_accepted=loaded['new_kernel_boot'],
        v2_pointer_accepted=True, current_counter_domain_primary=loaded['seed']['primary_calls'],
        archived_primary=loaded['archive_counters']['primary_calls'], checkpoint_specific_marker_preserved=True))

    last_live = copy.deepcopy(prior)
    last_live['camera_owner'].update(pid=901, birth_ticks='100', command_sha256='b' * 64)
    rejected = None
    try:
        pointer(old_final, last_live)
    except rules['Hold'] as error:
        rejected = str(error)
    assert rejected == 'FINAL_POINTER_WRONG_PREDECESSOR'
    results.append(dict(case='unclean_boot_old_sealed_owner_differs_from_last_live_owner', original_loader_accepted=True,
        v2_rejected=rejected, source_checkpoint_owner=prior['camera_owner'], active_predecessor_last_live_owner=last_live['camera_owner'],
        interpretation='Fail-closed cold coverage gap when shutdown produced no latest final; not an unsafe replay pass'))

    gate = dict(boot_id=fx.CURRENT, contract_sha256='c' * 64, checkpoint_sha256=normal_sha, predecessor=prior)
    wrong_mode = dict(mode='native_exact_same_boot', seed_sha256=normal_sha,
                      source_pid=prior['camera_owner']['pid'], source_birth_ticks=int(prior['camera_owner']['birth_ticks']))
    rules['verify_bootstrap_handoff'](wrong_mode, gate, fx.CURRENT, 'c' * 64)
    results.append(dict(case='same_boot_handoff_mode_for_different_boot_gate', accepted=True,
        source_boot_fields_missing=True, interpretation='Mode is not tied to source/current boot relation'))

    truncated = copy.deepcopy(old_final); truncated.pop('previous_kernel_history')
    loaded_truncated = original_cold_load(truncated)
    truncated_sha = pointer(truncated, prior, consumed=False)
    partial_gate = dict(gate, checkpoint_sha256=truncated_sha)
    metadata = dict(mode='native_new_kernel_boot', seed_sha256=truncated_sha, current_boot=fx.CURRENT,
                    source_boot=fx.OLD, source_pid=prior['camera_owner']['pid'], source_birth_ticks=int(prior['camera_owner']['birth_ticks']))
    rules['verify_bootstrap_handoff'](metadata, partial_gate, fx.CURRENT, 'c' * 64)
    results.append(dict(case='truncated_prior_history_passes_pointer_and_handoff_gate', original_immediate_source_loader_accepted=loaded_truncated['new_kernel_boot'],
        pointer_and_handoff_accepted=True, complete_history_adapter_or_current_bound_receipt_supplied=False,
        interpretation='These metadata gates do not enforce the full accepted archive chain; no real startup/READY is claimed'))
finally:
    for name, saved in saved_modules.items():
        if saved is None: sys.modules.pop(name, None)
        else: sys.modules[name] = saved

method = next(node for node in ast.walk(ast.parse(runtime_bytes)) if isinstance(node, ast.FunctionDef) and node.name == 'camera_samples')
calls = {'samples': 0}
identity = dict(pid=900, birth_ticks='99', command_sha256='d' * 64)


def synthetic_health(port, path):
    calls['samples'] += 1
    return dict(pid=900, board_boot_id=fx.CURRENT, motion_command_emitted=False, identity=dict(ready=True),
                dpu_schedule=dict(native_critical=True, native_abi=2, owner_fenced=False, quiesced=False),
                capture_frames=calls['samples'], detected_frames=calls['samples'])


namespace = dict(CAMERA=rules['CAMERA'], Hold=rules['Hold'], require=rules['require'], http=http,
    unit=lambda name: dict(MainPID='900', ActiveState='deactivating', SubState='stop-sigterm', Job='99 pending-stop'),
    process=lambda pid: identity, get_metadata=synthetic_health,
    time=types.SimpleNamespace(monotonic=lambda: 1.0, sleep=lambda seconds: None))
exec(compile(ast.Module(body=[method], type_ignores=[]), '<exact-frozen-camera_samples-with-RAM-inputs>', 'exec'), namespace)
owner, _ = namespace['camera_samples'](types.SimpleNamespace(boot=fx.CURRENT))
assert owner == identity and calls['samples'] == 2
results.append(dict(case='rebind_camera_samples_accepts_pending_stop', accepted=True, fake_samples=2,
    unit_state=dict(ActiveState='deactivating', SubState='stop-sigterm', Job='99 pending-stop'),
    interpretation='Stable PID/two advancing samples do not prove active/running/noJob during rebinding'))

report = dict(schema='boot-native-subreview-targeted-probes-1', runtime_sha256=RUNTIME_SHA, rules_sha256=RULE_SHA,
    results=results, existing65_tests_rerun=False, existing16_tests_rerun=False,
    all_checkpoint_marker_archive_proc_service_http_IO_in_memory=True, board_or_original_runtime_executed=False,
    original_pure_new_boot_loader_AST_executed=True, native_context_or_aura_cdll_created=False,
    candidate_and_other_branch_files_modified=False, cross_dialogue_messages_sent=False)
(HERE / 'BOOT_NATIVE_SUBREVIEW_PROBES.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
