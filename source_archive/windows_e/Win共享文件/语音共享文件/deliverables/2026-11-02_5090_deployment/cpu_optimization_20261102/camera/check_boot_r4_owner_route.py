"""Directed R4 recheck only: reused R3 RAM late-stop fault and four mode cases.
No author/runtime import, full-suite rerun, or real board/file/service operation.
"""
import ast
import copy
import hashlib
import http.client
import json
from pathlib import Path, PurePosixPath
import types

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / 'boot_review_inputs/observed_revision4/candidate'
RUNTIME_SHA = '28ffa2545cf9327da72a7a4d6c583923957f784c8f5c2d8d12571bddc3e00a5e'
RULE_SHA = '55bfc4db498be172beb040605dcae351c6f972e0df1371cecb48b7d1034ed268'
runtime_raw = (INPUT / 'boot_recovery.py').read_bytes()
rule_raw = (INPUT / 'recovery_rules.py').read_bytes()
assert hashlib.sha256(runtime_raw).hexdigest() == RUNTIME_SHA
assert hashlib.sha256(rule_raw).hexdigest() == RULE_SHA
rules = {}; exec(compile(ast.parse(rule_raw), '<frozen-R4-pure-rules>', 'exec'), rules)
methods = [node for node in ast.walk(ast.parse(runtime_raw)) if isinstance(node, ast.FunctionDef)
           and node.name in ('source_snapshot', 'camera_samples', 'check_camera_live', 'bind_camera')]
BOOT = '10000000-0000-4000-8000-000000000001'
OLD = '20000000-0000-4000-8000-000000000002'
OWNER = dict(pid=900, birth_ticks='99', command_sha256='d' * 64)

# Reuse the prior small RAM fixture. Only expose R4's additional method and
# retain diagnostic state on the now-expected HOLD; do not execute R3 tests.
fixture_raw = (HERE / 'check_boot_r3_owner_recheck.py').read_bytes()
tree = ast.parse(fixture_raw)
node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == 'run_case')
source = ast.get_source_segment(fixture_raw.decode(), node)
needle = "for name in ('source_snapshot', 'camera_samples', 'bind_camera')"
assert source.count(needle) == 1
source = source.replace(needle, "for name in ('source_snapshot', 'camera_samples', 'check_camera_live', 'bind_camera')")
needle = '    result = obj.bind_camera()\n'
assert source.count(needle) == 1
source = source.replace(needle, """    try:
        result = obj.bind_camera()
    except rules['Hold'] as error:
        return dict(fault_after_two_healthy_samples=flip_after_sampling, samples=phase['samples'],
            result='HOLD', reason=str(error), replacements=replacements,
            active_ledger_written_in_RAM=str(root/'active-source.json') in files,
            committed_receipt_written_in_RAM=any(name.endswith('/committed.json') for name in files),
            stopping_unit_metadata_observed_after_sampling=sum(value['ActiveState']=='deactivating' for value in unit_reads),
            owner_fingerprint_remained=OWNER, full_source_snapshot_method_executed=True,
            original_b77_verifier_and_prepared_prerequisites_stubbed=True)
""")
exec(compile(source, '<reused-small-RAM-fixture-for-R4>', 'exec'), globals())
owner_results = [run_case(False), run_case(True)]
assert owner_results[0]['result'] == 'ORIGINAL_VERIFIER_CURRENT_BINDING_COMMITTED'
fault = owner_results[1]
assert fault['result'] == 'HOLD' and fault['reason'] == 'CAMERA_LIFECYCLE_CHANGED_NO_BINDING_OR_READY'
assert not fault['replacements'] and not fault['active_ledger_written_in_RAM'] and not fault['committed_receipt_written_in_RAM']

mode_results = []
for same_boot, provided_mode, accept in (
        (False, 'native_new_kernel_boot', True), (False, 'native_exact_same_boot', False),
        (True, 'native_exact_same_boot', True), (True, 'native_new_kernel_boot', False)):
    prior_boot = BOOT if same_boot else OLD
    gate = dict(boot_id=BOOT, contract_sha256='c'*64, checkpoint_sha256='b'*64,
                predecessor=dict(boot_id=prior_boot, camera_owner=OWNER))
    handoff = dict(mode=provided_mode, seed_sha256='b'*64, source_pid=900, source_birth_ticks=99,
                   current_boot=BOOT, source_boot=prior_boot)
    accepted, reason = False, None
    try:
        rules['verify_bootstrap_handoff'](handoff, gate, BOOT, 'c'*64); accepted = True
    except rules['Hold'] as error:
        reason = str(error)
    assert accepted == accept
    if not accept:
        assert reason == 'ORIGINAL_BOOTSTRAP_MODE_DIFFERS_FROM_ACTUAL_BOOT_ROUTE'
    mode_results.append(dict(same_boot=same_boot, provided_mode=provided_mode, expected_accept=accept,
                             accepted=accepted, rejection=reason, passed=True))

report = dict(schema='aura-boot-r4-owner-route-targeted-probes-1', runtime_sha256=RUNTIME_SHA, rules_sha256=RULE_SHA,
    owner_cases=owner_results, boot_mode_cases=mode_results, all_directed_expectations_passed=True,
    old65_or_full_suites_rerun=False, real_b77_verifier_or_Native_loader_executed=False,
    all_target_mutations_in_RAM_only=True, board_SSH_HTTP_proc_model_DB_or_service_access=False,
    author_or_production_files_modified=False, cross_dialogue_messages_sent=False,
    original_history_gate_integration_not_approved=True)
(HERE / 'BOOT_FIX_R4_OWNER_ROUTE_PROBES.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2))
