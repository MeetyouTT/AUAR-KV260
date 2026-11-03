"""State-machine tests only: no subprocess, board, camera, model or DB."""
import copy
import importlib.util
from pathlib import Path
import types

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('serial_trial_fixture', HERE/'serial_trial.py')
trial = importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)
BOOT = '8100a7fd-0c6a-46c4-82b8-f874988a1521'
RB = '/home/root/private/readback.json'
CANDIDATE = '/home/root/private/candidate'
HISTORY = {'archive_path': '/private/history.json', 'archive_sha256': 'a'*64}


def owner(pid, birth, argv):
    return {'pid': pid, 'birth': str(birth), 'argv': list(argv),
            'cmd_sha256': trial.digest(('\0'.join(argv)+'\0').encode())}


def exec_property(argv):
    return '{ path='+argv[0]+' ; argv[]='+' '.join(argv)+' ; ignore_errors=no ; }'


def recovery():
    return [{'faults': 2, 'attempts': 1, 'recoveries': 1, 'attempt_count': 1, 'history_opaque': False},
            {'faults': 0, 'attempts': 0, 'recoveries': 0, 'attempt_count': 0, 'history_opaque': False}]


def seed(calls=100):
    return {'abi_version': 2, 'struct_size': 520, 'checkpoint_kind': 1, 'fenced': 0,
            'purpose': 'final_quiescent_business_checkpoint', 'boot_id': BOOT,
            'source_manifest_sha256': trial.NATIVE_MANIFEST,
            'primary_calls': calls, 'primary_period_overruns': 1,
            'overruns': [1, 2, 3], 'recovery': recovery()}


class MemoryJournal:
    def __init__(self):self.value = None;self.saves = []
    def read(self):return copy.deepcopy(self.value)
    def save(self, value):
        self.value = copy.deepcopy(value);self.saves.append(copy.deepcopy(value))


