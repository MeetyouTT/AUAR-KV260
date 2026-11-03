"""Cold-start barriers around ORIGINAL services. No reference, center or follow.

Not activated by this offline package. A fresh main/axis/CPU handoff, exact source
contract and separately installed activation receipt are mandatory. This entry
never stops/restarts an existing owner and never writes Native state. The sole
register operation is the unchanged, pinned original ID_STOP_ONLY program.
"""
import argparse
import ast
import copy
try:
    import fcntl
except ImportError:  # Offline Windows tests can import metadata rules; execution is still Linux-only.
    fcntl = None
import http.client
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time
import uuid

from recovery_rules import (APP, BENCHMARK, CAMERA, CLIENT, CLIENT_SHA, DAEMON_SHA,
                            GUI, IDSTOP_SHA, MANIFEST_SHA, VERIFIER_SHA, Hold,
                            config_patch, digest, encoded, gui_projection,
                            loaded_app, make_binding, next_history_expected, require, require_no_owners,
                            verify_final_pointer, verify_bootstrap_handoff, verify_idstop, verify_job,
                            verify_platform, verify_ready, verify_unloaded)

STATE_ROOT = Path('/var/lib/aura-boot-recovery/v1')
PACKAGE_ROOT = Path('/usr/local/lib/aura-boot-recovery/v1')
CHECKPOINT = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')
RELEASE = Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
PROPS = ('LoadState,MainPID,ControlPID,ActiveState,SubState,Job,Result,ExecMainStatus,ExecMainCode,'
         'InvocationID,ExecMainPID,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,'
         'ExecStart,ExecStartPre,ExecStartPost,Restart,KillMode,SendSIGKILL,TimeoutStartUSec,TimeoutStopUSec,FragmentPath,DropInPaths')


def regular(path, limit=67108864):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink(), 'REDIRECTED_METADATA_PATH')
    require(path.suffix.lower() not in {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.wav', '.mp3', '.png', '.jpg'}, 'PRIVATE_OR_MEDIA_PATH_REFUSED')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, 'METADATA_FILE_SHAPE')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) <= limit and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'METADATA_CHANGED_DURING_READ')
    return raw


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create(path, raw):
    path = Path(path)
    require(path.parent.resolve() == path.parent and not path.parent.is_symlink(), 'REDIRECTED_OUTPUT_PARENT')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fsync_directory(path.parent)


def replace_known(path, before, after):
    path = Path(path)
    require(regular(path) == before, 'CAS_SOURCE_CHANGED')
    mode = stat.S_IMODE(path.stat().st_mode)
    temp = path.with_name(path.name + '.boot-recovery-' + str(os.getpid()))
    create(temp, after)
    os.chmod(temp, mode)
    # All project writers must be frozen; recapture immediately before replace.
    require(regular(path) == before, 'CAS_SOURCE_CHANGED_BEFORE_RENAME')
    os.replace(temp, path)
    fsync_directory(path.parent)
    require(regular(path) == after, 'CAS_READBACK_MISMATCH')


def command(argv, timeout=6):
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def unit(name):
    result = command(['systemctl', 'show', name, '--property=' + PROPS])
    require(result.returncode == 0, 'SYSTEMD_METADATA_UNAVAILABLE')
    return dict(line.split('=', 1) for line in result.stdout.decode().splitlines() if '=' in line)


def process(pid, executable=False):
    path = Path('/proc') / str(pid)
    tail = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    result = dict(pid=int(pid), birth_ticks=tail[19], command_sha256=digest((path / 'cmdline').read_bytes()))
    if executable:
        result['executable_sha256'] = digest(regular((path / 'exe').resolve()))
    return result


def owner_scan(motion_only=False):
    result = dict(complete=True, owners=[], unreadable=[])
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            maps = (path / 'maps').read_text()
            targets = []
            for fd in (path / 'fd').iterdir():
                try:
                    targets.append(str(fd.readlink()))
                except FileNotFoundError:
                    continue
            motion = 'libvsrv' in maps or '/dev/mem' in maps or '/dev/mem' in targets
            native = any(name in maps for name in ('libvart', 'libaura_native_operator'))
            device = any(name.startswith(('/dev/dri/renderD', '/dev/dpu')) for name in targets)
            if motion or (not motion_only and (native or device)):
                result['owners'].append(process(path.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (PermissionError, OSError, ValueError, IndexError):
            result['complete'] = False
            result['unreadable'].append(int(path.name))
    return result


def platform_metadata():
    firmware = Path('/proc/device-tree/fpga-full/firmware-name')
    overlays = Path('/sys/kernel/config/device-tree/overlays')
    require(overlays.is_dir(), 'OVERLAY_METADATA_UNAVAILABLE')
    links, unexpected = [], []
    for driver in Path('/sys/bus/platform/drivers').iterdir():
        if 'zocl' not in driver.name.lower():
            continue
        for entry in driver.iterdir():
            if not entry.is_symlink():
                continue
            target = str(entry.resolve())
            if target.startswith('/sys/devices/'):
                links.append(target)
            elif entry.name != 'module' or not target.startswith('/sys/module/'):
                unexpected.append(str(entry))
    return dict(firmware=firmware.read_bytes().rstrip(b'\0').decode() if firmware.exists() else None,
                fpga_state=Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),
                vart=regular('/etc/vart.conf').decode(),
                fdt_sha256=digest(Path('/sys/firmware/fdt').read_bytes()),
                overlays=[dict(name=p.name, status=(p / 'status').read_text().strip()) for p in overlays.iterdir() if p.is_dir()],
                render=[dict(name=p.name, device=str((p / 'device').resolve())) for p in Path('/sys/class/drm').glob('renderD*')],
                zocl_links=links, unexpected_zocl_links=unexpected)


def get_metadata(port, path):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        body = response.read(2097153)
        require(response.status == 200 and len(body) <= 2097152, 'LOCAL_METADATA_RESPONSE')
        return json.loads(body)
    finally:
        connection.close()


def original_verify(aura, binding):
    path = aura / 'board/runtime/audio/face_gallery_readback.py'
    source = regular(path)
    require(digest(source) == VERIFIER_SHA, 'ORIGINAL_VERIFIER_SOURCE_CHANGED')
    tree = ast.parse(source)
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FaceGalleryReadback')
    method = copy.deepcopy(next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == '_verify'))
    method.decorator_list = []
    scope = dict(Path=Path, hashlib=__import__('hashlib'), json=json)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path) + '::<original-metadata-only-_verify>', 'exec'), scope)
    scope['_verify'](binding)  # Never construct FaceGalleryReadback or a store.


