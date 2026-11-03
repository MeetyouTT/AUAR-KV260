"""One RAM lifecycle fault plus healthy control on exact frozen R3 methods.
No recovery runtime import, service/proc/HTTP access, or original65 suite run.
"""
import ast
import copy
import hashlib
import http.client
import json
from pathlib import Path, PurePosixPath
import types

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / 'boot_review_inputs/observed_revision3/candidate'
RUNTIME_SHA = 'e60d8f4ebf32f7ed738789d8e79a1e25d80881cb03fda90e5217880c3d70b9b7'
RULE_SHA = '72492c2d50c746b2f26b3292beff189bd76d7d39be04515baab13dbc881c7284'
runtime_raw = (INPUT / 'boot_recovery.py').read_bytes()
rule_raw = (INPUT / 'recovery_rules.py').read_bytes()
assert hashlib.sha256(runtime_raw).hexdigest() == RUNTIME_SHA
assert hashlib.sha256(rule_raw).hexdigest() == RULE_SHA
rules = {}; exec(compile(ast.parse(rule_raw), '<frozen-pure-rules>', 'exec'), rules)
methods = [node for node in ast.walk(ast.parse(runtime_raw)) if isinstance(node, ast.FunctionDef)
           and node.name in ('source_snapshot', 'camera_samples', 'bind_camera')]
BOOT = '10000000-0000-4000-8000-000000000001'
OLD = '20000000-0000-4000-8000-000000000002'
OWNER = dict(pid=900, birth_ticks='99', command_sha256='d' * 64)