class FakeSystem:
    def __init__(self, monkeypatch):
        self.clock = 10_000_000_000;self.commands = [];self.reads = [];self.files = {}
        self.pending = None;self.hang_stop = False;self.retained = False
        self.bad_checkpoint = None;self.bad_health = None;self.crash_start = None;self.crash_write = False
        self.npid = 1400;self.frames = 100;self.mapped_ok = True
        self.baseline_argv = ['/usr/bin/python3', '-B', trial.BASE]
        self.current_owner = owner(1334, 100, self.baseline_argv)
        self.owners = {1334: self.current_owner}
        self.native_seed = seed();self.handoff = {'mode': 'native_new_kernel_boot', 'previous_kernel_history': HISTORY}
        self.original = {key: '' for key in trial.SAFE_PROPERTIES}
        self.original.update(MainPID='1334', ActiveState='active', SubState='running',
            ExecStart=exec_property(self.baseline_argv), Restart='on-failure', SendSIGKILL='yes',
            TimeoutStopUSec='1min 30s', KillSignal='15', KillMode='control-group', Type='simple',
            FragmentPath='/etc/systemd/system/aura-camera-ui.service',
            DropInPaths='/etc/systemd/system/aura-camera-ui.service.d/00-original.conf', Job='0')
        self.props = copy.deepcopy(self.original)
        self.files[self.original['FragmentPath']] = b'original unit'
        self.files[self.original['DropInPaths']] = b'original unrelated dropin'
        self.files[trial.BASE] = b'protected r17 source'
        self.files[trial.SCHEDULE_SOURCE] = b'pinned schedule fixture'
        monkeypatch.setattr(trial, 'SCHEDULE_SHA', trial.digest(self.files[trial.SCHEDULE_SOURCE]))
        self.camera_path = '/home/root/old-runtime/config.json';identity_path = '/home/root/identity.json'
        self.camera = {'identity': {'enabled': True, 'config': identity_path},
                       'native_execution': {'checkpoint_output': trial.CHECKPOINT,
                                            'seed': {'path': trial.CHECKPOINT, 'sha256': 'b'*64}}}
        self.files[self.camera_path] = trial.encode(self.camera)
        identity = {'database': '/PRIVATE_DB_MUST_NEVER_OPEN', 'model_id': 'sface-int8-fixture', 'result_ttl_ms': 1000}
        for key, kind in [('face_backend', 'dpu_yunet'), ('feature_backend', 'dpu_sface')]:
            model, manifest = '/home/root/'+key+'.xmodel', '/home/root/'+key+'.json'
            self.files[model] = (kind+' model fixture').encode();self.files[manifest] = (kind+' manifest fixture').encode()
            identity[key] = {'kind': kind, 'model': model, 'manifest': manifest,
                             'model_sha256': trial.digest(self.files[model]), 'manifest_sha256': trial.digest(self.files[manifest])}
        self.files[identity_path] = trial.encode(identity)
        self.readback = {'version': 1, 'enabled': True, 'board_boot_id': BOOT, 'camera_pid': 1334,
            'camera_start_ticks': '100', 'camera_cmdline_sha256': self.current_owner['cmd_sha256'],
            'camera_config': self.camera_path, 'identity_config': identity_path, 'backend': 'DPU_SFACE_INT8',
            'dimension': 128, 'database': identity['database'], 'model_id': identity['model_id'], 'result_ttl_ms': 1000,
            'source_sha256': {name: trial.digest(self.files[name]) for name in (trial.BASE, self.camera_path, identity_path)}}
        self.files[RB] = trial.encode(self.readback)

    def now(self):return self.clock
    def sleep(self, value):self.clock += int(value*1e9)
    def boot(self):return BOOT
    def exists(self, path):return path in self.files
    def read(self, path, **options):
        assert path != '/PRIVATE_DB_MUST_NEVER_OPEN'
        self.reads.append(path)
        if path not in self.files:raise FileNotFoundError(path)
        return self.files[path]
    def owner(self, pid):return copy.deepcopy(self.owners.get(pid))
    def mapped(self, pid):return self.mapped_ok and pid in self.owners
    def show(self):return copy.deepcopy(self.props)
    def static_verify(self, path, expected):
        trial.need(path == CANDIDATE and expected == 'c'*64, 'candidate_fixture_changed')
        return {'candidate_sources': {}, 'inherited_pins': {}}
    def checkpoint_validate(self, pin, boot):
        assert boot == BOOT and trial.digest(self.files[pin['path']]) == pin['sha256']
        doc = trial.parse(self.files[pin['path']]);s = doc['seed']
        trial.need(s['source_pid'] not in self.owners, 'original_predecessor_still_alive')
        trial.need(not self.exists(pin['path']+'.native-consumed-'+pin['sha256']), 'original_already_consumed')
        trial.need(doc['auxiliary']['pending_result_tokens'] == [0, 0, 0], 'original_pending_result')
        return {'document': doc, 'seed': s, 'auxiliary': doc['auxiliary']}
    def write_dropin(self, path, raw, old_sha=None):
        if path in self.files:
            if self.files[path] == raw:return
            assert trial.digest(self.files[path]) == old_sha
        else:assert old_sha is None
        self.files[path] = raw
        if self.crash_write and b'ExecStart=' in raw:
            self.crash_write = False;raise OSError('simulated journal/write interruption')
    def remove_dropin(self, path, expected):
        assert trial.digest(self.files[path]) == expected
        assert path.startswith('/run/systemd/system/'+trial.UNIT+'.d/'+trial.TRIAL_PREFIX)
        del self.files[path]
    def finish_stop(self):
        stopped = self.current_owner;self.clock += 1
        value = copy.deepcopy(self.native_seed);value['primary_calls'] += 10
        value.update(source_pid=stopped['pid'], source_birth_ticks=int(stopped['birth']), captured_mono_ns=self.clock)
        doc = {'schema': 'aura-native-protection-checkpoint-2', 'scope': 'final_quiescent_before_native_owner_close',
               'source_unit_sha256': trial.NATIVE_UNIT, 'seed': value,
               'auxiliary': {'active': 0, 'primary_waiting': 0, 'fenced': 0,
                   'pending_result_tokens': [0, 0, 0], 'sface_counters': {'requests': 10, 'features_returned': 8}},
               'previous_kernel_history': copy.deepcopy(HISTORY)}
        if self.bad_checkpoint:self.bad_checkpoint(doc)
        self.files[trial.CHECKPOINT] = trial.encode(doc)
        self.owners.pop(stopped['pid'])
        self.props.update(MainPID='0', ActiveState='inactive', SubState='dead', Job='0')
    def command(self, *args):
        self.commands.append(args)
        assert args[0] in ('daemon-reload', 'stop', 'start')
        if args[0] == 'daemon-reload':
            for key in ('Restart', 'SendSIGKILL', 'TimeoutStopUSec', 'KillSignal', 'ExecStart', 'DropInPaths'):
                self.props[key] = self.original[key]
            owned = [p for p in self.files if p.startswith('/run/systemd/system/'+trial.UNIT+'.d/')]
            if owned:
                assert len(owned) == 1
                text = self.files[owned[0]].decode()
                self.props.update(Restart='no', SendSIGKILL='no', TimeoutStopUSec='infinity', KillSignal='15',
                                  DropInPaths=self.original['DropInPaths']+' '+owned[0])
                commands = [row[len('ExecStart='):] for row in text.splitlines() if row.startswith('ExecStart=') and row != 'ExecStart=']
                if commands:self.props['ExecStart'] = exec_property(commands[-1].split())
        elif args[0] == 'stop':
            assert args == ('stop', '--no-block', trial.UNIT)
            assert self.props['SendSIGKILL'] == 'no' and self.props['Restart'] == 'no'
            if self.retained:
                pid = self.current_owner['pid']
                self.files[trial.OPS+'/native-run-'+BOOT+'-'+str(pid)+'/UNSAFE_OWNER_RETAINED.json'] = b'{}'
            elif not self.hang_stop:self.finish_stop()
        elif args[0] == 'start':
            assert args == ('start', '--no-block', trial.UNIT)
            assert self.props['MainPID'] == '0'
            if self.crash_start == 'before':self.crash_start = None;raise OSError('client lost before request')
            doc = trial.parse(self.files[trial.CHECKPOINT]);sha = trial.digest(self.files[trial.CHECKPOINT])
            assert trial.CHECKPOINT+'.native-consumed-'+sha not in self.files
            argv = trial.argv_from_property(self.props['ExecStart'])
            self.current_owner = owner(self.npid, self.npid, argv);self.npid += 100
            self.owners[self.current_owner['pid']] = self.current_owner
            self.props.update(MainPID=str(self.current_owner['pid']), ActiveState='active', SubState='running')
            self.native_seed = copy.deepcopy(doc['seed']);self.native_seed['primary_calls'] += 10
            self.handoff = {'mode': 'native_exact_same_boot', 'seed_sha256': sha,
                            'source_pid': doc['seed']['source_pid'], 'source_birth_ticks': doc['seed']['source_birth_ticks'],
                            'previous_kernel_history': copy.deepcopy(HISTORY)}
            runtime = copy.deepcopy(self.camera);runtime['native_execution']['seed']['sha256'] = sha
            if self.bad_health == 'config':runtime['identity']['config'] += '.different'
            self.files[trial.OPS+'/native-run-'+BOOT+'-'+str(self.current_owner['pid'])+'/config.json'] = trial.encode(runtime)
            self.files[trial.CHECKPOINT+'.native-consumed-'+sha] = (sha+'\n').encode()
            if self.crash_start == 'after':self.crash_start = None;raise OSError('client lost after request')
        return ''
    def health(self):
        self.frames += 1;pid = self.current_owner['pid']
        s = copy.deepcopy(self.native_seed)
        if self.bad_health == 'rollback':s['primary_calls'] = 0
        schedule = {'native_critical': True, 'native_abi': 2,
                    'primary_calls': s['primary_calls'], 'primary_period_overruns': s['primary_period_overruns'],
                    'owner_fenced': self.bad_health == 'fenced', 'seed_loaded': True,
                    'optional': {'yunet': {'overruns': s['overruns'][1]}, 'sface': {'overruns': s['overruns'][2]}},
                    'yunet_recovery': s['recovery'][0], 'sface_recovery': s['recovery'][1],
                    'protection_handoff': copy.deepcopy(self.handoff)}
        return {'pid': pid, 'board_boot_id': BOOT, 'role': 'DPU_YOLOX_PERSON_PREVIEW',
                'service_epoch': 'service-'+str(pid), 'camera_epoch': 'camera-'+str(pid),
                'camera_error': '', 'detector_error': '', 'capture_age_ms': 20, 'observation_age_ms': 50,
                'capture_frames': self.frames, 'detected_frames': self.frames,
                'identity': {'ready': True, 'error': '', 'backend': 'DPU_SFACE_INT8',
                             'feature_inference': {'requests': 10, 'features_returned': 8},
                             'face_targets': {'ready': True, 'error': '', 'fault_latched': False, 'source_age_ms': 200}},
                'dpu_schedule': schedule}


