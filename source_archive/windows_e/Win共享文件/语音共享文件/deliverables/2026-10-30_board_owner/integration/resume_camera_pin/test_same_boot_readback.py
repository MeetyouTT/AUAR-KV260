"""Synthetic COMPLETE trial/source proof. No board, service, runner or DB."""
import copy
import importlib.util
import io
from pathlib import Path, PurePosixPath
import stat
import types

import pytest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


pin = load('same_boot_pin_fixture', HERE/'rebuild_same_boot_readback.py')
fixtures = load('complete_trial_fixture', HERE.parent/'resume_camera_budget/test_serial_trial.py')
exe = fixtures.trial


@pytest.fixture
def env(monkeypatch):
    system, journal = fixtures.FakeSystem(monkeypatch), fixtures.MemoryJournal()
    system.readback['model_sha256'] = 'e'*64
    for index in range(16):
        name = '/home/root/pinned-old-source-'+str(index)+'.py'
        system.files[name] = ('source fixture '+str(index)).encode()
        system.readback['source_sha256'][name] = pin.digest(system.files[name])
    system.files[fixtures.RB] = pin.encoded(system.readback)
    trial = exe.Trial(system, journal)
    fixtures.prepare((system, journal, trial))
    trial.stop('baseline', .5);trial.start(False, 2)
    trial.stop('candidate', .5);trial.start(True, 2);trial.finalize()
    authority = dict(pin.AUTHORITY, baseline_path=fixtures.RB,
                     baseline_sha256=pin.digest(system.files[fixtures.RB]),
                     manifest_sha256='c'*64, candidate_pid=1400, restored_pid=1500,
                     checkpoint_sha256=trial.d['handoff']['sha256'])
    source = (HERE.parent/'resume_camera_budget/serial_trial.py').read_bytes()
    assert pin.digest(source) == pin.AUTHORITY['executor_sha256']
    system.files[authority['executor_path']] = source
    system.files[authority['journal_path']] = pin.encoded(journal.read())
    system.validate_seed_abi = lambda seed: pin.need(seed.get('abi_version') == 2 and seed.get('purpose') == 'final_quiescent_business_checkpoint', 'fixture_invalid_native_abi')
    options = {'journal_path': authority['journal_path'],
               'expected_journal_sha256': pin.digest(system.files[authority['journal_path']]),
               'baseline_path': authority['baseline_path'], 'expected_baseline_sha256': authority['baseline_sha256'],
               'executor_path': authority['executor_path'], 'expected_executor_sha256': authority['executor_sha256'],
               'reader': system.read, 'authority': authority}
    return types.SimpleNamespace(s=system, j=journal, t=trial, a=authority, options=options)


def build(env):return pin.build(exe, env.s, **env.options)


def change_journal(env, mutation):
    data = pin.parse(env.s.files[env.a['journal_path']]);mutation(data)
    env.s.files[env.a['journal_path']] = pin.encoded(data)
    env.options['expected_journal_sha256'] = pin.digest(env.s.files[env.a['journal_path']])


def test_reviewed_production_authority_is_exact_completed_restoration():
    assert pin.AUTHORITY['baseline_pid'] == 1334
    assert pin.AUTHORITY['candidate_pid'] == 240801
    assert pin.AUTHORITY['restored_pid'] == 260102
    assert pin.AUTHORITY['baseline_pin_count'] == 19
    assert pin.AUTHORITY['checkpoint_sha256'] == 'a16ccd5b823f385890cc119fe8cd427ee9908906c05bad73271c06b220ad9228'


def test_valid_sameboot_completed_source_adds_one_runtime_preserves_all_old19(env):
    before_files = copy.deepcopy(env.s.files);before_commands = list(env.s.commands)
    candidate, report = build(env)
    baseline = pin.parse(env.s.files[env.a['baseline_path']])
    assert len(candidate['source_sha256']) == 20 and len(baseline['source_sha256']) == 19
    assert all(candidate['source_sha256'][k] == v for k, v in baseline['source_sha256'].items())
    assert candidate['camera_pid'] == 1500 and candidate['camera_start_ticks'] == '1500'
    assert candidate['camera_config'] != baseline['camera_config']
    assert set(candidate) == pin.FIELDS
    assert all(candidate[k] == baseline[k] for k in
               ('database', 'identity_config', 'model_id', 'dimension', 'model_sha256', 'result_ttl_ms', 'backend'))
    assert report['ready'] and not report['written']
    assert report['latest_consumed_checkpoint_sha256'] == env.a['checkpoint_sha256']
    assert env.s.files == before_files and env.s.commands == before_commands
    assert '/PRIVATE_DB_MUST_NEVER_OPEN' not in env.s.reads


def test_observation_token_excludes_live_progress_but_retains_epoch_and_owner(env):
    one, a = build(env);env.s.frames += 500
    two, b = build(env)
    assert one == two and a['observation_sha256'] == b['observation_sha256']


