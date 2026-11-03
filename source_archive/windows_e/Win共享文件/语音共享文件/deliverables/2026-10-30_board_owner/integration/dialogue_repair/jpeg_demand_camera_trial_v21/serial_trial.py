"""Root-controlled, stepwise camera trial. No action runs at import time.

One CLI invocation performs one action. The private atomic journal is the
authority; an interrupted start is observed, never blindly repeated. Only an
explicit normal stop may affect the sole camera owner. No forced kill, native
reset, marker deletion, old-checkpoint restore or parallel publisher exists.
"""
import argparse
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import select
import socket
import stat
import subprocess
import sys
import time
import types

UNIT = 'aura-camera-ui.service'
OPS = '/home/root/aura-native-live-20261024/ops/be72669aa53de735'
BASE = OPS+'/pan-face-edge-v5/face-source-v17/entry.py'
LIBRARY = OPS+'/pan-face-edge-v5/native-operator-v1/libaura_native_operator.so'
SOURCE_ROOT = '/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura'
CHECKPOINT = SOURCE_ROOT.rsplit('/', 1)[0]+'/state/native-protection-checkpoint.json'
NATIVE_UNIT = '7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
NATIVE_MANIFEST = '5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
SAFE_PROPERTIES = ['MainPID', 'ActiveState', 'SubState', 'ExecStart', 'Restart',
                   'SendSIGKILL', 'TimeoutStopUSec', 'KillSignal', 'FragmentPath',
                   'DropInPaths', 'KillMode', 'Type', 'User', 'Group', 'WorkingDirectory',
                   'ExecStop', 'ExecStopPost', 'Job']
SCHEDULE_SOURCE = SOURCE_ROOT+'/board/vision/native_schedule.py'
SCHEDULE_SHA = 'dd42f2110cab499130706759bd2155dae0a161abb05d7b5563d319f29e956abf'
TRIAL_PREFIX = 'z'*64+'-aura-face-cadence-'
LEGACY_TRIAL_PREFIX = 'zzzzzz-aura-face-cadence-'


class Refused(RuntimeError):
    pass


class Pending(Refused):
    pass


def need(value, code):
    if not value:raise Refused(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def no_unit_job(value):
    return isinstance(value, str) and value.split() in ([], ['0'])


def trial_dropin(name):
    return Path(name).name.startswith((TRIAL_PREFIX, LEGACY_TRIAL_PREFIX))


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def parse(raw):
    need(len(raw) <= 262144, 'metadata_too_large')
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(Refused('nonfinite_json')))


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()


def argv_from_property(value):
    # All accepted commands use the original three simple arguments or the
    # candidate's five; spaces/quotes/escapes in these paths are not permitted.
    match = re.search(r'argv\[\]=([^;]+);', value or '')
    need(match is not None and str(value).count('argv[]=') == 1, 'ambiguous_unit_execstart')
    result = match.group(1).strip().split()
    need(all(re.fullmatch(r'[A-Za-z0-9_./:=+-]+', x) for x in result), 'unsafe_unit_execstart')
    return result