@pytest.fixture
def env(monkeypatch):
    system, journal = FakeSystem(monkeypatch), MemoryJournal()
    return system, journal, trial.Trial(system, journal)


def prepare(env):
    s, j, t = env
    t.prepare(candidate_dir=CANDIDATE, manifest_sha256='c'*64, readback=RB,
              readback_sha256=trial.digest(s.files[RB]), boot=BOOT, pid=1334, birth='100')
    return s, j, t


def candidate(env):
    s, j, t = prepare(env);t.stop('baseline', .5);t.start(False, 2)
    return s, j, t


def restored(env):
    s, j, t = candidate(env);t.stop('candidate', .5);t.start(True, 2)
    return s, j, t


def test_full_serial_trial_never_reuses_seed_or_parallel_owner_and_removes_only_own_dropin(env):
    s, j, t = candidate(env)
    original_seed_sha = t.d['handoff']['sha256']
    assert t.d['candidate']['pid'] == 1400
    t.stop('candidate', .5)
    candidate_seed_sha = t.d['handoff']['sha256']
    assert candidate_seed_sha != original_seed_sha
    t.start(True, 2);t.finalize()
    assert t.d['phase'] == 'COMPLETE' and t.d['restored']['pid'] == 1500
    assert s.handoff['seed_sha256'] == candidate_seed_sha
    assert s.files[trial.CHECKPOINT+'.native-consumed-'+original_seed_sha] == (original_seed_sha+'\n').encode()
    assert s.files[trial.CHECKPOINT+'.native-consumed-'+candidate_seed_sha] == (candidate_seed_sha+'\n').encode()
    assert s.original['DropInPaths'] in s.files and t.d['dropin'] not in s.files
    assert s.props['Restart'] == s.original['Restart']
    assert sum(c[0] == 'start' for c in s.commands) == 2
    assert sum(c[0] == 'stop' for c in s.commands) == 2
    assert all('/PRIVATE_DB_MUST_NEVER_OPEN' != name for name in s.reads)
    assert not t.report()['forced_kill']