@pytest.mark.parametrize('field', ['executor_path', 'executor_sha256', 'baseline_path', 'baseline_sha256', 'journal_path'])
def test_explicit_authority_inputs_cannot_be_redirected(env, field):
    option = {'executor_sha256': 'expected_executor_sha256', 'baseline_sha256': 'expected_baseline_sha256'}.get(field, field)
    env.options[option] += 'changed'
    with pytest.raises(pin.Refused):build(env)


@pytest.mark.parametrize('field', ['phase', 'boot', 'baseline', 'candidate', 'restored', 'manifest_sha256', 'readback_path'])
def test_even_new_explicit_journal_hash_cannot_approve_changed_owner_chain(env, field):
    def mutate(d):
        if field in ('baseline', 'candidate', 'restored'):d[field]['pid'] += 1
        else:d[field] = 'changed'
    change_journal(env, mutate)
    with pytest.raises((pin.Refused, exe.Refused)):build(env)


@pytest.mark.parametrize('case', ['pid_birth', 'unit_owner', 'cmdline', 'mapped', 'source', 'model', 'guard', 'unit_flags', 'unit_dropin'])
def test_actual_current_owner_source_or_unit_change_refused(env, case):
    if case == 'pid_birth':env.s.owners[1500]['birth'] = 'new'
    if case == 'unit_owner':env.s.props['MainPID'] = '999'
    if case == 'cmdline':env.s.owners[1500]['argv'].append('--different')
    if case == 'mapped':env.s.mapped_ok = False
    if case == 'source':env.s.files[exe.BASE] += b'changed'
    if case == 'model':env.s.files['/home/root/feature_backend.xmodel'] += b'changed'
    if case == 'guard':env.s.files[env.t.d['dropin']] = b'guard reappeared'
    if case == 'unit_flags':env.s.props['SendSIGKILL'] = 'different'
    if case == 'unit_dropin':env.s.files[env.s.original['DropInPaths']] += b'changed'
    with pytest.raises((pin.Refused, exe.Refused)):build(env)


@pytest.mark.parametrize('case', ['bytes', 'marker_missing', 'marker_content', 'candidate_alive', 'seed_source', 'seed_counter', 'sface', 'history', 'pending'])
def test_consumed_checkpoint_full_counter_and_history_binding_refused(env, case):
    d = pin.parse(env.s.files[env.a['journal_path']]);marker = d['handoff']['consumption_marker']
    if case == 'bytes':env.s.files[exe.CHECKPOINT] += b'changed'
    if case == 'marker_missing':del env.s.files[marker]
    if case == 'marker_content':env.s.files[marker] = b'wrong SHA\n'
    if case == 'candidate_alive':env.s.owners[1400] = copy.deepcopy(d['candidate'])
    if case in ('seed_source', 'seed_counter', 'sface', 'history', 'pending'):
        def mutate(data):
            if case == 'seed_source':data['handoff']['seed']['source_pid'] = 1
            if case == 'seed_counter':data['handoff']['seed']['primary_calls'] = 1
            if case == 'sface':data['handoff']['sface_counters']['requests'] = 1
            if case == 'history':data['handoff']['previous_kernel_history'] = None
            if case == 'pending':data['handoff']['seed']['checkpoint_kind'] = 0
        change_journal(env, mutate)
    with pytest.raises((pin.Refused, exe.Refused, FileNotFoundError)):build(env)


@pytest.mark.parametrize('case', ['runtime_non_seed', 'runtime_seed', 'health_counter', 'health_epoch', 'source_age'])
def test_restored_runtime_and_actual_health_must_match_original_v3_proof(env, case):
    if case.startswith('runtime'):
        path = env.t.d['restored_health']['runtime_path'];value = pin.parse(env.s.files[path])
        if case == 'runtime_non_seed':value['identity']['config'] += '.changed'
        else:value['native_execution']['seed']['sha256'] = 'd'*64
        env.s.files[path] = pin.encoded(value)
    else:
        old = env.s.health
        def health():
            value = old()
            if case == 'health_counter':value['dpu_schedule']['primary_calls'] = 0
            if case == 'health_epoch':value['camera_epoch'] += '-changed'
            if case == 'source_age':value['identity']['face_targets']['source_age_ms'] = 1000
            return value
        env.s.health = health
    with pytest.raises((pin.Refused, exe.Refused)):build(env)


def test_second_owner_observation_and_pin_recheck_refuse_inflight_change(env):
    original = env.s.owner;calls = [0]
    def observed(pid):
        result = original(pid)
        if pid == 1500:
            calls[0] += 1
            if calls[0] >= 4:result['birth'] = 'reused'
        return result
    env.s.owner = observed
    with pytest.raises((pin.Refused, exe.Refused)):build(env)


@pytest.mark.parametrize('case', ['source', 'journal', 'checkpoint', 'marker', 'runtime'])
def test_second_proof_rejects_inflight_source_and_consumed_provenance_changes(env, case):
    original = env.s.health;calls = [0]
    def health():
        result = original();calls[0] += 1
        if calls[0] == 1:
            if case == 'source':env.s.files[exe.BASE] += b'changed'
            if case == 'journal':env.s.files[env.a['journal_path']] += b' '
            if case == 'checkpoint':env.s.files[exe.CHECKPOINT] += b' '
            if case == 'marker':env.s.files[env.t.d['handoff']['consumption_marker']] += b'changed'
            if case == 'runtime':env.s.files[env.t.d['restored_health']['runtime_path']] += b' '
        return result
    env.s.health = health
    with pytest.raises((pin.Refused, exe.Refused)):build(env)


