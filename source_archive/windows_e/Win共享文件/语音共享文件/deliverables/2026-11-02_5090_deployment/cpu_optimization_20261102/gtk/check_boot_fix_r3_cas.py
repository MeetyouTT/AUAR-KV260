"""Two local RAM cases for the observed active-ledger CAS gap only.

Runs exact source_snapshot/pin/bind_camera ASTs with synthetic files and explicit
stubs for every live stage. No package import, CLI, transport or actual I/O.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import types

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / 'boot_review_inputs/observed_revision3/candidate'
SOURCE = BASELINE / 'boot_recovery.py'
RAW = SOURCE.read_bytes()
EXPECTED_SHA = 'e60d8f4ebf32f7ed738789d8e79a1e25d80881cb03fda90e5217880c3d70b9b7'
assert hashlib.sha256(RAW).hexdigest() == EXPECTED_SHA
tree = ast.parse(RAW)
klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Recovery')
methods = [node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name in ('pin', 'source_snapshot', 'bind_camera')]
assert len(methods) == 3
rules_raw = (BASELINE / 'recovery_rules.py').read_bytes()
assert hashlib.sha256(rules_raw).hexdigest() == '72492c2d50c746b2f26b3292beff189bd76d7d39be04515baab13dbc881c7284'
rules = {}
exec(compile(rules_raw, '<pure-recovery-rules>', 'exec'), rules)
BOOT = '10000000-0000-4000-8000-000000000001'
OLD_BOOT = '20000000-0000-4000-8000-000000000002'
new_owner = dict(pid=700, birth_ticks='111', command_sha256='a' * 64)
old_owner = dict(pid=600, birth_ticks='99', command_sha256='b' * 64)
results = []
for inject in (False, True):
    files, directories, cas_calls = {}, set(), []

    class MemoryPath(PurePosixPath):
        def exists(self):
            return str(self) in files or str(self) in directories

        def mkdir(self, **kwargs):
            assert not self.exists()
            directories.add(str(self))

    def regular(path, limit=67108864):
        return files[str(path)]

    def create(path, raw):
        assert str(path) not in files
        files[str(path)] = raw

    def replace_known(path, before, after):
        assert regular(path) == before
        cas_calls.append({'path': str(path), 'before_sha256': rules['digest'](before)})
        files[str(path)] = after

    state = MemoryPath('/synthetic/state')
    aura = MemoryPath('/synthetic/runtime/aura')
    startup_path = MemoryPath('/synthetic/startup.json')
    ui_path = aura / 'config/board_avatar_gtk.json'
    active_path = state / 'active-source.json'
    ops = MemoryPath('/synthetic/ops')
    run = ops / ('native-run-' + BOOT + '-700/config.json')
    checkpoint = MemoryPath('/synthetic/native-checkpoint.json')
    camera_sources = {'/synthetic/old-run/config.json': rules['digest'](b'old config'),
                      '/synthetic/camera.py': rules['digest'](b'original camera')}
    for path, raw in (('/synthetic/old-run/config.json', b'old config'), ('/synthetic/camera.py', b'original camera'),
                      (aura / 'gtk.py', b'latest synthetic GTK'), (aura / 'identity.py', b'latest synthetic identity')):
        files[str(path)] = raw
    selected = dict(board_boot_id=OLD_BOOT, camera_pid=old_owner['pid'], camera_start_ticks=old_owner['birth_ticks'],
                    camera_cmdline_sha256=old_owner['command_sha256'], camera_config='/synthetic/old-run/config.json',
                    source_sha256=camera_sources, model_policy='KEEP', identity_policy={'gallery': 'SYNTHETIC_KEEP'})
    selected_raw = rules['encoded'](selected)
    selected_pin = dict(path='/synthetic/selected.json', sha256=rules['digest'](selected_raw))
    files[selected_pin['path']] = selected_raw
    files[str(ui_path)] = rules['encoded'](dict(board_business={'face_readback': selected_pin}, identity_policy='KEEP'))
    startup = dict(runtime='/synthetic/runtime', component_sha256={
        'config/board_avatar_gtk.json': rules['digest'](files[str(ui_path)]),
        'gtk.py': rules['digest'](files[str(aura / 'gtk.py')]),
        'identity.py': rules['digest'](files[str(aura / 'identity.py')])}, later_legitimate_setting='KEEP')
    files[str(startup_path)] = rules['encoded'](startup)
    active_before = dict(contract_sha256='8' * 64, startup_sha256=rules['digest'](files[str(startup_path)]),
                         ui_sha256=rules['digest'](files[str(ui_path)]), selected_pin=selected_pin,
                         selected_sources=camera_sources, predecessor={'boot_id': OLD_BOOT, 'camera_owner': old_owner},
                         transaction='/synthetic/prior-publication')
    active_before_raw = rules['encoded'](active_before)
    files[str(active_path)] = active_before_raw
    newer_active = copy.deepcopy(active_before)
    newer_active['transaction'] = '/synthetic/concurrent-newer-publication'
    newer_active_raw = rules['encoded'](newer_active)
    assert newer_active_raw != active_before_raw
    files[str(run)] = rules['encoded']({'native_execution': {'source_manifest': '/synthetic/native-manifest.json',
        'source_manifest_sha256': '1' * 64, 'checkpoint_output': str(checkpoint)}})
    gate = dict(boot_id=BOOT, contract_sha256='8' * 64, checkpoint_sha256='6' * 64,
                predecessor={'boot_id': OLD_BOOT, 'camera_owner': old_owner})
    scope = dict(json=json, Path=MemoryPath, STATE_ROOT=state, CHECKPOINT=checkpoint,
                 os=types.SimpleNamespace(getpid=lambda: 777, path=types.SimpleNamespace(lexists=lambda path: str(path) in files)), regular=regular, create=create,
                 replace_known=replace_known, original_verify=lambda aura, binding: None,
                 process=lambda pid: copy.deepcopy(new_owner),
                 unit=lambda name: {'MainPID': '0', 'ActiveState': 'activating', 'SubState': 'start-pre', 'ControlPID': '777'},
                 **{name: rules[name] for name in ('GUI', 'require', 'digest', 'encoded', 'config_patch', 'make_binding', 'verify_bootstrap_handoff')})
    exec(compile(ast.Module(body=copy.deepcopy(methods), type_ignores=[]), '<exact-source-snapshot-and-bind-camera>', 'exec'), scope)
    recovery = types.SimpleNamespace(
        contract_sha='8' * 64, boot=BOOT, activation={'installed_files': {}},
        contract=dict(startup_path=str(startup_path), runtime_aura=str(aura), component_count=3,
                      immutable_files={}, original_units={}, native_ops_root=str(ops),
                      native_manifest={'path': '/synthetic/native-manifest.json', 'sha256': '1' * 64}),
        tx=state / 'boots' / BOOT, prepared=lambda: None)
    files[str(recovery.tx / 'current-camera-gate.json')] = rules['encoded'](gate)
    recovery.pin = types.MethodType(scope['pin'], recovery)
    counter = [0]

    def source_snapshot(self):
        counter[0] += 1
        if inject and counter[0] == 2:
            files[str(active_path)] = newer_active_raw
        return scope['source_snapshot'](self)

    recovery.source_snapshot = types.MethodType(source_snapshot, recovery)
    recovery.camera_samples = lambda: (copy.deepcopy(new_owner), {'dpu_schedule': {'protection_handoff': dict(
        mode='native_new_kernel_boot', seed_sha256='6' * 64, current_boot=BOOT,
        source_boot=OLD_BOOT, source_pid=old_owner['pid'], source_birth_ticks=int(old_owner['birth_ticks']))}})
    saved_ui, saved_startup = files[str(ui_path)], files[str(startup_path)]
    outcome, reason = None, None
    try:
        outcome = scope['bind_camera'](recovery)
    except rules['Hold'] as exc:
        reason = str(exc)
    intent_path = recovery.tx / 'binding-700-111/intent.json'
    intent = json.loads(files[str(intent_path)])
    assert intent['active_before_sha256'] == rules['digest'](active_before_raw)
    committed = recovery.tx / 'binding-700-111/committed.json'
    if inject:
        assert reason == 'SOURCE_CHANGED_BEFORE_BINDING_CAS'
        assert not cas_calls
        assert files[str(active_path)] == newer_active_raw
        assert files[str(ui_path)] == saved_ui and files[str(startup_path)] == saved_startup
        assert str(committed) not in files
        assert counter[0] == 2
    else:
        assert reason is None and outcome['status'] == 'ORIGINAL_VERIFIER_CURRENT_BINDING_COMMITTED'
        ledger_call = next(row for row in cas_calls if row['path'] == str(active_path))
        assert ledger_call['before_sha256'] == intent['active_before_sha256']
        assert str(committed) in files and counter[0] == 3
    results.append({'case': 'newer_ledger_after_prior_snapshot' if inject else 'unchanged_baseline',
                    'passed': True, 'outcome_status': outcome['status'] if outcome else reason,
                    'source_snapshot_calls': counter[0],
                    'intent_active_before_sha256': intent['active_before_sha256'],
                    'CAS_target_write_count': len(cas_calls),
                    'UI_unchanged': files[str(ui_path)] == saved_ui,
                    'startup_unchanged': files[str(startup_path)] == saved_startup,
                    'intervening_newer_ledger_preserved': files[str(active_path)] == newer_active_raw if inject else None,
                    'committed_record_present': str(committed) in files})
assert SOURCE.read_bytes() == RAW
manage = BASELINE / 'manage_installation.py'
manage_sha = hashlib.sha256(manage.read_bytes()).hexdigest()
assert manage_sha == 'de31f75b2aac3296861cbdb80a075dd5f3762eff93d885a8c6b9af95462ad975'
report = {
    'schema': 'aura-boot-fix-r3-cas-independent-recheck-1',
    'verdict': 'PASS_B03_ACTIVE_LEDGER_CAS_FIX_OFFLINE_ONLY',
    'candidate_sha256': EXPECTED_SHA,
    'rules_sha256': hashlib.sha256(rules_raw).hexdigest(),
    'unchanged_manage_installation_sha256': manage_sha,
    'snapshot': str(BASELINE.parent / 'SNAPSHOT.json'),
    'snapshot_sha256': hashlib.sha256((BASELINE.parent / 'SNAPSHOT.json').read_bytes()).hexdigest(),
    'tested_exact_methods': ['Recovery.pin', 'Recovery.source_snapshot', 'Recovery.bind_camera'],
    'cases_run': 2, 'results': results,
    'source_review': {
        'source_snapshot_lines': [220, 221, 222, 223, 253],
        'publication_lines': [595, 596, 605, 606, 607, 610, 611, 618, 619, 621, 622, 624, 625],
        'finding': 'Exact source_snapshot now retains raw active ledger bytes and existence. Before any UI/startup replace, bind_camera recaptures and checks both against the initial snapshot. Existing-ledger publication uses the original captured raw bytes, and absence uses lexists plus O_EXCL create. A final full source snapshot is compared before the committed record. The original reproduced drift is refused before either original UI/startup target is touched.'
    },
    'fixture_adaptations_only': ['Use observed_revision3 exact pinned methods/rules.', 'Stub os.path.lexists against the same RAM file map so the real new source_snapshot returns active_source_raw/present.', 'Change expected drift result to HOLD and assert zero target CAS calls plus unchanged original UI/startup and preserved intervening ledger.'],
    'baseline_behavior': 'Unchanged case commits and its ledger expected SHA equals intent.active_before_sha256.',
    'B03_resolved': True,
    'commit_gap_manual_HOLD_limitation_preserved': {
        'prior_evidence': str(HERE / 'BOOT_BINDING_COMMIT_GAP_CASE.json'),
        'prior_evidence_sha256': hashlib.sha256((HERE / 'BOOT_BINDING_COMMIT_GAP_CASE.json').read_bytes()).hexdigest(),
        'status': 'SAFE_HOLD_RECOVERY_COMPLETENESS_LIMITATION_UNCHANGED',
        'locations': {'boot_recovery.py': [619, 622, 626], 'manage_installation.py': [240, 241, 242, 243]},
        'finding': 'manage_installation is unchanged. Crash after active ledger publication but before committed record can still require manual reconciliation; no presealed active-after ledger was added and already-current reentry does not write the missing committed record. This result does not claim automatic rollback coverage for that point.'
    },
    'scope': 'Only the original baseline and ledger-drift RAM cases. Exact ASTs with explicit prepared/health/original metadata verifier/process/unit/filesystem stubs; no real Native approval. The65 baseline was not rerun and its receipt was not reassigned to revision3.',
    'remaining_external_gates': ['Fresh dpu-auto-config merged unit/helper source and ordering proof or actual absence remains required.', 'Fresh exclusive handoff and actual source/owner/platform/Native/systemd/READY evidence remain required.'],
    'candidate_or_author_files_modified': False,
    'board_SSH_HTTP_model_or_real_store_access': False,
    'production_or_Native_execution_authorized': False,
    'full65_suite_rerun': False,
    'cross_conversation_messages_sent': False,
}
with (HERE / 'BOOT_FIX_R3_CAS_RECHECK.json').open('x', encoding='utf-8') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps({'verdict': report['verdict'], 'candidate_sha256': EXPECTED_SHA, 'cases': results,
                  'report_sha256': hashlib.sha256((HERE / 'BOOT_FIX_R3_CAS_RECHECK.json').read_bytes()).hexdigest()}))