class Recovery:
    def __init__(self, contract_path):
        require(platform.system() == 'Linux' and platform.machine() == 'aarch64' and os.geteuid() == 0
                and sys.dont_write_bytecode, 'BOARD_ROOT_B_INTERPRETER_REQUIRED')
        require(Path(contract_path) == PACKAGE_ROOT / 'contract.json', 'INSTALLED_CONTRACT_PATH_REQUIRED')
        self.contract_raw = regular(contract_path)
        self.contract = json.loads(self.contract_raw)
        self.contract_sha = digest(self.contract_raw)
        activation = json.loads(regular(PACKAGE_ROOT / 'activation.json'))
        require(activation.get('schema') == 'aura-boot-recovery-activation-1' and activation.get('enabled') is True
                and activation.get('contract_sha256') == self.contract_sha, 'CANDIDATE_NOT_ACTIVATED')
        require(self.contract.get('schema') == 'aura-boot-recovery-contract-1'
                and self.contract.get('fresh_handoff_approved') is True, 'FRESH_HANDOFF_CONTRACT_REQUIRED')
        self.activation = activation
        for path, pin in activation['installed_files'].items():
            require(digest(regular(path)) == pin, 'INSTALLED_CANDIDATE_CHANGED')
        self.boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        require(str(uuid.UUID(self.boot)) == self.boot, 'BOOT_UUID')
        require(STATE_ROOT.resolve() == STATE_ROOT and STATE_ROOT.stat().st_uid == 0
                and stat.S_IMODE(STATE_ROOT.stat().st_mode) == 0o700, 'STATE_DIRECTORY_OWNER')
        self.lock = (STATE_ROOT / 'operation.lock').open('a+')
        fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.tx = STATE_ROOT / 'boots' / self.boot
        self.tx.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(self.tx.resolve() == self.tx and not self.tx.is_symlink(), 'TRANSACTION_PATH_REDIRECTED')

    def pin(self, pin):
        raw = regular(pin['path'])
        require(digest(raw) == pin['sha256'], 'PUBLIC_SOURCE_PIN_CHANGED')
        return raw

    def source_snapshot(self):
        for path, pin in self.activation['installed_files'].items():
            require(digest(regular(path)) == pin, 'INSTALLED_CANDIDATE_CHANGED')
        active_path = STATE_ROOT / 'active-source.json'
        active_present = os.path.lexists(active_path)
        active_raw = regular(active_path) if active_present else b'null\n'
        active = json.loads(active_raw) if active_present else self.contract['initial_source_state']
        require(active['contract_sha256'] == (self.contract_sha if active_present else 'INITIAL_CONTRACT'), 'SOURCE_STATE_CONTRACT_CHANGED')
        startup_raw = regular(self.contract['startup_path'])
        require(digest(startup_raw) == active['startup_sha256'], 'STARTUP_CHANGED_RESEAL_REQUIRED')
        startup = json.loads(startup_raw)
        aura = Path(startup['runtime']) / 'aura'
        require(str(aura) == self.contract['runtime_aura'] and len(startup['component_sha256']) == self.contract['component_count'], 'RUNTIME_SOURCE_SET_CHANGED')
        for relative, pin in startup['component_sha256'].items():
            require(not Path(relative).is_absolute() and '..' not in Path(relative).parts, 'COMPONENT_PATH_ESCAPE')
            require(digest(regular(aura / relative)) == pin, 'COMPONENT_SOURCE_CHANGED')
        ui_path = aura / 'config/board_avatar_gtk.json'
        ui_raw = regular(ui_path)
        require(digest(ui_raw) == active['ui_sha256'], 'UI_SOURCE_CHANGED')
        ui = json.loads(ui_raw)
        require(ui['board_business']['face_readback'] == active['selected_pin'], 'SELECTED_SPEC_CHANGED')
        selected = json.loads(self.pin(active['selected_pin']))
        require(selected['source_sha256'] == active['selected_sources'], 'SELECTED_SOURCE_SET_CHANGED')
        for path, pin in selected['source_sha256'].items():
            require(digest(regular(path)) == pin, 'CAMERA_SELECTED_SOURCE_CHANGED')
        for path, pin in self.contract['immutable_files'].items():
            require(digest(regular(path)) == pin, 'APPROVED_CAMERA_OR_LAUNCHER_SOURCE_CHANGED')
        for name, expected in self.contract['original_units'].items():
            current = unit(name)
            paths = {current['FragmentPath']} | set(current['DropInPaths'].split())
            own = {p for p in self.activation['installed_files'] if p.startswith('/etc/systemd/system/' + name + '.d/')}
            require(paths == set(expected['source_sha256']) | own, 'ORIGINAL_UNIT_SOURCE_SET_CHANGED')
            for path, pin in expected['source_sha256'].items():
                require(digest(regular(path)) == pin, 'ORIGINAL_UNIT_SOURCE_CHANGED')
        for name in self.contract.get('absent_platform_units', []):
            require(unit(name).get('LoadState') == 'not-found', 'UNREVIEWED_PLATFORM_STARTUP_UNIT_APPEARED')
        return dict(active=active, active_source_raw=active_raw, active_source_present=active_present,
                    startup=startup, startup_raw=startup_raw, ui=ui, ui_raw=ui_raw,
                    ui_path=ui_path, aura=aura, selected=selected)

    def quiet(self):
        """Queued ordered start jobs are allowed; actual owner processes are not."""
        pending = {}
        for name in (CAMERA, GUI):
            current = unit(name)
            require(current['MainPID'] == '0' and current['ActiveState'] in {'inactive', 'activating'}
                    and current['SubState'] in {'dead', 'start-pre'}, 'EXISTING_SERVICE_OWNER_NO_REPLACEMENT')
            control = int(current.get('ControlPID', '0'))
            require(control in {0, os.getpid()}, 'ANOTHER_START_HELPER_PRESENT')
            if current.get('Job'):
                pending[name] = current
        # Pending loader work can have NO process yet. Inspect the whole job
        # queue on every boundary, not only while camera/GUI have start jobs.
        result = command(['systemctl', 'list-jobs', '--no-legend', '--no-pager', '--plain'])
        require(result.returncode == 0, 'QUEUED_START_JOB_METADATA_UNAVAILABLE')
        rows = [line.split() for line in result.stdout.decode().splitlines() if line.strip()]
        require(all(len(row) == 4 and row[0].isdigit() for row in rows), 'SYSTEMD_JOB_QUEUE_SHAPE_UNKNOWN')
        for name, current in pending.items():
            matches = [row for row in rows if row[1] == name]
            expected_state = 'running' if int(current.get('ControlPID', '0')) == os.getpid() else 'waiting'
            require(len(matches) == 1 and matches[0][0] == current['Job'].split()[0]
                    and matches[0][2:] == ['start', expected_state], 'PENDING_JOB_IS_NOT_OUR_ORDERED_START')
        for _, name, job_type, job_state in rows:
            if name in {CAMERA, GUI}:
                require(name in pending, 'SERVICE_JOB_CHANGED_DURING_QUEUE_SCAN')
                continue  # Individually checked above, including helper identity.
            current = unit(name)
            if name == 'aura-original-wide-prepare.service':
                require(int(current.get('MainPID', '0')) == os.getpid() and job_type == 'start'
                        and job_state == 'running', 'ANOTHER_PLATFORM_PREPARE_JOB_PENDING')
                continue
            entries = ' '.join(current.get(key, '') for key in ('ExecStart', 'ExecStartPre', 'ExecStartPost')).lower()
            # Own Python ID_STOP_ONLY jobs also touch the platform. Pending
            # actions block advancement; observe_job binds an existing action
            # to its durable unit/InvocationID without another submission.
            own_action_job = name.startswith('aura-boot-wide-')
            loader_name = bool(re.search(r'dfx|xmutil|fpga|zocl|dpu-auto', name, flags=re.IGNORECASE))
            loader_entry = ('dfx-mgr-client' in entries or 'dfx-mgrd' in entries
                            or ('xmutil' in entries and ('loadapp' in entries or 'unloadapp' in entries)))
            require(not own_action_job and not loader_name and not loader_entry, 'OTHER_PLATFORM_OR_DAEMON_JOB_PENDING_NO_DFX')
        for path in Path('/proc').iterdir():
            if not path.name.isdigit() or int(path.name) == os.getpid():
                continue
            try:
                groups = (path / 'cgroup').read_text()
                require(not any(name in groups for name in (CAMERA, GUI)), 'OLD_SERVICE_CGROUP_PROCESS_PRESENT')
                argv = (path / 'cmdline').read_bytes().split(b'\0')
                names = {part.rsplit(b'/', 1)[-1] for part in argv if part}
                require(b'dfx-mgr-client' not in names
                        and not (b'xmutil' in names and ({b'loadapp', b'unloadapp'} & set(argv))),
                        'OTHER_OR_PENDING_ORIGINAL_DFX_CLIENT_OBSERVE_ONLY')
            except (FileNotFoundError, ProcessLookupError):
                continue
        require_no_owners(owner_scan())

    def daemon_owner(self):
        state = unit('dfx-mgr.service')
        require(state['ActiveState'] == 'active' and state['SubState'] == 'running' and int(state['MainPID']) > 0, 'DAEMON_NOT_RUNNING')
        require(not state.get('Job'), 'DAEMON_JOB_PENDING_NO_DFX')
        value = process(state['MainPID'], executable=True)
        require(value['executable_sha256'] == DAEMON_SHA and digest(regular(CLIENT)) == CLIENT_SHA, 'ORIGINAL_DAEMON_CLIENT_CHANGED')
        return value

    def original_release(self):
        raw = regular(RELEASE / 'candidate-manifest.json')
        require(digest(raw) == MANIFEST_SHA, 'ORIGINAL_WIDE_MANIFEST_CHANGED')
        manifest = json.loads(raw)
        require(manifest['app'] == APP and manifest['abi'] == 2 and manifest['build_id'] == 0x10282601
                and len(manifest['runtime_files']) == 4 and len(manifest['payload_files']) == 3, 'ORIGINAL_RELEASE_SHAPE')
        for path, pin in manifest['runtime_files'].items():
            require(digest(regular(path)) == pin, 'ORIGINAL_FIRMWARE_CHANGED')
        for name, pin in manifest['payload_files'].items():
            require(name in {'libvsrv.so', 'vsrv_driver.py', 'vsrv_transport.py'}
                    and digest(regular(RELEASE / 'driver' / name)) == pin, 'ORIGINAL_DRIVER_CHANGED')
        require(digest(regular(RELEASE / 'bench_identity_stop.py')) == IDSTOP_SHA, 'ORIGINAL_IDSTOP_CHANGED')

    def kernel_marker_path(self):
        policy = self.contract['native_boot_policy']
        directory = Path(policy['new_boot_marker_directory'])
        require(directory.is_absolute() and not directory.is_symlink() and directory.resolve() == directory,
                'ORIGINAL_NEW_BOOT_MARKER_DIRECTORY_REDIRECTED')
        return directory / ('kernel-boot-' + self.boot + '.consumed')

    def current_domain_consumed(self):
        marker = self.kernel_marker_path()
        # lexists includes an original partial record, symlink or any other
        # path object. Neither marker family is changed by this wrapper.
        return os.path.lexists(marker)

    def checkpoint_gate(self, snapshot, checkpoint):
        policy = self.contract['native_boot_policy']
        return verify_final_pointer(
            checkpoint, os.path.lexists(str(CHECKPOINT) + '.native-consumed-' + digest(checkpoint)),
            snapshot['active']['predecessor'], current_boot=self.boot,
            allow_new_kernel_boot=policy['allow_new_kernel_boot'],
            current_domain_consumed=self.current_domain_consumed())

    def run_history_gate(self, kind, history, *, checkpoint_pin=None, predecessor=None,
                         normal_expected_pin=None, normal_result_pin=None):
        request = dict(schema='aura-original-history-gate-request-1', kind=kind, boot_id=self.boot,
                       adapter_pin=self.contract['history_adapter_pin'], history_expected=history)
        if checkpoint_pin is not None:
            request.update(checkpoint_pin=checkpoint_pin, source_boot=predecessor['boot_id'],
                           source_owner=predecessor['camera_owner'], source_manifest_sha256=self.contract['native_manifest']['sha256'],
                           new_boot_marker_directory=self.contract['native_boot_policy']['new_boot_marker_directory'])
        if normal_expected_pin is not None:
            request['normal_stop_expected_pin'] = normal_expected_pin
            request['normal_stop_complete_result_pin'] = normal_result_pin
        raw = encoded(request)
        request_sha = digest(raw)
        request_path = self.tx / ('history-request-' + request_sha + '.json')
        if request_path.exists():
            require(regular(request_path) == raw, 'ORIGINAL_HISTORY_REQUEST_CHANGED')
        else:
            create(request_path, raw)
        recipe = regular(PACKAGE_ROOT / 'original_history_gate.py')
        result = subprocess.run(['/usr/bin/python3', '-B', '-I', '-S', '-', '--request', str(request_path),
                                 '--request-sha256', request_sha], input=recipe, capture_output=True, timeout=25)
        require(result.returncode == 0 and not result.stderr and len(result.stdout) <= 2097152,
                'EXACT_FINAL_OR_ORIGINAL_COMPLETE_HISTORY_NOT_VERIFIED')
        value = json.loads(result.stdout)
        require(value.get('schema') == 'aura-original-history-gate-result-1' and value.get('request_sha256') == request_sha
                and value.get('kind') == kind and value.get('boot_id') == self.boot
                and value.get('adapter_sha256') == self.contract['history_adapter_pin']['sha256']
                and value.get('checkpoint_pin') == checkpoint_pin and value.get('history_expected') == history
                and value.get('complete_ordered_history_verified') is True and value.get('original_calls_only') is True
                and value.get('checkpoint_or_marker_written') is False and value.get('native_context_created') is False
                and value.get('model_or_device_opened') is False, 'ORIGINAL_HISTORY_RESULT_NOT_BOUND_TO_REQUEST')
        result_path = self.tx / ('history-result-' + request_sha + '.json')
        result_raw = encoded(value)
        if result_path.exists():
            require(regular(result_path) == result_raw, 'ORIGINAL_HISTORY_RESULT_CHANGED')
        else:
            create(result_path, result_raw)
        return dict(request_pin=dict(path=str(request_path), sha256=request_sha),
                    result_pin=dict(path=str(result_path), sha256=digest(result_raw)), history_expected=history)

    def check_prestart_history(self, snapshot, checkpoint):
        history = snapshot['active']['history_expected']
        source = snapshot['active']['predecessor']
        pin = dict(path=str(CHECKPOINT), sha256=digest(checkpoint))
        if source['boot_id'] != self.boot:
            require(type(history['archive_count']) is int and history['archive_count'] < 64,
                    'NEW_BOOT_WOULD_EXCEED_ORIGINAL_COMPLETE_HISTORY_BOUND')
            return self.run_history_gate('cold_predecessor', history, checkpoint_pin=pin, predecessor=source)
        # This pin is supplied only by the existing CPU/main normal-stop flow.
        # No stop intent, fresh final or approval boolean is fabricated here.
        proof = json.loads(regular(STATE_ROOT / 'same-boot-history.proof.json'))
        require(proof.get('schema') == 'aura-existing-cpu-same-boot-history-pins-1', 'GENUINE_CPU_SAME_BOOT_PROOF_PINS_REQUIRED')
        return self.run_history_gate('same_boot_resume', history, checkpoint_pin=pin, predecessor=source,
                                     normal_expected_pin=proof['expected_pin'], normal_result_pin=proof['complete_result_pin'])

    def history_bytes_unchanged(self, proof):
        self.pin(proof['request_pin'])
        self.pin(proof['result_pin'])
        expected = proof['history_expected']
        for row in expected['archives']:
            self.pin(dict(path=row['path'], sha256=row['sha256']))
        self.pin(expected['legacy_pin'])

    def verify_gate_history(self, gate):
        proof = gate['history_proof']
        request = json.loads(self.pin(proof['request_pin']))
        result = json.loads(self.pin(proof['result_pin']))
        checkpoint_pin = dict(path=str(CHECKPOINT), sha256=gate['checkpoint_sha256'])
        expected_kind = 'same_boot_resume' if gate['predecessor']['boot_id'] == self.boot else 'cold_predecessor'
        require(request['kind'] == result['kind'] == expected_kind and request['checkpoint_pin'] == result['checkpoint_pin'] == checkpoint_pin
                and request['boot_id'] == result['boot_id'] == self.boot
                and request['source_owner'] == gate['predecessor']['camera_owner']
                and request['source_boot'] == gate['predecessor']['boot_id']
                and request['adapter_pin'] == self.contract['history_adapter_pin']
                and result['adapter_sha256'] == self.contract['history_adapter_pin']['sha256']
                and request['history_expected'] == result['history_expected'] == proof['history_expected']
                and result['request_sha256'] == proof['request_pin']['sha256'], 'CAMERA_GATE_HISTORY_PROOF_NOT_EXACT_FINAL')
        self.pin(checkpoint_pin)
        self.history_bytes_unchanged(proof)

    def accepted_live_history(self, gate, handoff):
        self.verify_gate_history(gate)
        history = next_history_expected(gate['history_proof']['history_expected'], gate, handoff, self.boot)
        if gate['predecessor']['boot_id'] == self.boot:
            marker = str(CHECKPOINT) + '.native-consumed-' + gate['checkpoint_sha256']
            require(regular(marker, 256) == (gate['checkpoint_sha256'] + '\n').encode(), 'ORIGINAL_SAME_BOOT_CONSUMPTION_NOT_PROVEN')
        else:
            marker = json.loads(regular(self.kernel_marker_path(), 262144))
            require(marker.get('schema') == 'aura-native-current-kernel-consumption-1' and marker.get('boot') == self.boot
                    and marker.get('source_checkpoint_sha256') == gate['checkpoint_sha256']
                    and marker.get('archive_path') == history['head']['archive_path']
                    and marker.get('archive_sha256') == history['head']['archive_sha256']
                    and type(marker.get('captured_mono_ns')) is int and 0 < marker['captured_mono_ns'] <= time.monotonic_ns(),
                    'ORIGINAL_CURRENT_BOOT_COMMIT_LINK_NOT_PROVEN')
        proof = self.run_history_gate('running_archive_chain', history)
        return history, proof

    def once(self, action, argv, allow_submit=True):
        """Durable once-only submission; reentry observes the SAME transient unit."""
        unit_name = 'aura-boot-wide-' + self.boot + '-' + action + '.service'
        intent_path = self.tx / (action + '-intent.json')
        out_path, err_path = self.tx / (action + '.stdout.raw'), self.tx / (action + '.stderr.raw')
        intent = dict(boot_id=self.boot, contract_sha256=self.contract_sha, unit=unit_name,
                      argv=argv, daemon=self.daemon_owner(), startup_sha256=digest(regular(self.contract['startup_path'])))
        if intent_path.exists():
            require(json.loads(regular(intent_path)) == intent, 'EXISTING_INTENT_CONTEXT_CHANGED')
        else:
            require(allow_submit, 'NO_EXISTING_JOB_TO_OBSERVE')
            require(unit(unit_name).get('LoadState') == 'not-found', 'UNEXPLAINED_EXISTING_OS_JOB')
            create(out_path, b'')
            create(err_path, b'')
            create(intent_path, encoded(intent))  # fsync BEFORE any D-Bus dispatch.
            args = ['systemd-run', '--unit=' + unit_name, '--no-block', '--service-type=exec', '--remain-after-exit',
                    '--property=Restart=no', '--property=TimeoutStartSec=infinity', '--property=RuntimeMaxSec=infinity',
                    '--property=TimeoutStopSec=infinity', '--property=KillMode=process', '--property=SendSIGKILL=no',
                    '--property=StandardInput=null', '--property=StandardOutput=append:' + str(out_path),
                    '--property=StandardError=append:' + str(err_path), '--property=UMask=0077'] + argv
            try:
                submitted = command(args, timeout=8)
                receipt = dict(submit_returncode=submitted.returncode, completion_claimed=False)
            except subprocess.TimeoutExpired:
                receipt = dict(submission_outcome='UNKNOWN_OBSERVE_SAME_UNIT', completion_claimed=False)
            create(self.tx / (action + '-submission.json'), encoded(receipt))
        invocation_path = self.tx / (action + '-invocation.json')
        deadline = time.monotonic() + 25
        while True:
            current = unit(unit_name)
            invocation = current.get('InvocationID', '')
            if invocation:
                if invocation_path.exists():
                    require(json.loads(regular(invocation_path)) == {'InvocationID': invocation}, 'OS_JOB_REPLACED')
                else:
                    create(invocation_path, encoded({'InvocationID': invocation}))
            if current.get('SubState') == 'exited' or current.get('ActiveState') == 'failed':
                break
            require(time.monotonic() < deadline, 'UNKNOWN_OR_PENDING_OS_JOB_NO_RETRY')
            time.sleep(.25)
        out, err = regular(out_path, 65536), regular(err_path, 65536)
        result = verify_job(current, invocation, out, err, action)
        return result, current

    def observe_job(self, action):
        require(action in {'list', 'remove', 'load', 'idstop'}, 'UNKNOWN_ORIGINAL_ACTION')
        self.source_snapshot()
        path = self.tx / (action + '-intent.json')
        require(path.exists(), 'NO_EXISTING_JOB_TO_OBSERVE')
        intent = json.loads(regular(path))
        value, state = self.once(action, intent['argv'], allow_submit=False)
        # Observation never declares a loaded/unloaded platform from an OS exit alone.
        metadata = platform_metadata()
        if action == 'remove':
            require(not (self.tx / 'load-intent.json').exists(), 'REMOVE_FINISHED_LOAD_STAGE_EXISTS_OBSERVE_LOAD')
            verify_unloaded(metadata)
        elif action == 'load':
            verify_platform(metadata, APP)
        elif action == 'idstop':
            verify_platform(metadata, APP)
            verify_idstop(json.loads(regular(self.tx / 'id-stop.json')), self.boot, MANIFEST_SHA)
        return dict(status='EXISTING_ORIGINAL_JOB_OBSERVED_NO_SUBMISSION', action=action,
                    InvocationID=state['InvocationID'], boot_id=self.boot, original_list_app=value)

    def prepared(self):
        result = json.loads(regular(self.tx / 'prepared.json'))
        require(result['boot_id'] == self.boot and result['contract_sha256'] == self.contract_sha, 'PREPARED_CONTEXT_CHANGED')
        value = platform_metadata()
        verify_platform(value, APP)
        require(value['fdt_sha256'] == result['context']['fdt_sha256'], 'PREPARED_FDT_CHANGED')
        report = json.loads(regular(self.tx / 'id-stop.json'))
        verify_idstop(report, self.boot, MANIFEST_SHA)
        require(digest(regular(self.tx / 'id-stop.json')) == result['idstop_sha256'], 'IDSTOP_RECEIPT_CHANGED')
        return result

    def prepare(self):
        snapshot = self.source_snapshot()
        self.original_release()
        if (self.tx / 'prepared.json').exists():
            self.prepared()
            require_no_owners(owner_scan(motion_only=True))
            return dict(status='ALREADY_PREPARED_NO_DFX_RESUBMISSION', boot_id=self.boot)
        require(self.boot != self.contract['installed_boot_id'], 'INSTALL_BOOT_REQUIRES_MANUAL_MAIN_AXIS_RECOVERY')
        self.quiet()
        cp = regular(CHECKPOINT, 262144)
        cp_sha = self.checkpoint_gate(snapshot, cp)
        require(json.loads(cp)['seed']['boot_id'] != self.boot, 'COLD_PREDECESSOR_BOOT_REQUIRED')
        history_proof = self.check_prestart_history(snapshot, cp)
        sealed = self.tx / ('predecessor-final-' + cp_sha + '.json')
        if sealed.exists():
            require(regular(sealed) == cp, 'SEALED_FINAL_CHANGED')
        else:
            create(sealed, cp)
        daemon = self.daemon_owner()

        def boundary():
            now = self.source_snapshot()
            require(now['startup_raw'] == snapshot['startup_raw'] and regular(CHECKPOINT, 262144) == cp, 'SOURCE_OR_FINAL_CHANGED_DURING_PREPARE')
            require(self.checkpoint_gate(now, cp) == cp_sha, 'CHECKPOINT_ROUTE_CHANGED_DURING_PREPARE')
            self.history_bytes_unchanged(history_proof)
            require(self.daemon_owner() == daemon, 'DAEMON_OWNER_CHANGED')
            self.quiet()

        boundary()
        initial_path = self.tx / 'initial-platform.json'
        if initial_path.exists():
            initial = json.loads(regular(initial_path))
            require(initial['boot_id'] == self.boot and initial['contract_sha256'] == self.contract_sha
                    and initial['checkpoint_sha256'] == cp_sha and initial['daemon'] == daemon
                    and initial['startup_sha256'] == digest(snapshot['startup_raw']), 'INITIAL_PLATFORM_CONTEXT_CHANGED')
            require(digest(regular(self.tx / 'list.stdout.raw', 65536)) == initial['list_stdout_sha256'], 'INITIAL_LIST_REPLY_CHANGED')
            app = loaded_app(regular(self.tx / 'list.stdout.raw', 65536))
            require(app == initial['app'], 'INITIAL_LIST_IDENTITY_CHANGED')
            self.once('list', [CLIENT, '-listPackage'], allow_submit=False)
        else:
            app, _ = self.once('list', [CLIENT, '-listPackage'])
            verify_platform(platform_metadata(), app)
            initial = dict(boot_id=self.boot, contract_sha256=self.contract_sha, checkpoint_sha256=cp_sha,
                           daemon=daemon, startup_sha256=digest(snapshot['startup_raw']), app=app,
                           list_stdout_sha256=digest(regular(self.tx / 'list.stdout.raw', 65536)))
            create(initial_path, encoded(initial))
        if app == BENCHMARK:
            boundary()
            if not (self.tx / 'remove-intent.json').exists():
                verify_platform(platform_metadata(), BENCHMARK)
            self.once('remove', [CLIENT, '-remove', '0'])
            # A prior successful load may already be present when explicitly resuming
            # the same transaction. Never tear it down or resend either operation.
            if not (self.tx / 'load-intent.json').exists():
                verify_unloaded(platform_metadata())
            boundary()
            self.once('load', [CLIENT, '-load', APP])
            verify_platform(platform_metadata(), APP)
        boundary()
        value = platform_metadata()
        verify_platform(value, APP)
        context = dict(boot_id=self.boot, fdt_sha256=value['fdt_sha256'], firmware_name=value['firmware'])
        context_path = self.tx / 'wide-context.json'
        if context_path.exists():
            require(json.loads(regular(context_path)) == context, 'WIDE_CONTEXT_CHANGED')
        else:
            create(context_path, encoded(context))
        argv = ['/usr/bin/python3', '-B', str(RELEASE / 'bench_identity_stop.py'), '--execute', '--confirmation', 'ID_STOP_ONLY',
                '--manifest', str(RELEASE / 'candidate-manifest.json'), '--manifest-sha256', MANIFEST_SHA,
                '--context', str(context_path), '--output', str(self.tx / 'id-stop.json')]
        self.once('idstop', argv)
        report_raw = regular(self.tx / 'id-stop.json')
        verify_idstop(json.loads(report_raw), self.boot, MANIFEST_SHA)
        expected_stdout = dict(identity_stop_passed=True, motion_tested=False, report=str(self.tx / 'id-stop.json'))
        require(json.loads(regular(self.tx / 'idstop.stdout.raw', 65536)) == expected_stdout, 'ORIGINAL_IDSTOP_REPLY_CHANGED')
        boundary()
        verify_platform(platform_metadata(), APP)
        receipt = dict(status='ORIGINAL_WIDE_READY_IDSTOP_ONLY', boot_id=self.boot, contract_sha256=self.contract_sha,
                       context=context, predecessor_final_sha256=cp_sha, idstop_sha256=digest(report_raw),
                       prestart_history=history_proof,
                       reference_initialized=False, centered=False, follow_started=False,
                       original_reader_and_camera_not_bypassed=True)
        create(self.tx / 'prepared.json', encoded(receipt))
        return receipt

    def camera_check(self):
        snapshot = self.source_snapshot()
        self.original_release()
        self.prepared()
        self.quiet()
        current = unit(CAMERA)
        require(all(current.get(k) == v for k, v in {'Restart': 'no', 'KillMode': 'process', 'SendSIGKILL': 'no', 'TimeoutStopUSec': 'infinity'}.items()), 'NATIVE_NORMAL_STOP_PROTECTION_CHANGED')
        checkpoint = regular(CHECKPOINT, 262144)
        checkpoint_sha = self.checkpoint_gate(snapshot, checkpoint)
        history_proof = self.check_prestart_history(snapshot, checkpoint)
        gate = dict(boot_id=self.boot, contract_sha256=self.contract_sha, checkpoint_sha256=checkpoint_sha,
                    startup_sha256=digest(snapshot['startup_raw']), predecessor=snapshot['active']['predecessor'],
                    history_proof=history_proof,
                    checked_mono_ns=time.monotonic_ns())
        create(self.tx / ('camera-gate-' + str(os.getpid()) + '.json'), encoded(gate))
        gate_path = self.tx / 'current-camera-gate.json'
        if gate_path.exists():
            replace_known(gate_path, regular(gate_path), encoded(gate))
        else:
            create(gate_path, encoded(gate))
        return dict(status='ORIGINAL_CAMERA_MAY_START', boot_id=self.boot, checkpoint_seed_marker_modified=False)

    def camera_samples(self):
        deadline = time.monotonic() + 75
        first = None
        while True:
            state = unit(CAMERA)
            require(state['ActiveState'] != 'failed', 'ORIGINAL_CAMERA_START_FAILED')
            require(state['ActiveState'] != 'deactivating' and not state.get('Job'), 'CAMERA_EXIT_OR_JOB_PENDING_NO_BINDING')
            try:
                require(state['ActiveState'] == 'active' and state['SubState'] == 'running'
                        and state.get('ControlPID', '0') == '0', 'CAMERA_SERVICE_NOT_STABLY_RUNNING')
                sample = get_metadata(8790, '/health')
                pid = int(state['MainPID'])
                require(pid > 0 and sample.get('pid') == pid and sample.get('board_boot_id') == self.boot, 'CAMERA_OWNER_NOT_READY')
                current_owner = process(pid)
                require(sample.get('motion_command_emitted') is False and sample.get('identity', {}).get('ready') is True
                        and not any(sample.get(k) for k in ('camera_error', 'detector_error', 'preview_error'))
                        and not sample.get('identity', {}).get('error'), 'CAMERA_NOT_HEALTHY')
                schedule = sample.get('dpu_schedule') or {}
                require(schedule.get('native_critical') is True and schedule.get('native_abi') == 2
                        and schedule.get('owner_fenced') is False and schedule.get('quiesced') is False,
                        'NATIVE_ORIGINAL_OWNER_NOT_HEALTHY')
                if first and first[0] == current_owner:
                    require(sample['capture_frames'] > first[1]['capture_frames'] and sample['detected_frames'] > first[1]['detected_frames'], 'CAMERA_NOT_ADVANCING')
                    return current_owner, sample
                first = current_owner, sample
            except (OSError, ValueError, KeyError, Hold, http.client.HTTPException):
                first = None
            require(time.monotonic() < deadline, 'CAMERA_NOT_READY_NO_RESTART')
            time.sleep(1)

    def check_camera_live(self, expected_owner):
        def lifecycle():
            state = unit(CAMERA)
            require(state['ActiveState'] == 'active' and state['SubState'] == 'running'
                    and not state.get('Job') and state.get('ControlPID', '0') == '0'
                    and state['MainPID'] == str(expected_owner['pid']), 'CAMERA_LIFECYCLE_CHANGED_NO_BINDING_OR_READY')
            require(process(expected_owner['pid']) == expected_owner, 'CAMERA_OWNER_CHANGED_NO_BINDING_OR_READY')
        lifecycle()
        health = get_metadata(8790, '/health')
        schedule = health.get('dpu_schedule') or {}
        require(health.get('pid') == expected_owner['pid'] and health.get('board_boot_id') == self.boot
                and health.get('motion_command_emitted') is False and health.get('identity', {}).get('ready') is True
                and not any(health.get(key) for key in ('camera_error', 'detector_error', 'preview_error'))
                and not health.get('identity', {}).get('error')
                and schedule.get('native_critical') is True and schedule.get('native_abi') == 2
                and schedule.get('owner_fenced') is False and schedule.get('quiesced') is False,
                'CAMERA_NATIVE_STATE_CHANGED_NO_BINDING_OR_READY')
        lifecycle()
        return health

    def bind_camera(self):
        self.prepared()
        snapshot = self.source_snapshot()
        gui = unit(GUI)
        require(gui['MainPID'] == '0' and gui['ActiveState'] == 'activating' and gui['SubState'] == 'start-pre'
                and int(gui['ControlPID']) == os.getpid(), 'BINDING_REQUIRES_ORIGINAL_GUI_PRESTART')
        current_owner, health = self.camera_samples()
        ops = Path(self.contract['native_ops_root'])
        run = ops / ('native-run-' + self.boot + '-' + str(current_owner['pid'])) / 'config.json'
        run_raw = regular(run)
        run_config = json.loads(run_raw)
        native = run_config['native_execution']
        require(native['source_manifest'] == self.contract['native_manifest']['path']
                and native['source_manifest_sha256'] == self.contract['native_manifest']['sha256'], 'CURRENT_NATIVE_SOURCE_MANIFEST_CHANGED')
        require(native['checkpoint_output'] == str(CHECKPOINT), 'ORIGINAL_CHECKPOINT_OUTPUT_CHANGED')
        # Reading the original bootstrap's public handoff proves a new owner, not a fabricated seed.
        handoff = health['dpu_schedule'].get('protection_handoff') or {}
        gate = json.loads(regular(self.tx / 'current-camera-gate.json'))
        verify_bootstrap_handoff(handoff, gate, self.boot, self.contract_sha)
        accepted_history, live_history_proof = self.accepted_live_history(gate, handoff)
        current_binding = snapshot['selected']
        if (current_binding.get('board_boot_id') == self.boot and current_binding.get('camera_pid') == current_owner['pid']
                and current_binding.get('camera_start_ticks') == current_owner['birth_ticks']):
            require(current_binding.get('camera_config') == str(run)
                    and current_binding['source_sha256'].get(str(run)) == digest(run_raw), 'CURRENT_OWNER_RUN_CONFIG_CHANGED')
            original_verify(snapshot['aura'], current_binding)
            require(snapshot['active']['history_expected'] == accepted_history, 'CURRENT_BINDING_HISTORY_LEDGER_DIFFERS')
            return dict(status='BINDING_ALREADY_CURRENT_NO_WRITE', boot_id=self.boot, camera_owner=current_owner)
        candidate = make_binding(current_binding, self.boot, current_owner,
                                 dict(path=str(run), sha256=digest(run_raw)), snapshot['active']['selected_sources'])
        original_verify(snapshot['aura'], candidate)
        directory = self.tx / ('binding-' + str(current_owner['pid']) + '-' + current_owner['birth_ticks'])
        require(not directory.exists(), 'BINDING_ATTEMPT_EXISTS_RECONCILE_NO_RETRY')
        directory.mkdir(mode=0o700)
        selected_path = directory / 'face_gallery_readback.local.json'
        candidate_raw = encoded(candidate)
        selected_pin = dict(path=str(selected_path), sha256=digest(candidate_raw))
        new_ui, new_startup = config_patch(snapshot['startup'], snapshot['ui'], selected_pin)
        create(directory / 'ui.before.json', snapshot['ui_raw'])
        create(directory / 'startup.before.json', snapshot['startup_raw'])
        create(directory / 'ui.after.json', new_ui)
        create(directory / 'startup.after.json', new_startup)
        create(selected_path, candidate_raw)
        prior_active_raw = snapshot['active_source_raw']
        prior_active_present = snapshot['active_source_present']
        active = dict(contract_sha256=self.contract_sha, startup_sha256=digest(new_startup), ui_sha256=digest(new_ui),
                      selected_pin=selected_pin, selected_sources=candidate['source_sha256'],
                      predecessor=dict(boot_id=self.boot, camera_owner=current_owner), transaction=str(directory),
                      history_expected=accepted_history, history_provenance=live_history_proof)
        active_after_raw = encoded(active)
        create(directory / 'active-source.after.json', active_after_raw)
        intent = dict(boot_id=self.boot, contract_sha256=self.contract_sha, camera_owner=current_owner,
                      startup_before_sha256=digest(snapshot['startup_raw']), startup_after_sha256=digest(new_startup),
                      ui_before_sha256=digest(snapshot['ui_raw']), ui_after_sha256=digest(new_ui),
                      active_before_sha256=digest(prior_active_raw),
                      active_after_sha256=digest(active_after_raw),
                      selected_pin=selected_pin, changed_components=['config/board_avatar_gtk.json'])
        create(directory / 'intent.json', encoded(intent))
        require(process(current_owner['pid']) == current_owner and regular(run) == run_raw, 'CAMERA_OWNER_CHANGED_BEFORE_CAS')
        now = self.source_snapshot()  # FULL recapture immediately before the two known-byte changes.
        require(now['startup_raw'] == snapshot['startup_raw'] and now['ui_raw'] == snapshot['ui_raw']
                and now['active_source_present'] == prior_active_present
                and now['active_source_raw'] == prior_active_raw, 'SOURCE_CHANGED_BEFORE_BINDING_CAS')
        original_verify(snapshot['aura'], candidate)
        create(directory / 'active-source.before.json', prior_active_raw)
        self.check_camera_live(current_owner)
        replace_known(snapshot['ui_path'], snapshot['ui_raw'], new_ui)
        replace_known(self.contract['startup_path'], snapshot['startup_raw'], new_startup)
        require(process(current_owner['pid']) == current_owner, 'CAMERA_OWNER_CHANGED_AFTER_CAS')
        self.check_camera_live(current_owner)
        original_verify(snapshot['aura'], candidate)
        active_path = STATE_ROOT / 'active-source.json'
        if prior_active_present:
            replace_known(active_path, prior_active_raw, active_after_raw)
        else:
            require(not os.path.lexists(active_path), 'ACTIVE_LEDGER_APPEARED_DURING_BINDING')
            create(active_path, active_after_raw)
        final_snapshot = self.source_snapshot()
        require(final_snapshot['active_source_present'] and final_snapshot['active_source_raw'] == active_after_raw,
                'ACTIVE_LEDGER_CHANGED_AFTER_BINDING_CAS')
        create(directory / 'committed.json', active_after_raw)
        return dict(status='ORIGINAL_VERIFIER_CURRENT_BINDING_COMMITTED', boot_id=self.boot,
                    camera_owner=current_owner, selected_source_count=len(candidate['source_sha256']),
                    changed_components=['config/board_avatar_gtk.json'])

    def verify_gui(self):
        prepared = self.prepared()
        snapshot = self.source_snapshot()
        current_owner, camera_health = self.camera_samples()
        gate = json.loads(regular(self.tx / 'current-camera-gate.json'))
        handoff = camera_health['dpu_schedule'].get('protection_handoff') or {}
        verify_bootstrap_handoff(handoff, gate, self.boot, self.contract_sha)
        accepted_history, _ = self.accepted_live_history(gate, handoff)
        require(snapshot['active']['history_expected'] == accepted_history, 'READY_COMPLETE_HISTORY_LEDGER_DIFFERS')
        original_verify(snapshot['aura'], snapshot['selected'])
        state = unit(GUI)
        require(state['ActiveState'] == 'active' and state['SubState'] == 'running' and not state['Job'], 'ORIGINAL_GUI_NOT_RUNNING')
        supervisor = process(state['MainPID'])
        launch = json.loads(regular(Path(snapshot['startup']['runtime']) / 'launch.json'))
        require(launch['boot_id'] == self.boot and launch['supervisor_pid'] == supervisor['pid'] and launch['service'] == GUI, 'GUI_LAUNCH_OWNER_CHANGED')
        gtk = process(launch['pid'])
        preference = json.loads(regular(self.contract['listening_preference_path']))
        require(set(preference) == {'version', 'enabled'} and preference['version'] == 1 and type(preference['enabled']) is bool, 'ORIGINAL_LISTENING_PREFERENCE_SHAPE')
        deadline = time.monotonic() + 90
        first = None
        while True:
            try:
                last = gui_projection(get_metadata(8783, '/api/state'))
                if first is not None:
                    verify_ready(first, last, preference['enabled'])
                    break
                first = last
            except (OSError, ValueError, Hold, http.client.HTTPException):
                first = None
            require(time.monotonic() < deadline, 'GUI_NOT_READY_NO_RESTART')
            time.sleep(1)
        require_no_owners(owner_scan(motion_only=True))
        require(process(supervisor['pid']) == supervisor and process(gtk['pid']) == gtk
                and process(current_owner['pid']) == current_owner, 'READY_OWNER_CHANGED')
        require(self.source_snapshot()['startup_raw'] == snapshot['startup_raw'], 'READY_SOURCE_CHANGED')
        original_verify(snapshot['aura'], snapshot['selected'])
        self.prepared()
        final_gui = unit(GUI)
        require(final_gui['MainPID'] == str(supervisor['pid']) and final_gui['ActiveState'] == 'active'
                and final_gui['SubState'] == 'running' and not final_gui.get('Job')
                and final_gui.get('ControlPID', '0') == '0', 'GUI_LIFECYCLE_CHANGED_BEFORE_READY')
        self.check_camera_live(current_owner)
        receipt = dict(schema='aura-boot-recovery-ready-1', status='GUI_SOFTWARE_READY_AXIS_OUTPUT_DISABLED',
                       boot_id=self.boot, contract_sha256=self.contract_sha,
                       startup_sha256=digest(snapshot['startup_raw']), camera_owner=current_owner,
                       gui_supervisor=supervisor, gtk_owner=gtk, first=first, last=last,
                       idstop_sha256=prepared['idstop_sha256'], axis_output_proof='Original this-boot ID_STOP_ONLY + same platform + no register owner + original UI remains mechanically locked',
                       reference_initialized=False, centered=False, follow_started=False,
                       physical_panel_observed=False, physical_direction_accepted=False)
        ready_path = self.tx / 'ready.json'
        if not ready_path.exists():
            create(ready_path, encoded(receipt))
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', default=str(PACKAGE_ROOT / 'contract.json'))
    parser.add_argument('--job', choices=['list', 'remove', 'load', 'idstop'])
    parser.add_argument('action', choices=['prepare', 'camera-check', 'bind-camera', 'verify-gui', 'observe-job'])
    args = parser.parse_args()
    recovery = None
    try:
        recovery = Recovery(args.contract)
        if args.action == 'observe-job':
            require(args.job is not None, 'EXISTING_JOB_NAME_REQUIRED')
            value = recovery.observe_job(args.job)
        else:
            value = getattr(recovery, args.action.replace('-', '_'))()
        print(json.dumps(value, sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        # Never echo raw API documents, exception text from an original runtime, or identity data.
        reason = str(error) if isinstance(error, Hold) else type(error).__name__
        result = dict(status='HOLD_NO_RESTART_NO_OWNER_REPLACEMENT', action=args.action,
                      reason=reason, board_mutation_rollback_attempted=False)
        if recovery is not None:
            path = recovery.tx / ('hold-' + args.action + '.json')
            if not path.exists():
                create(path, encoded(result))
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