@pytest.mark.parametrize('change', ['SendSIGKILL', 'Restart', 'TimeoutStopUSec', 'KillSignal'])
def test_effective_guard_failure_prevents_stop(env, change):
    s, j, t = prepare(env);s.props[change] = 'unsafe'
    before = len(s.commands)
    with pytest.raises(trial.Refused):t.stop('baseline', .5)
    assert len(s.commands) == before and 1334 in s.owners


@pytest.mark.parametrize('case', ['birth', 'cmdline', 'mainpid', 'source', 'dropin', 'other_dropin'])
def test_changed_owner_or_source_never_issues_stop(env, case):
    s, j, t = prepare(env)
    if case == 'birth':s.owners[1334]['birth'] = '999'
    if case == 'cmdline':s.owners[1334]['argv'].append('--different')
    if case == 'mainpid':s.props['MainPID'] = '999'
    if case == 'source':s.files[trial.BASE] += b'changed'
    if case == 'dropin':s.files[t.d['dropin']] += b'changed'
    if case == 'other_dropin':s.files[s.original['DropInPaths']] += b'changed'
    with pytest.raises(trial.Refused):t.stop('baseline', .5)
    assert not any(c[0] == 'stop' for c in s.commands)


def test_retained_owner_or_timeout_never_forces_stop_or_starts_second(env):
    s, j, t = prepare(env);s.retained = True
    with pytest.raises(trial.Refused, match='retained'):t.stop('baseline', .5)
    assert t.d['phase'] == 'STOPPING_BASELINE' and 1334 in s.owners
    with pytest.raises(trial.Refused):t.start(False, .5)
    assert not any(c[0] == 'start' for c in s.commands)


def test_timeout_is_resumable_observation_without_repeating_stop(env):
    s, j, t = prepare(env);s.hang_stop = True
    with pytest.raises(trial.Pending):t.stop('baseline', .4)
    assert 1334 in s.owners and t.d['phase'] == 'STOPPING_BASELINE'
    s.finish_stop();t = trial.Trial(s, j);t.stop('baseline', .5)
    assert t.d['phase'] == 'BASELINE_STOPPED'
    assert sum(c[0] == 'stop' for c in s.commands) == 1