def guards(argv=None):
    text = '[Service]\nRestart=no\nSendSIGKILL=no\nTimeoutStopSec=infinity\nKillSignal=SIGTERM\n'
    if argv is not None:
        need(all(isinstance(x, str) and re.fullmatch(r'[A-Za-z0-9_./:=+-]+', x) for x in argv), 'unsafe_exec_argument')
        text += 'ExecStart=\nExecStart='+' '.join(argv)+'\n'
    return text.encode()


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = None
        self.unit_lock = None

    def __enter__(self):
        need(os.name == 'posix' and os.geteuid() == 0, 'actual_root_posix_required')
        parent = self.path.parent
        need(parent.is_absolute() and parent.resolve() == parent and not parent.is_symlink(), 'private_journal_path_required')
        info = parent.stat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o077,
             'private_root_owned_journal_directory_required')
        import fcntl
        # One action across all journal paths, plus a visible own-drop-in gate
        # below, prevents two independent journals claiming the same unit.
        global_fd = os.open('/run/aura-face-cadence-trial-action.lock',
                            os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
        global_info = os.fstat(global_fd)
        need(global_info.st_uid == 0 and not global_info.st_mode & 0o077, 'unit_action_lock_not_private')
        self.unit_lock = os.fdopen(global_fd, 'r+b')
        fcntl.flock(self.unit_lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        lock_path = parent/(self.path.name+'.lock')
        fd = os.open(str(lock_path), os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
        info = os.fstat(fd)
        need(info.st_uid == 0 and not info.st_mode & 0o077, 'journal_lock_not_private')
        self.lock = os.fdopen(fd, 'r+b')
        fcntl.flock(self.lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        return self

    def __exit__(self, *args):
        if self.lock:self.lock.close()
        if self.unit_lock:self.unit_lock.close()

    def read(self):
        if not self.path.exists():return None
        need(not self.path.is_symlink() and self.path.resolve() == self.path, 'journal_redirected')
        info = self.path.stat()
        need(info.st_uid == 0 and not info.st_mode & 0o077, 'journal_not_private')
        return parse(self.path.read_bytes())

    def save(self, value):
        raw = encode(value)
        temp = self.path.with_name(self.path.name+'.partial-'+str(os.getpid()))
        fd = os.open(str(temp), os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            os.replace(str(temp), str(self.path))
            parent = os.open(str(self.path.parent), os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(parent)
            finally:os.close(parent)
        finally:
            if temp.exists() and not temp.is_symlink():temp.unlink()


class System:
    """Small injectable OS adapter; no native/model context is constructed."""
    def now(self):return time.monotonic_ns()
    def sleep(self, seconds):time.sleep(seconds)
    def boot(self):return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def exists(self, name):return os.path.lexists(name)

    def read(self, name, *, private=False):
        path = Path(name)
        need(path.is_absolute() and path.resolve() == path and not path.is_symlink() and path.is_file(), 'metadata_redirected_or_missing')
        info = path.stat()
        if private:need(info.st_uid == 0 and not info.st_mode & 0o077, 'metadata_not_private')
        return path.read_bytes()

    def owner(self, pid):
        try:
            proc = Path('/proc')/str(pid)
            raw = (proc/'cmdline').read_bytes()
            ticks = (proc/'stat').read_text().rsplit(')', 1)[1].split()[19]
            return {'pid': int(pid), 'birth': str(ticks), 'cmd_sha256': digest(raw),
                    'argv': [part.decode() for part in raw.split(b'\0') if part]}
        except FileNotFoundError:return None

    def mapped(self, pid):
        try:return any(line.rstrip().split()[-1:] == [LIBRARY]
                       for line in (Path('/proc')/str(pid)/'maps').read_text().splitlines())
        except FileNotFoundError:return False

    def command(self, *args):
        # systemctl requests are no-block; timeout kills only this short-lived
        # client, never the service owner. The journal already records intent.
        result = subprocess.run(['systemctl', *args], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=8, check=False)
        need(result.returncode == 0, 'systemctl_request_failed')
        return result.stdout.decode().strip()

    def show(self):
        raw = self.command('show', '--all', UNIT, *['--property='+x for x in SAFE_PROPERTIES])
        result = dict(row.split('=', 1) for row in raw.splitlines() if '=' in row)
        missing = set(SAFE_PROPERTIES)-set(result)
        if missing == {'ExecStop', 'ExecStopPost'}:
            # The actual systemd249 build omits both empty command arrays even
            # with --all. Accept only this observed shape, after independent
            # full effective-property and every loaded source-file proof.
            full_raw = self.command('show', '--all', UNIT)
            full = dict(row.split('=', 1) for row in full_raw.splitlines() if '=' in row)
            need(not any(key.startswith('ExecStop') for key in full), 'effective_stop_hook_present')
            need(all(full.get(key) == value for key, value in result.items()
                     if key in SAFE_PROPERTIES), 'unit_changed_during_empty_stop_hook_proof')
            sources = [result['FragmentPath']]+result['DropInPaths'].split()
            for name in sources:
                text = self.read(name).decode('utf-8-sig')
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith(('#', ';')):continue
                    need(not line.startswith('.include') and
                         re.match(r'(?:ExecStop|ExecStopPost)\s*=', line) is None,
                         'stop_hook_assignment_or_include_in_unit_source')
            result.update(ExecStop='', ExecStopPost='')
        need(set(SAFE_PROPERTIES) <= set(result), 'unit_properties_incomplete')
        return result

    def write_dropin(self, name, raw, old_sha=None):
        path = Path(name)
        need(path.parent.parent == Path('/run/systemd/system') and
             path.parent.name == UNIT+'.d' and path.name.startswith(TRIAL_PREFIX), 'dropin_path_not_owned')
        path.parent.mkdir(mode=0o755, exist_ok=True)
        need(path.parent.resolve() == path.parent and not path.parent.is_symlink(), 'dropin_parent_redirected')
        if self.exists(name):
            current = self.read(name)
            if current == raw:return
            need(old_sha is not None and digest(current) == old_sha, 'owned_dropin_changed')
        else:need(old_sha is None, 'owned_dropin_disappeared')
        temp = path.with_name(path.name+'.partial-'+str(os.getpid()))
        fd = os.open(str(temp), os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(str(temp), name)

    def remove_dropin(self, name, expected):
        need(digest(self.read(name)) == expected, 'owned_dropin_changed')
        Path(name).unlink()

    def static_verify(self, directory, expected):
        root = Path(directory)
        need(root.is_absolute() and root.resolve() == root and not root.is_symlink(), 'candidate_directory_redirected')
        info = root.stat()
        need(info.st_uid == 0 and not info.st_mode & 0o077, 'candidate_directory_not_private')
        manifest = parse(self.read(str(root/'candidate-manifest.json'), private=True))
        need(digest(self.read(str(root/'candidate-manifest.json'), private=True)) == expected, 'candidate_manifest_changed')
        source = self.read(str(root/'entry.py'), private=True)
        need(digest(source) == manifest.get('candidate_sources', {}).get('entry.py'), 'candidate_entry_changed')
        module = types.ModuleType('_face_trial_static_verify')
        module.__file__ = str(root/'entry.py')
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        module.verify(root, expected)
        return manifest

    def checkpoint_validate(self, pin, boot):
        # These exact source modules are in the reviewed inherited manifest.
        # load_business_checkpoint imports only the original ABI definitions;
        # it does not create a model, runner or NativeContext or consume a SHA.
        sys.path.insert(0, SOURCE_ROOT)
        module = importlib.import_module('board.vision.native_protection')
        need(str(Path(module.__file__).resolve()) == SOURCE_ROOT+'/board/vision/native_protection.py',
             'original_checkpoint_validator_path_changed')
        loaded = module.load_business_checkpoint(pin, boot_id=boot)
        return loaded

    def health(self):
        # Fixed local metadata endpoint. No redirect, remote route or images.
        end = time.monotonic()+.75
        connection = socket.create_connection(('127.0.0.1', 8790), timeout=.3)
        try:
            need(connection.getpeername() == ('127.0.0.1', 8790), 'health_peer_changed')
            connection.sendall(b'GET /health HTTP/1.0\r\nHost: 127.0.0.1:8790\r\nConnection: close\r\n\r\n')
            connection.setblocking(False)
            raw = bytearray();header_end = None;size = None
            while True:
                remaining = end-time.monotonic()
                need(remaining > 0 and select.select([connection], [], [], remaining)[0], 'health_absolute_deadline')
                block = connection.recv(4096)
                need(block, 'health_incomplete')
                raw.extend(block)
                need(len(raw) <= 270336, 'health_response_too_large')
                if header_end is None:
                    at = raw.find(b'\r\n\r\n')
                    if at < 0:
                        need(len(raw) <= 8192, 'health_headers_too_large');continue
                    need(at <= 8192, 'health_headers_too_large')
                    lines = bytes(raw[:at]).decode('ascii').split('\r\n')
                    need(lines[0].split()[:2] in (['HTTP/1.0', '200'], ['HTTP/1.1', '200']), 'health_status_unavailable')
                    headers = {}
                    for line in lines[1:]:
                        key, value = line.split(':', 1);key = key.lower()
                        need(key not in headers, 'health_duplicate_header');headers[key] = value.strip()
                    need(headers.get('content-type', '').split(';')[0] == 'application/json'
                         and 'transfer-encoding' not in headers and headers.get('content-length', '').isdigit(), 'health_layout_changed')
                    size = int(headers['content-length']);need(size <= 262144, 'health_body_too_large')
                    header_end = at+4
                if len(raw)-header_end >= size:
                    return parse(bytes(raw[header_end:header_end+size]))
        finally:connection.close()


class Trial:
    def __init__(self, system, journal):
        self.s, self.j = system, journal
        self.d = journal.read()

    def save(self):self.j.save(self.d)

    def phase(self, name, **values):
        self.d.update(values);self.d['phase'] = name;self.save()

    def report(self):
        d = self.d or {}
        return {'phase': d.get('phase', 'UNPREPARED'), 'boot_id': d.get('boot'),
                'baseline_pid': d.get('baseline', {}).get('pid'),
                'candidate_pid': d.get('candidate', {}).get('pid'),
                'restored_pid': d.get('restored', {}).get('pid'),
                'journal_schema': d.get('schema'), 'unit': UNIT,
                'last_checkpoint_sha256': d.get('handoff', {}).get('sha256'),
                'forced_kill': False, 'database_opened': False,
                'old_checkpoint_restored': False}

    def invariants(self, *, guarded=True, argv=None, full=True):
        d = self.d
        need(d is not None and d.get('schema') == 'aura-face-cadence-trial-1', 'journal_schema_required')
        need(self.s.boot() == d['boot'], 'boot_changed_no_action')
        if full:
            need(digest(self.s.read(d['readback_path'], private=True)) == d['readback_sha256'], 'predecessor_readback_changed')
            for name, expected in d['pins'].items():
                need(digest(self.s.read(name)) == expected, 'source_pin_changed')
            self.s.static_verify(d['candidate_dir'], d['manifest_sha256'])
        props = self.s.show()
        need(props['FragmentPath'] == d['unit']['FragmentPath'], 'unit_fragment_changed')
        others = [p for p in props['DropInPaths'].split() if p != d['dropin']]
        need(others == d['unit']['DropInPaths'].split(), 'other_unit_dropins_changed')
        need(all(Path(name).name < Path(d['dropin']).name for name in others), 'owned_dropin_not_last')
        for name, expected in d['unit_files'].items():
            need(digest(self.s.read(name)) == expected, 'unit_source_changed')
        for key in ['KillMode', 'Type', 'User', 'Group', 'WorkingDirectory']:
            need(props[key] == d['unit'][key], 'unrelated_unit_property_changed')
        if guarded:
            need(d['dropin'] in props['DropInPaths'].split(), 'owned_guard_not_loaded')
            need(props['Restart'] == 'no' and props['SendSIGKILL'] == 'no'
                 and props['TimeoutStopUSec'] == 'infinity' and props['KillSignal'] in ('15', 'SIGTERM'),
                 'effective_no_force_kill_guards_required')
            need(digest(self.s.read(d['dropin'])) == d['dropin_sha256'], 'owned_dropin_changed')
        if argv is not None:need(argv_from_property(props['ExecStart']) == argv, 'effective_execstart_changed')
        return props

    def exact_owner(self, props, expected, argv):
        need(int(props['MainPID']) == expected['pid'], 'unit_mainpid_changed')
        observed = self.s.owner(expected['pid'])
        need(observed == expected and observed['argv'] == argv, 'owner_pid_birth_or_cmdline_changed')
        return observed

    def prepare(self, *, candidate_dir=None, manifest_sha256=None, readback=None,
                readback_sha256=None, boot=None, pid=None, birth=None):
        if self.d is None:
            need(sha(manifest_sha256) and sha(readback_sha256), 'explicit_reviewed_hashes_required')
            need(self.s.boot() == boot, 'explicit_boot_mismatch')
            raw = self.s.read(readback, private=True)
            need(digest(raw) == readback_sha256, 'readback_sha_mismatch')
            config = parse(raw)
            need(config.get('version') == 1 and config.get('enabled') is True
                 and config.get('board_boot_id') == boot and config.get('camera_pid') == pid
                 and config.get('camera_start_ticks') == str(birth)
                 and config.get('backend') == 'DPU_SFACE_INT8' and config.get('dimension') == 128,
                 'readback_owner_mismatch')
            owner = self.s.owner(pid)
            baseline_argv = ['/usr/bin/python3', '-B', BASE]
            need(owner is not None and owner['birth'] == str(birth) and owner['argv'] == baseline_argv
                 and owner['cmd_sha256'] == config.get('camera_cmdline_sha256'), 'actual_baseline_owner_mismatch')
            props = self.s.show()
            need(int(props['MainPID']) == pid and props['ActiveState'] == 'active'
                 and argv_from_property(props['ExecStart']) == baseline_argv, 'unit_not_actual_baseline')
            need(not props['ExecStop'] and not props['ExecStopPost'] and no_unit_job(props['Job']),
                 'unexpected_stop_hook_or_pending_unit_job')
            need(not any(trial_dropin(name) for name in props['DropInPaths'].split()),
                 'another_trial_already_owns_unit')
            pins = config.get('source_sha256', {})
            need(isinstance(pins, dict) and 1 <= len(pins) <= 128 and BASE in pins
                 and config['camera_config'] in pins and config['identity_config'] in pins, 'baseline_source_pins_required')
            for name, expected in pins.items():
                need(sha(expected) and digest(self.s.read(name)) == expected, 'baseline_source_changed')
            camera = parse(self.s.read(config['camera_config']))
            need(camera.get('identity') == {'enabled': True, 'config': config['identity_config']}
                 and camera.get('native_execution', {}).get('checkpoint_output') == CHECKPOINT,
                 'baseline_selection_changed')
            identity = parse(self.s.read(config['identity_config']))
            need(identity.get('database') == config['database'] and identity.get('model_id') == config['model_id']
                 and identity.get('result_ttl_ms') == config['result_ttl_ms'], 'identity_selection_changed')
            # Hash artifacts; never stat, open or connect to the identity DB.
            model_pins = {}
            for key in ('face_backend', 'feature_backend'):
                backend = identity.get(key, {})
                need(backend.get('kind') == {'face_backend': 'dpu_yunet', 'feature_backend': 'dpu_sface'}[key], 'int8_identity_required')
                for name, field in [('model', 'model_sha256'), ('manifest', 'manifest_sha256')]:
                    target, expected = backend[name], backend[field]
                    need(target != config['database'] and sha(expected) and digest(self.s.read(target)) == expected, 'model_artifact_changed')
                    model_pins[target] = expected
            manifest = self.s.static_verify(candidate_dir, manifest_sha256)
            need(digest(self.s.read(SCHEDULE_SOURCE)) == SCHEDULE_SHA, 'native_schedule_source_changed')
            model_pins[SCHEDULE_SOURCE] = SCHEDULE_SHA
            need(all(name not in pins or pins[name] == expected for name, expected in model_pins.items()),
                 'artifact_extension_would_replace_original_pin')
            health = self.s.health()
            native, handoff = native_health(health.get('dpu_schedule'))
            need(health.get('pid') == pid and health.get('board_boot_id') == boot
                 and not native['fenced'] and native['seed_loaded'] and self.s.mapped(pid), 'baseline_native_health_unavailable')
            baseline_health = {'service_epoch': health['service_epoch'], 'camera_epoch': health['camera_epoch'],
                               'native': native, 'previous_kernel_history': handoff.get('previous_kernel_history')}
            unit_files = {name: digest(self.s.read(name)) for name in
                          [props['FragmentPath']]+props['DropInPaths'].split()}
            nonce = digest((readback_sha256+manifest_sha256+str(self.s.now())).encode())[:16]
            dropin = '/run/systemd/system/'+UNIT+'.d/'+TRIAL_PREFIX+nonce+'.conf'
            need(all(Path(name).name < Path(dropin).name for name in props['DropInPaths'].split()),
                 'owned_dropin_not_last')
            need(not self.s.exists(dropin), 'trial_dropin_already_exists')
            self.d = {'schema': 'aura-face-cadence-trial-1', 'phase': 'PREPARE_INTENT', 'boot': boot,
                      'baseline': owner, 'baseline_argv': baseline_argv, 'baseline_camera': camera,
                      'baseline_health': baseline_health,
                      'baseline_config': config, 'readback_path': readback, 'readback_sha256': readback_sha256,
                      'candidate_dir': candidate_dir, 'manifest_sha256': manifest_sha256,
                      'pins': dict(pins, **model_pins), 'unit': props, 'unit_files': unit_files,
                      'dropin': dropin, 'dropin_sha256': digest(guards()), 'prepared_ns': self.s.now()}
            self.save()
        need(self.d['phase'] in ('PREPARE_INTENT', 'GUARDED'), 'prepare_wrong_phase')
        if self.d['phase'] == 'PREPARE_INTENT':
            self.s.write_dropin(self.d['dropin'], guards())
            self.s.command('daemon-reload')
            props = self.invariants(argv=self.d['baseline_argv'])
            self.exact_owner(props, self.d['baseline'], self.d['baseline_argv'])
            self.phase('GUARDED')
        else:
            props = self.invariants(argv=self.d['baseline_argv'])
            self.exact_owner(props, self.d['baseline'], self.d['baseline_argv'])
        return self.report()

    def fresh_checkpoint(self, owner, stop_ns):
        raw = self.s.read(CHECKPOINT, private=True)
        expected = digest(raw)
        document = parse(raw)
        seed = document.get('seed', {})
        need(document.get('schema') == 'aura-native-protection-checkpoint-2'
             and document.get('scope') == 'final_quiescent_before_native_owner_close'
             and document.get('source_unit_sha256') == NATIVE_UNIT
             and seed.get('source_manifest_sha256') == NATIVE_MANIFEST
             and seed.get('boot_id') == self.d['boot'] and seed.get('source_pid') == owner['pid']
             and str(seed.get('source_birth_ticks')) == owner['birth']
             and type(seed.get('captured_mono_ns')) is int
             and stop_ns <= seed['captured_mono_ns'] <= self.s.now(), 'checkpoint_not_fresh_exact_predecessor')
        prior = self.d.get('handoff')
        expected_history = (prior if prior else self.d['baseline_health']).get('previous_kernel_history')
        need(document.get('previous_kernel_history') == expected_history, 'previous_kernel_history_changed')
        if prior:
            need(seed.get('primary_calls', -1) >= prior['seed']['primary_calls'], 'primary_counter_rollback')
            self.monotone(seed, prior['seed'])
            for key, value in prior['sface_counters'].items():
                need(document.get('auxiliary', {}).get('sface_counters', {}).get(key, -1) >= value, 'sface_counter_rollback')
        else:
            self.health_not_rolled_back(seed, self.d['baseline_health']['native'])
        marker = CHECKPOINT+'.native-consumed-'+expected
        need(not self.s.exists(marker), 'fresh_checkpoint_already_consumed')
        loaded = self.s.checkpoint_validate({'path': CHECKPOINT, 'sha256': expected}, self.d['boot'])
        need(loaded['document'] == document and not loaded.get('new_kernel_boot'), 'original_same_boot_validation_required')
        return {'sha256': expected, 'seed': seed,
                'sface_counters': document['auxiliary']['sface_counters'],
                'previous_kernel_history': document.get('previous_kernel_history'),
                'consumption_marker': marker, 'source': owner, 'captured_after_stop_ns': stop_ns}

    @staticmethod
    def monotone(current, previous):
        for key in ('primary_calls', 'primary_period_overruns'):
            need(type(current.get(key)) is int and current[key] >= previous[key], 'native_counter_rollback')
        need(len(current.get('overruns', [])) == len(previous['overruns']) and
             all(type(a) is int and a >= b for a, b in zip(current['overruns'], previous['overruns'])), 'native_overrun_history_rollback')
        need(len(current.get('recovery', [])) == len(previous['recovery']), 'native_recovery_history_missing')
        for new, old in zip(current['recovery'], previous['recovery']):
            for key in ('faults', 'attempts', 'recoveries'):
                need(type(new.get(key)) is int and new[key] >= old[key], 'native_recovery_counter_rollback')
            need(not old.get('history_opaque') or new.get('history_opaque'), 'opaque_native_history_cleared')

    @staticmethod
    def health_not_rolled_back(seed, observed):
        for key in ('primary_calls', 'primary_period_overruns'):
            need(seed[key] >= observed[key], 'checkpoint_before_observed_counter')
        for index, key in enumerate(('yunet', 'sface'), 1):
            need(seed['overruns'][index] >= observed['optional_overruns'][key], 'checkpoint_optional_counter_rollback')
            for counter in ('faults', 'attempts', 'recoveries'):
                need(seed['recovery'][index-1][counter] >= observed['recovery'][index-1][counter], 'checkpoint_recovery_counter_rollback')

    def stop(self, which, wait_seconds):
        allowed = {'baseline': (('GUARDED',), 'STOPPING_BASELINE', 'BASELINE_STOPPED'),
                   'candidate': (('CANDIDATE_RUNNING', 'STARTING_CANDIDATE'), 'STOPPING_CANDIDATE', 'CANDIDATE_STOPPED'),
                   'restored': (('BASELINE_RESTORED', 'RESTORING'), 'STOPPING_RESTORED', 'RESTORED_STOPPED')}
        begin, stopping, ended = allowed[which]
        need(self.d and self.d['phase'] in begin+(stopping, ended), 'stop_wrong_phase')
        if self.d['phase'] == ended:
            props = self.invariants()
            need(int(props['MainPID']) == 0 and no_unit_job(props['Job']), 'stopped_phase_has_live_unit')
            return self.report()
        argv = self.candidate_argv() if which == 'candidate' else self.d['baseline_argv']
        props = self.invariants(argv=argv)
        owner = self.d.get(which)
        if owner is None:
            owner = self.s.owner(int(props['MainPID']))
            need(owner is not None and owner['argv'] == argv
                 and int(owner['birth']) > int(self.d['handoff']['source']['birth']), 'partial_start_owner_unconfirmed')
            self.d[which] = owner;self.save()
        if self.d['phase'] in begin:
            self.exact_owner(props, owner, argv)
            self.phase(stopping, stopping_owner=owner, stop_request_ns=self.s.now(), stop_issued=False)
        if not self.d['stop_issued']:
            # Intent is durable before the request. Repeating a normal stop is
            # allowed only for this same PID+birth, never a replacement owner.
            self.exact_owner(self.s.show(), owner, argv)
            self.d['stop_issued'] = True;self.save()
            self.s.command('stop', '--no-block', UNIT)
        end = self.s.now()+int(wait_seconds*1e9)
        while True:
            props = self.invariants(argv=argv, full=False)
            observed = self.s.owner(owner['pid'])
            need(observed is None or observed == owner, 'stop_owner_reused_or_changed')
            unsafe = OPS+'/native-run-'+self.d['boot']+'-'+str(owner['pid'])+'/UNSAFE_OWNER_RETAINED.json'
            need(not self.s.exists(unsafe), 'unsafe_native_owner_retained_no_replacement')
            if observed is None:
                need(int(props['MainPID']) == 0 and props['ActiveState'] in ('inactive', 'failed')
                     and no_unit_job(props['Job']), 'unit_has_another_owner_or_job')
                handoff = self.fresh_checkpoint(owner, self.d['stop_request_ns'])
                self.invariants(argv=argv)
                self.phase(ended, handoff=handoff)
                return self.report()
            need(int(props['MainPID']) in (0, owner['pid']), 'second_owner_appeared')
            if self.s.now() >= end:raise Pending('normal_stop_pending_owner_retained_no_force_kill')
            self.s.sleep(.2)

    def candidate_argv(self):
        return ['/usr/bin/python3', '-B', self.d['candidate_dir']+'/entry.py',
                '--manifest-sha256', self.d['manifest_sha256']]

    def change_exec(self, argv):
        raw = guards(argv)
        # Durable desired bytes allow only this script's interrupted own-file
        # replacement to be recovered; any different content fails closed.
        old = self.d['dropin_sha256']
        self.d['dropin_pending_sha256'] = digest(raw);self.save()
        self.s.write_dropin(self.d['dropin'], raw, old_sha=old)
        self.d['dropin_sha256'] = digest(raw);self.d.pop('dropin_pending_sha256', None);self.save()
        self.s.command('daemon-reload')
        self.invariants(argv=argv)

    def running_health(self, owner, predecessor):
        need(self.s.mapped(owner['pid']), 'approved_operator_library_not_mapped')
        runtime_path = OPS+'/native-run-'+self.d['boot']+'-'+str(owner['pid'])+'/config.json'
        runtime_raw = self.s.read(runtime_path, private=True)
        runtime = parse(runtime_raw)
        baseline = copy.deepcopy(self.d['baseline_camera'])
        baseline['native_execution']['seed']['sha256'] = predecessor['sha256']
        need(runtime == baseline, 'runtime_selection_or_non_seed_configuration_changed')
        need(self.s.read(predecessor['consumption_marker'], private=True) == (predecessor['sha256']+'\n').encode(),
             'same_boot_checkpoint_not_exclusively_consumed')
        h = self.s.health()
        need(h.get('pid') == owner['pid'] and h.get('board_boot_id') == self.d['boot']
             and h.get('role') == 'DPU_YOLOX_PERSON_PREVIEW' and not h.get('camera_error')
             and not h.get('detector_error') and type(h.get('capture_age_ms')) is int
             and 0 <= h['capture_age_ms'] < 1000 and type(h.get('observation_age_ms')) is int
             and 0 <= h['observation_age_ms'] < 750, 'fresh_single_owner_health_required')
        identity = h.get('identity', {})
        need(identity.get('ready') is True and not identity.get('error')
             and identity.get('backend') == 'DPU_SFACE_INT8', 'identity_health_not_ready')
        feature = identity.get('feature_inference', {})
        for key, value in predecessor['sface_counters'].items():
            need(type(feature.get(key)) is int and feature[key] >= value, 'sface_counter_not_inherited')
        faces = identity.get('face_targets', {})
        need(faces.get('ready') is True and not faces.get('error') and not faces.get('fault_latched')
             and type(faces.get('source_age_ms')) is int and 0 <= faces['source_age_ms'] < 1000,
             'face_source_health_not_ready')
        schedule = h.get('dpu_schedule', {})
        # Actual native_schedule.health shape is pinned and verified by the
        # source audit; projection is isolated here for precise fixture tests.
        native, handoff = native_health(schedule)
        need(handoff.get('mode') == 'native_exact_same_boot'
             and handoff.get('seed_sha256') == predecessor['sha256']
             and handoff.get('source_pid') == predecessor['source']['pid']
             and str(handoff.get('source_birth_ticks')) == predecessor['source']['birth'],
             'same_boot_native_handoff_proof_missing')
        need(not native.get('fenced') and native.get('seed_loaded')
             and native.get('boot_id', self.d['boot']) == self.d['boot'], 'native_health_fenced_or_unseeded')
        for key in ('primary_calls', 'primary_period_overruns'):
            need(type(native.get(key)) is int and native[key] >= predecessor['seed'][key], 'native_counter_rollback')
        for index, key in enumerate(('yunet', 'sface'), 1):
            need(native['optional_overruns'][key] >= predecessor['seed']['overruns'][index], 'native_optional_counter_rollback')
            for counter in ('faults', 'attempts', 'recoveries'):
                need(native['recovery'][index-1][counter] >= predecessor['seed']['recovery'][index-1][counter], 'native_recovery_counter_rollback')
            need(not predecessor['seed']['recovery'][index-1].get('history_opaque')
                 or native['recovery'][index-1].get('history_opaque'), 'opaque_native_history_cleared')
        need(handoff.get('previous_kernel_history') == predecessor.get('previous_kernel_history'), 'native_history_link_missing')
        return {'runtime_path': runtime_path, 'runtime_sha256': digest(runtime_raw),
                'service_epoch': h['service_epoch'], 'camera_epoch': h['camera_epoch'],
                'capture_frames': h['capture_frames'], 'detected_frames': h['detected_frames'],
                'native_primary_calls': native['primary_calls'], 'same_boot_verified': True}

    def start(self, restore, wait_seconds):
        begin, starting, running = ((('CANDIDATE_STOPPED', 'RESTORED_STOPPED'), 'RESTORING', 'BASELINE_RESTORED') if restore else
                                    (('BASELINE_STOPPED',), 'STARTING_CANDIDATE', 'CANDIDATE_RUNNING'))
        need(self.d and self.d['phase'] in begin+(starting, running), 'start_wrong_phase')
        argv = self.d['baseline_argv'] if restore else self.candidate_argv()
        if self.d['phase'] == running:
            name = 'restored' if restore else 'candidate'
            props = self.invariants(argv=argv)
            self.exact_owner(props, self.d[name], argv)
            self.running_health(self.d[name], self.d['handoff'])
            return self.report()
        if self.d['phase'] in begin:
            props = self.invariants()
            need(int(props['MainPID']) == 0 and props['ActiveState'] in ('inactive', 'failed')
                 and no_unit_job(props['Job']), 'owner_or_unit_job_still_present')
            handoff = self.d['handoff']
            need(self.s.owner(handoff['source']['pid']) is None, 'predecessor_still_alive')
            need(digest(self.s.read(CHECKPOINT, private=True)) == handoff['sha256']
                 and not self.s.exists(handoff['consumption_marker']), 'checkpoint_changed_or_already_consumed')
            self.s.checkpoint_validate({'path': CHECKPOINT, 'sha256': handoff['sha256']}, self.d['boot'])
            # A fresh attempt must not reuse a prior restored owner's record.
            # Its provenance remains in the sealed handoff.source. Until this
            # attempt is verified, stop() must bind the actual new sole owner.
            name = 'restored' if restore else 'candidate'
            self.d.pop(name, None)
            self.d.pop(name+'_health', None)
            self.phase(starting, start_issued=False, start_request_ns=self.s.now())
        if not self.d['start_issued']:
            self.change_exec(argv)
            self.invariants(argv=argv)
            props = self.s.show()
            need(int(props['MainPID']) == 0 and props['ActiveState'] in ('inactive', 'failed'), 'owner_appeared_before_start')
            need(not self.s.exists(self.d['handoff']['consumption_marker']), 'checkpoint_consumed_before_start')
            # A crash after this durable intent must never resend start. The
            # same action can only observe. No retry clears/rewinds a marker.
            self.d['start_issued'] = True;self.save()
            self.s.command('start', '--no-block', UNIT)
        end = self.s.now()+int(wait_seconds*1e9)
        stable = None
        last_error = 'new_owner_not_ready'
        while True:
            props = self.invariants(argv=argv, full=False)
            pid = int(props['MainPID'])
            if pid:
                owner = self.s.owner(pid)
                need(owner is not None and owner['argv'] == argv
                     and owner != self.d['handoff']['source'], 'unexpected_new_owner')
                need(int(owner['birth']) > int(self.d['handoff']['source']['birth']), 'new_owner_birth_not_after_predecessor')
                unsafe = OPS+'/native-run-'+self.d['boot']+'-'+str(pid)+'/UNSAFE_OWNER_RETAINED.json'
                need(not self.s.exists(unsafe), 'new_owner_native_state_retained_no_retry')
                if stable is not None:need(owner == stable[0], 'new_owner_replaced_during_validation')
                try:
                    proof = self.running_health(owner, self.d['handoff'])
                    if stable is None:stable = (owner, proof, self.s.now())
                    elif self.s.now()-stable[2] >= 1_000_000_000:
                        need(proof['service_epoch'] == stable[1]['service_epoch']
                             and proof['camera_epoch'] == stable[1]['camera_epoch']
                             and proof['capture_frames'] > stable[1]['capture_frames']
                             and proof['detected_frames'] > stable[1]['detected_frames'], 'new_owner_not_stably_progressing')
                        for previous in ('baseline_health', 'candidate_health'):
                            if previous in self.d:
                                need(proof['service_epoch'] != self.d[previous]['service_epoch']
                                     and proof['camera_epoch'] != self.d[previous]['camera_epoch'], 'owner_epoch_reused')
                        name = 'restored' if restore else 'candidate'
                        self.invariants(argv=argv)
                        self.exact_owner(self.s.show(), owner, argv)
                        self.phase(running, **{name: owner, name+'_health': proof})
                        return self.report()
                except (OSError, Refused) as exc:
                    # Refusal never becomes success. Keep the sole process;
                    # one can observe again or request its normal stop.
                    last_error = str(exc);stable = None
            if self.s.now() >= end:raise Pending('start_observation_pending_no_retry:'+last_error)
            self.s.sleep(.2)

    def finalize(self):
        need(self.d and self.d['phase'] in ('BASELINE_RESTORED', 'FINALIZING', 'COMPLETE'), 'finalize_wrong_phase')
        if self.d['phase'] == 'COMPLETE':
            props = self.invariants(guarded=False, argv=self.d['baseline_argv'])
            self.exact_owner(props, self.d['restored'], self.d['baseline_argv'])
            return self.report()
        if self.d['phase'] == 'BASELINE_RESTORED':
            props = self.invariants(argv=self.d['baseline_argv'])
            self.exact_owner(props, self.d['restored'], self.d['baseline_argv'])
            self.running_health(self.d['restored'], self.d['handoff'])
            self.phase('FINALIZING')
        if self.s.exists(self.d['dropin']):
            props = self.invariants(argv=self.d['baseline_argv'])
            self.exact_owner(props, self.d['restored'], self.d['baseline_argv'])
            self.running_health(self.d['restored'], self.d['handoff'])
            self.s.remove_dropin(self.d['dropin'], self.d['dropin_sha256'])
        self.s.command('daemon-reload')
        props = self.invariants(guarded=False, argv=self.d['baseline_argv'])
        for key in ('Restart', 'SendSIGKILL', 'TimeoutStopUSec', 'KillSignal'):
            need(props[key] == self.d['unit'][key], 'original_unit_guard_properties_not_restored')
        self.exact_owner(props, self.d['restored'], self.d['baseline_argv'])
        self.running_health(self.d['restored'], self.d['handoff'])
        self.phase('COMPLETE')
        return self.report()


def native_health(schedule):
    need(isinstance(schedule, dict), 'native_schedule_health_missing')
    handoff = schedule.get('protection_handoff')
    need(schedule.get('native_critical') is True and schedule.get('native_abi') == 2
         and isinstance(handoff, dict), 'native_schedule_projection_unavailable')
    optional = schedule.get('optional', {})
    native = {'primary_calls': schedule['primary_calls'], 'primary_period_overruns': schedule['primary_period_overruns'],
              'fenced': schedule['owner_fenced'], 'seed_loaded': schedule['seed_loaded'],
              'optional_overruns': {key: optional[key]['overruns'] for key in ('yunet', 'sface')},
              'recovery': [copy.deepcopy(schedule[key+'_recovery']) for key in ('yunet', 'sface')]}
    return native, handoff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'stop-baseline', 'start-candidate',
                                          'stop-candidate', 'stop-restored', 'restore', 'finalize', 'status'])
    parser.add_argument('--journal', required=True)
    parser.add_argument('--wait-seconds', type=float, default=20.)
    parser.add_argument('--candidate-dir')
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--readback')
    parser.add_argument('--readback-sha256')
    parser.add_argument('--expected-boot')
    parser.add_argument('--expected-pid', type=int)
    parser.add_argument('--expected-birth')
    args = parser.parse_args()
    result = None;trial = None
    try:
        need(0 < args.wait_seconds <= 60, 'bounded_wait_required')
        with Journal(args.journal) as journal:
            trial = Trial(System(), journal)
            if args.action == 'prepare':
                result = trial.prepare(candidate_dir=args.candidate_dir, manifest_sha256=args.manifest_sha256,
                    readback=args.readback, readback_sha256=args.readback_sha256,
                    boot=args.expected_boot, pid=args.expected_pid, birth=args.expected_birth)
            elif args.action == 'stop-baseline':result = trial.stop('baseline', args.wait_seconds)
            elif args.action == 'stop-candidate':result = trial.stop('candidate', args.wait_seconds)
            elif args.action == 'stop-restored':result = trial.stop('restored', args.wait_seconds)
            elif args.action == 'start-candidate':result = trial.start(False, args.wait_seconds)
            elif args.action == 'restore':result = trial.start(True, args.wait_seconds)
            elif args.action == 'finalize':result = trial.finalize()
            else:result = trial.report()
    except (OSError, ValueError, KeyError, IndexError, TypeError, Refused, subprocess.SubprocessError) as exc:
        result = dict(result or (trial.report() if trial is not None else {}),
                      status='PENDING' if isinstance(exc, Pending) else 'REFUSED',
                      reason=str(exc) if isinstance(exc, Refused) else type(exc).__name__,
                      forced_kill=False, automatic_replacement=False, database_opened=False)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get('status') not in ('REFUSED', 'PENDING') else 2


if __name__ == '__main__':
    raise SystemExit(main())