def test_executor_loader_only_accepts_exact_v3_source_and_is_inert(env):
    before = list(env.s.commands)
    module = pin.load_executor(env.a['executor_path'], env.a['executor_sha256'], reader=env.s.read, authority=env.a)
    assert module.Trial and env.s.commands == before
    with pytest.raises(pin.Refused):
        pin.load_executor(env.a['executor_path']+'.old', env.a['executor_sha256'], reader=env.s.read, authority=env.a)


def test_readonly_capabilities_reject_every_service_or_journal_mutation(monkeypatch):
    calls = []
    monkeypatch.setattr(exe.System, 'command', lambda self, *a: calls.append(a))
    system = pin.readonly_system(exe)
    for action in ('start', 'stop', 'restart', 'daemon-reload', 'kill'):
        with pytest.raises(pin.Refused):system.command(action, exe.UNIT)
    with pytest.raises(pin.Refused):system.write_dropin('file', b'bytes')
    with pytest.raises(pin.Refused):system.remove_dropin('file', 'sha')
    with pytest.raises(pin.Refused):system.checkpoint_validate({}, 'boot')
    with pytest.raises(pin.Refused):pin.FrozenJournal({}).save({})
    system.command('show', '--all', exe.UNIT)
    assert calls == [('show', '--all', exe.UNIT)]


class FakeFiles:
    def __init__(self):self.data = {};self.modes = {};self.fd = {};self.nextfd = 1;self.open_calls = []
    def path(self, name):
        fs = self
        class P:
            def __init__(self, value):self.value = PurePosixPath(value)
            def __str__(self):return str(self.value)
            def __hash__(self):return hash(self.value)
            def __eq__(self, other):return isinstance(other, P) and self.value == other.value
            def is_absolute(self):return self.value.is_absolute()
            def resolve(self):return self
            def is_symlink(self):return False
            def stat(self):return types.SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR|0o700)
            @property
            def parent(self):return P(self.value.parent)
            @property
            def parents(self):return tuple(P(p) for p in self.value.parents)
            @property
            def suffix(self):return self.value.suffix
        # All paths in a call share this exact P class.
        return P
    def open(self, path, flags, mode=None):
        self.open_calls.append((path, flags, mode))
        if flags & 8:
            if path in self.data:raise FileExistsError(path)
            self.data[path] = b'';self.modes[path] = mode
        fd = self.nextfd;self.nextfd += 1;self.fd[fd] = path;return fd
    def fdopen(self, fd, mode, closefd=False):
        fs = self
        class F:
            def __enter__(self):return self
            def __exit__(self, *a):pass
            def write(self, raw):fs.data[fs.fd[fd]] += raw
            def flush(self):pass
            def fileno(self):return fd
        return F()
    def os(self):
        return types.SimpleNamespace(name='posix', geteuid=lambda:0,
            path=types.SimpleNamespace(lexists=lambda p:p in self.data),
            O_CREAT=1, O_EXCL=8, O_WRONLY=2, O_NOFOLLOW=4, O_CLOEXEC=16, O_RDONLY=0, O_DIRECTORY=32,
            open=self.open, fdopen=self.fdopen, close=lambda fd:None, fsync=lambda fd:None)


def test_exclusive_private_output_and_proof_never_overwrite_old_config(env, monkeypatch):
    candidate, report = build(env);fs = FakeFiles()
    cls = fs.path('unused');monkeypatch.setattr(pin, 'Path', cls);monkeypatch.setattr(pin, 'os', fs.os())
    root = '/home/root/aura-board-owner-candidate-20261030/new-pin'
    out, proof = root+'/readback.json', root+'/proof.json'
    result = pin.write_candidate(candidate, report, private_root=root, output=out,
                                 proof_output=proof, expected_observation=report['observation_sha256'])
    assert result['written'] and pin.parse(fs.data[out]) == candidate
    assert pin.parse(fs.data[proof])['candidate_sha256'] == report['candidate_sha256']
    assert fs.modes == {out:0o600, proof:0o600}
    before = copy.deepcopy(fs.data)
    with pytest.raises(pin.Refused):pin.write_candidate(candidate, report, private_root=root, output=out,
        proof_output=proof, expected_observation=report['observation_sha256'])
    assert fs.data == before


def test_unreviewed_token_cannot_write_any_file(env, monkeypatch):
    candidate, report = build(env);fs = FakeFiles();cls = fs.path('unused')
    monkeypatch.setattr(pin, 'Path', cls);monkeypatch.setattr(pin, 'os', fs.os())
    root = '/home/root/aura-board-owner-candidate-20261030/new-pin'
    with pytest.raises(pin.Refused):pin.write_candidate(candidate, report, private_root=root,
        output=root+'/r.json', proof_output=root+'/p.json', expected_observation='d'*64)
    assert fs.data == {} and fs.open_calls == []