@pytest.mark.parametrize('case', ['boot', 'pid', 'birth', 'unit', 'manifest', 'old_capture', 'history', 'pending'])
def test_inexact_checkpoint_never_permits_candidate(env, case):
    s, j, t = prepare(env)
    def bad(d):
        if case == 'boot':d['seed']['boot_id'] = 'different'
        if case == 'pid':d['seed']['source_pid'] = 1
        if case == 'birth':d['seed']['source_birth_ticks'] = 99
        if case == 'unit':d['source_unit_sha256'] = 'd'*64
        if case == 'manifest':d['seed']['source_manifest_sha256'] = 'd'*64
        if case == 'old_capture':d['seed']['captured_mono_ns'] = 1
        if case == 'history':d['previous_kernel_history'] = None
        if case == 'pending':d['auxiliary']['pending_result_tokens'] = [0, 1, 0]
    s.bad_checkpoint = bad
    with pytest.raises(trial.Refused):t.stop('baseline', .5)
    with pytest.raises(trial.Refused):t.start(False, .5)
    assert not any(c[0] == 'start' for c in s.commands)


def test_consumed_checkpoint_never_replayed(env):
    s, j, t = prepare(env);t.stop('baseline', .5)
    p = t.d['handoff'];s.files[p['consumption_marker']] = (p['sha256']+'\n').encode()
    with pytest.raises(trial.Refused):t.start(False, 1)
    assert not any(c[0] == 'start' for c in s.commands)


@pytest.mark.parametrize('case', ['rollback', 'config', 'fenced'])
def test_unhealthy_partial_start_is_preserved_and_can_only_normal_stop(env, case):
    s, j, t = prepare(env);t.stop('baseline', .5);s.bad_health = case
    with pytest.raises(trial.Pending):t.start(False, .6)
    assert t.d['phase'] == 'STARTING_CANDIDATE' and len(s.owners) == 1
    s.bad_health = None
    t.stop('candidate', .5)
    assert t.d['phase'] == 'CANDIDATE_STOPPED'
    t.start(True, 2)
    assert t.d['phase'] == 'BASELINE_RESTORED'


@pytest.mark.parametrize('moment', ['before', 'after'])
def test_durable_start_intent_never_blindly_repeats_client_request(env, moment):
    s, j, t = prepare(env);t.stop('baseline', .5);s.crash_start = moment
    with pytest.raises(OSError):t.start(False, 2)
    t = trial.Trial(s, j)
    if moment == 'before':
        with pytest.raises(trial.Pending):t.start(False, .6)
    else:t.start(False, 2)
    assert sum(c[0] == 'start' for c in s.commands) == 1


def test_own_exec_dropin_journal_interruption_resumes_exact_intended_bytes(env):
    s, j, t = prepare(env);t.stop('baseline', .5);s.crash_write = True
    with pytest.raises(OSError):t.start(False, 2)
    assert j.value['phase'] == 'STARTING_CANDIDATE' and not j.value['start_issued']
    t = trial.Trial(s, j);t.start(False, 2)
    assert t.d['phase'] == 'CANDIDATE_RUNNING'
    assert sum(c[0] == 'start' for c in s.commands) == 1


@pytest.mark.parametrize('case', ['owner', 'native', 'other_dropin'])
def test_finalize_refuses_removal_before_restored_owner_stable(env, case):
    s, j, t = restored(env)
    t.phase('FINALIZING')
    if case == 'owner':s.owners[1500]['birth'] = '999'
    if case == 'native':s.bad_health = 'fenced'
    if case == 'other_dropin':s.files[s.original['DropInPaths']] += b'changed'
    with pytest.raises(trial.Refused):t.finalize()
    assert t.d['dropin'] in s.files


def test_stop_hooks_refused_before_guard_write(env):
    s, j, t = env;s.props['ExecStop'] = 'unexpected helper'
    with pytest.raises(trial.Refused):prepare(env)
    assert j.value is None and s.commands == []


def test_another_trial_journal_cannot_claim_already_guarded_unit(env):
    s, j, t = prepare(env)
    other = trial.Trial(s, MemoryJournal())
    with pytest.raises(trial.Refused, match='another_trial'):
        other.prepare(candidate_dir=CANDIDATE, manifest_sha256='c'*64, readback=RB,
                      readback_sha256=trial.digest(s.files[RB]), boot=BOOT, pid=1334, birth='100')
    assert other.d is None