def run_case(flip_after_sampling):
    files, directories, replacements, unit_reads = {}, set(), [], []
    phase = dict(stopping=False, samples=0)

    class VPath(PurePosixPath):
        def resolve(self, *args, **kwargs): return self
        def is_symlink(self): return False
        def exists(self): return str(self) in files or str(self) in directories
        def mkdir(self, *args, **kwargs):
            assert not self.exists(); directories.add(str(self))

    root = VPath('/synthetic/state'); tx = root / 'boots' / BOOT
    aura = VPath('/synthetic/runtime/aura'); ops = VPath('/synthetic/ops')
    run = ops / ('native-run-' + BOOT + '-900/config.json')
    checkpoint = VPath('/synthetic/native/state/native-protection-checkpoint.json')
    startup_path = VPath('/synthetic/startup/config.json')
    manifest = dict(path='/synthetic/native/camera-python-manifest.json', sha256='a' * 64)
    digest, encoded = rules['digest'], rules['encoded']

    def put(path, value):
        raw = encoded(value); files[str(path)] = raw
        return dict(path=str(path), sha256=digest(raw))

    source = '/synthetic/native/source.py'; files[source] = b'public source\n'
    sources = {source: digest(files[source])}
    selected_pin = put('/synthetic/selected-old.json', dict(source_sha256=sources, board_boot_id=OLD,
        camera_pid=800, camera_start_ticks='88', camera_config='/synthetic/old-run/config.json'))
    ui_path = aura / 'config/board_avatar_gtk.json'
    put(ui_path, dict(board_business=dict(face_readback=selected_pin)))
    files[str(aura / 'public.py')] = b'public GUI source\n'
    put(startup_path, dict(runtime='/synthetic/runtime', component_sha256={
        'config/board_avatar_gtk.json': digest(files[str(ui_path)]), 'public.py': digest(files[str(aura / 'public.py')])}))
    put(run, dict(native_execution=dict(source_manifest=manifest['path'], source_manifest_sha256=manifest['sha256'], checkpoint_output=str(checkpoint))))
    gate = dict(boot_id=BOOT, contract_sha256='c' * 64, checkpoint_sha256='b' * 64,
                predecessor=dict(boot_id=OLD, camera_owner=dict(pid=800, birth_ticks='88', command_sha256='e' * 64)))
    put(tx / 'current-camera-gate.json', gate)
    unit_file = '/synthetic/aura-camera-ui.service'; files[unit_file] = b'public unchanged unit\n'
    initial = dict(contract_sha256='INITIAL_CONTRACT', startup_sha256=digest(files[str(startup_path)]),
        ui_sha256=digest(files[str(ui_path)]), selected_pin=selected_pin, selected_sources=sources, predecessor=gate['predecessor'])
    contract = dict(startup_path=str(startup_path), runtime_aura=str(aura), component_count=2,
        native_ops_root=str(ops), native_manifest=manifest, initial_source_state=initial,
        immutable_files={source: sources[source]}, original_units={rules['CAMERA']: {'source_sha256': {unit_file: digest(files[unit_file])}}})

    def regular(path, *args):
        if str(path) == str(run) and phase['samples'] == 2 and flip_after_sampling:
            phase['stopping'] = True  # Samples returned, PID/birth/cmd remain unchanged.
        return files[str(path)]

    def unit(name):
        if name == rules['GUI']:
            return dict(MainPID='0', ActiveState='activating', SubState='start-pre', ControlPID='7000')
        state = dict(MainPID='900', ActiveState='deactivating' if phase['stopping'] else 'active',
            SubState='stop-sigterm' if phase['stopping'] else 'running', Job='99 stop' if phase['stopping'] else '',
            ControlPID='0', Result='success', FragmentPath=unit_file, DropInPaths='')
        unit_reads.append(copy.deepcopy(state)); return state

    def metadata(port, path):
        assert not phase['stopping']
        phase['samples'] += 1
        return dict(pid=900, board_boot_id=BOOT, motion_command_emitted=False, identity=dict(ready=True),
            capture_frames=phase['samples'], detected_frames=phase['samples'],
            dpu_schedule=dict(native_critical=True, native_abi=2, owner_fenced=False, quiesced=False,
                protection_handoff=dict(mode='native_new_kernel_boot', seed_sha256='b' * 64,
                    source_pid=800, source_birth_ticks=88, current_boot=BOOT, source_boot=OLD)))

    def create(path, raw):
        assert str(path) not in files; files[str(path)] = raw

    def replace_known(path, before, after):
        assert files[str(path)] == before
        replacements.append(dict(path=str(path), camera_stopping_at_replace=phase['stopping']))
        files[str(path)] = after

    def original_verify(aura_path, binding):
        # Scoped stub: metadata source pins are exact; original b77 is not run.
        for name, value in binding['source_sha256'].items(): assert digest(files[name]) == value

    namespace = dict(rules, Path=VPath, STATE_ROOT=root, CHECKPOINT=checkpoint, regular=regular, unit=unit,
        process=lambda pid: copy.deepcopy(OWNER), get_metadata=metadata, create=create, replace_known=replace_known,
        original_verify=original_verify, http=http, time=types.SimpleNamespace(monotonic=lambda: 1.0, sleep=lambda value: None),
        os=types.SimpleNamespace(getpid=lambda: 7000, path=types.SimpleNamespace(lexists=lambda path: str(path) in files)))
    exec(compile(ast.Module(body=methods, type_ignores=[]), '<exact-frozen-R3-methods-RAM-IO>', 'exec'), namespace)
    fake_type = type('ScopedRecovery', (), {name: namespace[name] for name in ('source_snapshot', 'camera_samples', 'bind_camera')})
    obj = fake_type(); obj.contract = contract; obj.activation = {'installed_files': {}}
    obj.contract_sha = 'c' * 64; obj.boot = BOOT; obj.tx = tx
    obj.prepared = lambda: {'status': 'synthetic prepared scope prerequisite'}
    obj.pin = lambda value: files[value['path']] if digest(files[value['path']]) == value['sha256'] else None
    result = obj.bind_camera()
    committed = any(name.endswith('/committed.json') for name in files)
    assert result['status'] == 'ORIGINAL_VERIFIER_CURRENT_BINDING_COMMITTED' and committed
    assert len(replacements) == 2
    assert all(row['camera_stopping_at_replace'] == flip_after_sampling for row in replacements)
    return dict(fault_after_two_healthy_samples=flip_after_sampling, samples=phase['samples'], result=result['status'],
        committed_receipt_written_in_RAM=committed, replacements=replacements,
        stopping_unit_metadata_observed_after_sampling=sum(value['ActiveState'] == 'deactivating' for value in unit_reads),
        owner_fingerprint_remained=OWNER, full_source_snapshot_method_executed=True,
        original_b77_verifier_and_prepared_prerequisites_stubbed=True)


results = [run_case(False), run_case(True)]
report = dict(schema='aura-boot-r3-owner-recheck-probes-1', runtime_sha256=RUNTIME_SHA, rules_sha256=RULE_SHA,
    results=results, cases=2, verdict='REPRODUCED_POST_SAMPLE_PENDING_STOP_BINDING_COMMIT',
    original65_tests_rerun=False, new_Native_framework_or_executor_created=False,
    board_http_proc_service_media_DB_model_or_real_file_mutation=False,
    actual_b77_verifier_not_run=True, author_files_modified=False, cross_dialogue_messages_sent=False)
(HERE / 'BOOT_FIX_R3_OWNER_RECHECK_PROBES.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
