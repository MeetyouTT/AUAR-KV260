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
BASELINE = HERE / 'boot_cas_review_current_cut'
SOURCE = BASELINE / 'candidate__boot_recovery.py.bin'
RAW = SOURCE.read_bytes()
EXPECTED_SHA = '15e4f53f981603dff3d10bb1c53272c479a9b97d557f539f8f9a31ffa6b601d7'
assert hashlib.sha256(RAW).hexdigest() == EXPECTED_SHA
tree = ast.parse(RAW)
klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Recovery')
methods = [node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name in ('pin', 'source_snapshot', 'bind_camera')]
assert len(methods) == 3
rules_raw = (BASELINE / 'candidate__recovery_rules.py.bin').read_bytes()
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
                 os=types.SimpleNamespace(getpid=lambda: 777), regular=regular, create=create,
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
    outcome = scope['bind_camera'](recovery)
    intent_path = recovery.tx / 'binding-700-111/intent.json'
    intent = json.loads(files[str(intent_path)])
    ledger_call = next(row for row in cas_calls if row['path'] == str(active_path))
    assert intent['active_before_sha256'] == rules['digest'](active_before_raw)
    if inject:
        assert ledger_call['before_sha256'] == rules['digest'](newer_active_raw)
        assert ledger_call['before_sha256'] != intent['active_before_sha256']
        assert files[str(active_path)] != newer_active_raw
    results.append({'case': 'newer_ledger_after_prior_snapshot' if inject else 'unchanged_baseline',
                    'outcome_status': outcome['status'], 'source_snapshot_calls': counter[0],
                    'intent_active_before_sha256': intent['active_before_sha256'],
                    'actual_ledger_CAS_expected_sha256': ledger_call['before_sha256'],
                    'expected_matches_transaction_before': ledger_call['before_sha256'] == intent['active_before_sha256'],
                    'newer_ledger_overwritten': inject and files[str(active_path)] != newer_active_raw})
assert SOURCE.read_bytes() == RAW
report = {'candidate_sha256': EXPECTED_SHA, 'results': results,
          'specific_gap_reproduced': results[1]['newer_ledger_overwritten'],
          'scope': 'Two pure in-memory cases. Exact bind_camera/source_snapshot/pin AST with original pure recovery_rules. All live readiness/stage/metadata-verifier/process/unit/IO surfaces explicitly stubbed; no Native validation claim or board/local production action.',
          'candidate_modified': False}
with (HERE / 'BOOT_ACTIVE_LEDGER_CAS_NEGATIVE_CURRENT.json').open('x', encoding='utf-8') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps(report))