def test_interrupted_finalize_removes_no_unrelated_dropin(env):
    s, j, t = restored(env)
    t.phase('FINALIZING')
    s.remove_dropin(t.d['dropin'], t.d['dropin_sha256'])
    # Simulated crash after unlink but before daemon-reload/journal completion.
    t = trial.Trial(s, j);t.finalize()
    assert t.d['phase'] == 'COMPLETE' and s.original['DropInPaths'] in s.files


def test_sface_inheritance_health_missing_never_approves_owner(env):
    s, j, t = prepare(env);t.stop('baseline', .5)
    original = s.health
    def incomplete():
        value = original();value['identity']['feature_inference'] = {};return value
    s.health = incomplete
    with pytest.raises(trial.Pending, match='sface_counter_not_inherited'):
        t.start(False, .6)
    assert t.d['phase'] == 'STARTING_CANDIDATE' and len(s.owners) == 1


def test_only_actual_face_targets_schema_passes_and_observation_never_restarts_owner(env):
    s,j,t = prepare(env)
    t.stop('baseline', .5)
    health = s.health
    def projected_alias():
        value = health()
        value['identity']['faces'] = value['identity'].pop('face_targets')
        return value
    s.health = projected_alias
    with pytest.raises(trial.Pending,match='face_source_health_not_ready'):
        t.start(False,.6)
    current = copy.deepcopy(s.current_owner)
    s.health = health
    t = trial.Trial(s,j)
    t.start(False,2)
    assert t.d['phase'] == 'CANDIDATE_RUNNING' and t.d['candidate'] == current
    assert sum(args[0] == 'start' for args in s.commands) == 1
    assert len(s.owners) == 1


def test_complete_phase_rechecks_exact_owner_before_repeating_finalize(env):
    s, j, t = restored(env);t.finalize()
    s.owners[1500]['birth'] = '99999'
    with pytest.raises(trial.Refused):t.finalize()


def test_second_partial_restore_can_normal_stop_its_new_owner(env):
    s, j, t = restored(env)
    first = copy.deepcopy(t.d['restored'])
    t.stop('restored', .5)
    assert t.d['handoff']['source'] == first
    s.bad_health = 'rollback'
    with pytest.raises(trial.Pending):t.start(True, .6)
    current = copy.deepcopy(s.current_owner)
    assert current['pid'] != first['pid']
    assert t.d['phase'] == 'RESTORING' and 'restored' not in t.d
    assert t.d['handoff']['source'] == first
    # Reload the durable journal, as the real stepwise CLI does for every action.
    t = trial.Trial(s, j)
    s.bad_health = None
    t.stop('restored', .5)
    assert t.d['phase'] == 'RESTORED_STOPPED'
    assert t.d['handoff']['source'] == current and not s.owners
    t.start(True, 2)
    t.finalize()
    assert t.d['phase'] == 'COMPLETE' and len(s.owners) == 1
    assert t.d['restored']['pid'] != current['pid']
    assert s.props['SendSIGKILL'] == s.original['SendSIGKILL']


def test_real_show_requests_all_and_keeps_empty_unit_properties(monkeypatch):
    system = trial.System()
    calls = []
    values = {key: '' for key in trial.SAFE_PROPERTIES}
    values.update(MainPID='1334', ActiveState='active')
    def command(*args):
        calls.append(args)
        return '\n'.join(key+'='+value for key,value in values.items())
    monkeypatch.setattr(system,'command',command)
    assert system.show() == values
    assert calls == [('show','--all',trial.UNIT,
                      *['--property='+key for key in trial.SAFE_PROPERTIES])]
    assert values['ExecStop'] == values['ExecStopPost'] == values['User'] == values['Group'] == ''


def test_actual_systemd_empty_hooks_need_full_effective_and_source_proof(monkeypatch):
    system = trial.System();calls = [];reads = []
    values = {key: '' for key in trial.SAFE_PROPERTIES if key not in ('ExecStop','ExecStopPost')}
    values.update(MainPID='1334', ActiveState='active', Job='',
        FragmentPath='/etc/systemd/system/aura-camera-ui.service',
        DropInPaths='/etc/systemd/system/aura-camera-ui.service.d/'+'z'*28+'-face-measure-v17.conf')
    raw = '\n'.join(key+'='+value for key,value in values.items())
    def command(*args):calls.append(args);return raw
    def read(name):reads.append(name);return b'[Service]\n# ExecStop=comment only\nExecStart=/usr/bin/python3\n'
    monkeypatch.setattr(system,'command',command)
    monkeypatch.setattr(system,'read',read)
    actual = system.show()
    assert actual == dict(values,ExecStop='',ExecStopPost='')
    assert calls[-1] == ('show','--all',trial.UNIT) and len(calls) == 2
    assert reads == [values['FragmentPath']]+values['DropInPaths'].split()


@pytest.mark.parametrize('case', ['hook', 'post_hook', 'empty_reset', 'include', 'effective_hook', 'owner_changed', 'other_missing'])
def test_missing_hooks_are_never_blindly_treated_as_empty(monkeypatch,case):
    system = trial.System();calls = []
    values = {key: '' for key in trial.SAFE_PROPERTIES if key not in ('ExecStop','ExecStopPost')}
    values.update(MainPID='1334', FragmentPath='/etc/systemd/system/aura-camera-ui.service',DropInPaths='')
    full = dict(values)
    content = {'hook':b'[Service]\nExecStop=/usr/bin/false\n',
               'post_hook':b'[Service]\nExecStopPost=/usr/bin/false\n',
               'empty_reset':b'[Service]\nExecStop=\n',
               'include':b'.include /other/unit.conf\n'}.get(case,b'[Service]\n')
    if case == 'effective_hook':full['ExecStopEx'] = 'nonempty command'
    if case == 'owner_changed':full['MainPID'] = '9999'
    if case == 'other_missing':values.pop('User')
    def command(*args):
        calls.append(args)
        return '\n'.join(key+'='+value for key,value in (full if len(calls)>1 else values).items())
    monkeypatch.setattr(system,'command',command)
    monkeypatch.setattr(system,'read',lambda _:content)
    with pytest.raises(trial.Refused):system.show()


@pytest.mark.parametrize('value,accepted',[('',True),('0',True),(' 0 ',True),('42',False),
    ('42 /org/freedesktop/systemd1/job/42',False),('0 unexpected',False),('[]',False)])
def test_only_observed_no_job_shapes_are_accepted(value,accepted):
    assert trial.no_unit_job(value) is accepted


def test_empty_job_actual_shape_and_late_existing_execstart_are_supported(env):
    s,j,t = env
    late = '/etc/systemd/system/'+trial.UNIT+'.d/'+'z'*28+'-face-measure-v17.conf'
    s.files[late] = b'[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B protected-r17\n'
    s.original['DropInPaths'] += ' '+late
    s.props['DropInPaths'] = s.original['DropInPaths']
    s.original['Job'] = s.props['Job'] = ''
    prepare(env)
    assert Path(t.d['dropin']).name.startswith('z'*64+'-aura-face-cadence-')
    assert all(Path(name).name < Path(t.d['dropin']).name for name in s.original['DropInPaths'].split())
    t.stop('baseline', .5)
    t.start(False,2)
    assert t.d['phase'] == 'CANDIDATE_RUNNING'
    assert trial.argv_from_property(s.props['ExecStart']) == t.candidate_argv()


@pytest.mark.parametrize('prefix', [trial.TRIAL_PREFIX,trial.LEGACY_TRIAL_PREFIX])
def test_existing_current_or_legacy_trial_dropin_cannot_be_claimed(env,prefix):
    s,j,t = env
    other = '/run/systemd/system/'+trial.UNIT+'.d/'+prefix+'other.conf'
    s.files[other] = b'other trial guard'
    s.original['DropInPaths'] += ' '+other
    s.props['DropInPaths'] = s.original['DropInPaths']
    with pytest.raises(trial.Refused,match='another_trial'):prepare(env)
    assert j.value is None and not s.commands


def test_longer_foreign_dropin_refuses_before_any_journal_or_guard(env):
    s,j,t = env
    later = '/etc/systemd/system/'+trial.UNIT+'.d/'+'z'*65+'-foreign.conf'
    s.files[later] = b'foreign later override'
    s.original['DropInPaths'] += ' '+later
    s.props['DropInPaths'] = s.original['DropInPaths']
    with pytest.raises(trial.Refused,match='owned_dropin_not_last'):prepare(env)
    assert j.value is None and not s.commands


def test_rolling_attempt_window_may_expire_but_cumulative_history_cannot_rollback():
    old = seed();new = copy.deepcopy(old);new['recovery'][0]['attempt_count'] = 0
    trial.Trial.monotone(new, old)
    new['recovery'][0]['attempts'] = 0
    with pytest.raises(trial.Refused):trial.Trial.monotone(new, old)
