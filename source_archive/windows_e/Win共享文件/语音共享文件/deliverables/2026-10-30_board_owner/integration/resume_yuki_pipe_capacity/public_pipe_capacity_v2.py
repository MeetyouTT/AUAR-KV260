"""Explicit root public-WAV capacity probe beside the detached synthetic GUI.

Default inspect performs read-only metadata/GET preflight, never imports models.
Run invokes the byte-exact reviewed public probe. Its only replaced attribute is
safety_snapshot: an inactive original UI unit is allowed ONLY with the exact
detached candidate owner, effective no-force guards, camera and assembly proof.
No start/stop, signal, device, DB, identity command or remote model request here.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import time

PROBE_SHA = 'b53803cab734bb69cd8a62698c92d630ed98d9d0b2cee7ecc9232bcb4a4323a3'
CONTROL_SHA = 'c44451097a1ef9ac5cd6f1b0ccb72e316c054651b619a14c3b0b4ada7628337a'
POLICY_SHA = '50f0c88ac736a153512afe022455b6e9925602620c9b332e4fb83e84a48dca18'
INSPECTION = '58d39ed8757f93c1780bf59408bf0fe15d42ffae4da5a2dbf97218925bedf7cf'
ROUND2_READY = True
RUNTIME_STATE = 'private/ui_settings.json'
BOOT = '8100a7fd-0c6a-46c4-82b8-f874988a1521'
CAMERA = {'pid': 260102, 'birth': '784437'}
BASE = '/home/root/aura-board-owner-candidate-20261030'
TARGET = BASE + '/yuki-gui-capacity-20261030-r3'
CONTROL_ROOT = BASE + '/ui-capacity-control-20261030-r2'
PAIR = 'xuefei-yuki-board-v1-candidate'
PROMPT = '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'
MISSING = object()


class Refused(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise Refused(code)


def error_code(exc):
    value = str(exc)
    return value if isinstance(exc, ValueError) and re.fullmatch(r'[a-z0-9_]{1,120}', value) else 'preflight_unavailable'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    # Byte contract of frozen assemble_v2. Inspection is SHA over the pretty
    # manifest without its inspection_sha256 field, including the final LF.
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refused('nonfinite_json')))


def read(path, maximum=2097152):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
         'canonical_nonlinked_file_required')
    info = path.stat()
    need(stat.S_ISREG(info.st_mode) and info.st_size <= maximum, 'bounded_regular_file_required')
    raw = path.read_bytes()
    need(len(raw) <= maximum, 'file_grew_beyond_bound')
    return raw


def load_pinned(path, expected, name):
    raw = read(path)
    need(digest(raw) == expected, name + '_source_changed')
    return strict_json(raw)


def load_module(path, expected, name):
    raw = read(path)
    need(digest(raw) == expected, name + '_source_changed')
    # Compile precisely the verified bytes: do not re-open an import path after
    # checking it, and do not create __pycache__ beside the frozen source.
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def get(value, path):
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            return MISSING
        value = value[key]
    return value


def protected_state(value):
    need(isinstance(value, dict), 'ui_state_not_object')
    equal = {'phase': 'IDLE', 'manual_pan.state': 'FAULT', 'local_recording.state': 'IDLE',
             'avatar_display.kind': 'native_yuki_egl', 'character_pair.state': 'READY',
             'character_pair.profile_version': PAIR, 'character_pair.prompt_sha256': PROMPT}
    false = ('playing', 'handsfree_dialogue.enabled', 'handsfree_dialogue.microphone_open',
             'manual_pan.automatic_following', 'voice_barge_in.listening',
             'voice_barge_in.continuation_listening', 'automatic_conversation.enabled',
             'local_transcription.service.pending')
    true = ('avatar_display.visible', 'avatar_display.frame_scheduling_active',
            'local_transcription.service.enabled', 'local_transcription.service.board_owned')
    need(all(get(value, key) == expected for key, expected in equal.items()),
         'candidate_idle_native_pair_or_fault_changed')
    need(all(get(value, key) is False for key in false), 'explicit_no_capture_no_play_no_follow_required')
    need(all(get(value, key) is True for key in true), 'visible_native_board_business_required')
    need(get(value, 'manual_pan.pulse_us') is None and get(value, 'manual_pan.target_us') is None,
         'mechanical_position_must_remain_explicit_null')
    need(type(get(value, 'avatar_display.target_fps')) in (int, float)
         and get(value, 'avatar_display.target_fps') == 16, 'native_target_must_remain_16fps')
    need(type(get(value, 'local_recording.sample_count')) is int
         and get(value, 'local_recording.sample_count') == 0, 'no_manual_recording_samples_required')
    # Only constant proof values leave this function. Never retain raw UI JSON,
    # conversation, profile, recognized names, identity IDs or image fields.
    return dict(phase='IDLE', playing=False, listening=False, microphone_open=False,
                following=False, pan_state='FAULT', pulse_us=None, target_us=None,
                native_visible=True, native_target_fps=16, pair=PAIR, board_business=True)


def loopback_state():
    """One bounded GET, no redirects/proxies/DNS; absolute read deadline."""
    deadline = time.monotonic() + 2.
    with socket.create_connection(('127.0.0.1', 8783), timeout=1.) as client:
        need(client.getpeername()[0] == '127.0.0.1', 'nonloopback_state_peer')
        client.sendall(b'GET /api/state HTTP/1.0\r\nHost: 127.0.0.1:8783\r\nConnection: close\r\n\r\n')
        chunks, size = [], 0
        while True:
            remaining = deadline - time.monotonic()
            need(remaining > 0, 'ui_state_deadline')
            client.settimeout(min(remaining, .5))
            try:
                chunk = client.recv(min(65536, 2097153 - size))
            except socket.timeout:
                continue
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            need(size <= 2097152, 'ui_state_size_limit')
    raw = b''.join(chunks)
    head, delimiter, body = raw.partition(b'\r\n\r\n')
    need(delimiter and len(head) <= 16384, 'ui_http_header_invalid')
    lines = head.split(b'\r\n')
    need(lines[0].split()[:2] in ([b'HTTP/1.0', b'200'], [b'HTTP/1.1', b'200']), 'ui_http_status')
    headers = {}
    for line in lines[1:]:
        key, sep, value = line.partition(b':')
        key = key.strip().lower()
        need(sep and key not in headers, 'ui_http_ambiguous_header')
        headers[key] = value.strip()
    need(b'transfer-encoding' not in headers and b'location' not in headers, 'ui_http_redirect_or_encoding')
    if b'content-length' in headers:
        need(headers[b'content-length'].isdigit() and int(headers[b'content-length']) == len(body),
             'ui_http_body_size')
    return strict_json(body)


def lock_proof(owner, receipt, control):
    lock = Path(control.LOCK)
    info = lock.stat()
    need(not lock.is_symlink() and stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1,
         'unsafe_gui_publisher_lock')
    fd = receipt.get('lock_inherited_fd')
    need(type(fd) is int and fd >= 3, 'inherited_gui_lock_fd_missing')
    inherited = Path('/proc') / str(owner['pid']) / 'fd' / str(fd)
    need(os.readlink(str(inherited)) == control.LOCK, 'candidate_lock_descriptor_changed')
    held = inherited.stat()
    need((held.st_dev, held.st_ino) == (info.st_dev, info.st_ino), 'candidate_lock_inode_changed')
    # Inherited flock's listed PID may be the exited launcher. Match the exact
    # locked inode plus inherited descriptor; never try acquiring/releasing it.
    expected = (os.major(info.st_dev), os.minor(info.st_dev), info.st_ino)
    matches = []
    for line in Path('/proc/locks').read_text().splitlines():
        fields = line.split()
        if len(fields) == 8 and fields[1:4] == ['FLOCK', 'ADVISORY', 'WRITE']:
            parts = fields[5].split(':')
            if len(parts) == 3:
                identity = (int(parts[0], 16), int(parts[1], 16), int(parts[2]))
                if identity == expected and fields[6:] == ['0', 'EOF']:
                    matches.append(fields)
    need(len(matches) == 1, 'candidate_exact_publisher_lock_not_held')
    return True


def private_state_metadata(info, *, directory=False):
    mode = stat.S_IMODE(info.st_mode)
    kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    allowed = 0o700 if directory else 0o600
    need(kind and info.st_uid == 0 and mode & ~allowed == 0
         and mode & 0o400 and (not directory or mode & 0o100),
         'runtime_ui_settings_must_remain_root_private')
    if not directory:
        need(info.st_nlink == 1 and 0 <= info.st_size <= 65536,
             'runtime_ui_settings_regular_single_link_size_required')


def runtime_state_file(relative=RUNTIME_STATE):
    """Validate the sole mutable JSON state; return no body or current digest.

    The original manifest row remains untouched. Canonical private directory
    and no-follow openat descriptors prevent a state allowance from redirecting
    reads outside the target or admitting a device/FIFO/hardlink/source file.
    """
    need(relative == RUNTIME_STATE, 'only_exact_ui_settings_state_is_mutable')
    private = Path(TARGET) / 'private'
    path = private / 'ui_settings.json'
    need(str(path) == str(Path(TARGET) / RUNTIME_STATE)
         and private.resolve(strict=True) == private and path.resolve(strict=True) == path
         and not private.is_symlink() and not path.is_symlink(),
         'runtime_ui_settings_canonical_private_path_required')
    directory_fd = state_fd = None
    try:
        directory_fd = os.open(str(private), os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY)
        directory_info = os.fstat(directory_fd)
        private_state_metadata(directory_info, directory=True)
        parent_info = private.stat()
        need((parent_info.st_dev, parent_info.st_ino) == (directory_info.st_dev, directory_info.st_ino),
             'runtime_private_directory_changed')
        state_fd = os.open('ui_settings.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                           dir_fd=directory_fd)
        info = os.fstat(state_fd)
        private_state_metadata(info)
        chunks, size = [], 0
        while True:
            raw = os.read(state_fd, min(65536, 65537 - size))
            if not raw:
                break
            chunks.append(raw)
            size += len(raw)
            need(size <= 65536, 'runtime_ui_settings_exceeds_size_bound')
        raw = b''.join(chunks)
        need(isinstance(strict_json(raw), dict), 'runtime_ui_settings_json_object_required')
        after = os.fstat(state_fd)
        private_state_metadata(after)
        current = path.stat()
        private_state_metadata(current)
        need((info.st_dev, info.st_ino) == (after.st_dev, after.st_ino)
             == (current.st_dev, current.st_ino)
             and len(raw) == info.st_size == after.st_size == current.st_size,
             'runtime_ui_settings_replaced_during_read')
        need(private.resolve(strict=True) == private and path.resolve(strict=True) == path
             and not private.is_symlink() and not path.is_symlink(),
             'runtime_ui_settings_redirected_after_read')
        parent_after = private.stat()
        private_state_metadata(parent_after, directory=True)
        need((parent_after.st_dev, parent_after.st_ino) == (directory_info.st_dev, directory_info.st_ino),
             'runtime_private_directory_changed_after_read')
        return True
    finally:
        if state_fd is not None:
            os.close(state_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def assembly_proof(control):
    manifest = strict_json(read(TARGET + '/assembly_manifest.json'))
    claimed = manifest.pop('inspection_sha256', None)
    need(claimed == INSPECTION and digest(encoded(manifest)) == INSPECTION,
         'reviewed_assembly_manifest_changed')
    need(manifest.get('target') == TARGET and manifest.get('ready') is True
         and manifest.get('data_origin') == 'synthetic', 'explicit_synthetic_assembly_required')
    files = manifest.get('candidate_files')
    need(isinstance(files, dict) and len(files) == 356 and RUNTIME_STATE in files,
         'complete_staged_file_map_with_exact_runtime_state_required')
    immutable = 0
    for relative, row in files.items():
        parts = PurePosixPath(relative)
        need(not parts.is_absolute() and '..' not in parts.parts and '\\' not in relative,
             'candidate_component_path_escape')
        if relative == RUNTIME_STATE:
            runtime_state_file()
        else:
            raw = read(TARGET + '/' + relative, maximum=33554432)
            need(len(raw) == row['bytes'] and digest(raw) == row['sha256'], 'candidate_component_changed')
            immutable += 1
    need(immutable == 355, 'exactly_355_immutable_files_required')
    launch = strict_json(read(TARGET + '/launch.json'))
    need(launch == manifest['launch'], 'candidate_launch_changed')
    need(launch['single_publisher_lock'] == control.LOCK and launch['original_service'] == control.UNIT,
         'candidate_publisher_changed')
    argv = launch['command']
    need(argv[:3] == ['/usr/bin/python3', '-B', TARGET + '/runtime/aura/tools/board_avatar_pan.py'],
         'original_pan_wrapper_entry_required')
    config = strict_json(read(TARGET + '/runtime/aura/config/board_avatar_gtk.json'))
    business = config.get('board_business', {})
    need(business.get('enabled') is True and business.get('data_origin') == 'synthetic'
         and business.get('model_port') == 8797
         and business.get('asr_threads') == 2 and business.get('frontend_threads') == 1,
         'original_candidate_business_models_required')
    return argv


def round2_owner_argv(argv, control):
    """The reviewed launcher moves only the evidence directory, never sources."""
    need(control.TARGET == TARGET and control.CONTROL == CONTROL_ROOT,
         'round2_exact_target_and_control_required')
    need(isinstance(argv, list) and argv.count('--evidence-root') == 1,
         'single_descriptor_evidence_argument_required')
    offset = argv.index('--evidence-root') + 1
    need(offset < len(argv) and argv[offset] == TARGET + '/evidence/gui-capacity-1',
         'descriptor_original_evidence_root_changed')
    expected = list(argv)
    expected[offset] = CONTROL_ROOT + '/evidence/gui-capacity-round2'
    return expected


class Verifier:
    def __init__(self, control, policy, expected, state_reader=loopback_state, lock_reader=lock_proof):
        self.control, self.policy, self.expected = control, policy, expected
        self.state_reader, self.lock_reader = state_reader, lock_reader
        self.calls = 0

    def snapshot(self, *, include_service_pids=True):
        # include_service_pids=False in the original inner probe does NOT bypass
        # any detached-owner, inactive-unit, camera or protected-state checks.
        control = self.control
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT, 'board_boot_changed')
        journal, unit = control.inactive(self.policy)  # Pinned read-only existing preflight, no lock or action.
        need(unit.get('MainPID') == '0' and unit.get('ActiveState') == 'inactive'
             and unit.get('Restart') == 'no' and unit.get('SendSIGKILL') == 'no'
             and unit.get('TimeoutStopUSec') == 'infinity' and not unit.get('Job'),
             'inactive_original_unit_without_jobs_and_no_force_guards_required')
        argv = round2_owner_argv(assembly_proof(control), control)
        owner = control.process(self.expected['pid'])
        need(control.same_owner(owner, self.expected) and owner['argv'] == argv, 'candidate_owner_changed')
        receipt = control.candidate_owner()
        need(isinstance(receipt, dict) and receipt.get('target') == TARGET
             and receipt.get('source_inspection') == INSPECTION
             and control.same_owner(receipt.get('owner'), self.expected)
             and receipt.get('argv_sha256') == self.expected['cmdline_sha256'],
             'candidate_launch_receipt_changed')
        camera = control.process(CAMERA['pid'])
        need(camera and camera.get('birth') == CAMERA['birth'], 'camera_owner_changed')
        # The exact camera service MainPID is independently checked, even though
        # the original unit's public preflight only checks its current proc birth.
        camera_pid = control.command(['/bin/systemctl', 'show', 'aura-camera-ui.service',
                                      '--property=MainPID', '--value'], timeout=2).strip()
        need(camera_pid == str(CAMERA['pid']), 'camera_service_owner_changed')
        self.lock_reader(owner, receipt, control)
        result = protected_state(self.state_reader())
        need(control.same_owner(control.process(self.expected['pid']), owner), 'candidate_owner_changed_during_check')
        camera_again = control.process(CAMERA['pid'])
        need(camera_again and camera_again.get('birth') == CAMERA['birth'], 'camera_changed_during_check')
        result.update(boot_id=BOOT, ui_pid=owner['pid'], ui_birth=owner['birth'],
                      ui_cmdline_sha256=owner['cmdline_sha256'], camera_pid=CAMERA['pid'],
                      camera_birth=CAMERA['birth'], original_unit_main_pid=0,
                      original_unit_guarded=True, assembly_inspection_sha256=INSPECTION,
                      inherited_publisher_lock=True)
        result.update(assembly_immutable_file_count=355, runtime_ui_settings_validated=True,
                      runtime_ui_settings_initial_manifest_pin_preserved=True)
        self.calls += 1
        return result


def probe_argv():
    return ['--code-root', TARGET + '/runtime/aura', '--resources-root', BASE,
            '--mode', 'pipeline', '--runs', '1', '--num-threads', '1',
            '--process-nice', '0', '--queue-frames', '8']


def execute(args, verifier, loader=load_module):
    need(digest(read(args.probe_file)) == PROBE_SHA, 'original_public_probe_changed')
    before = verifier.snapshot(include_service_pids=False)
    result = dict(status='INSPECTED_ONLY_NO_MODELS', action=args.action, before=before,
                  probe_sha256=PROBE_SHA, probe_argv=probe_argv(), actual_model_probe_executed=False,
                  actual_public_probe_invoked=False,
                  microphone_opened=False, playback_started=False, service_or_gui_action=False,
                  source_or_model_modified=False,
                  mutable_state_allowance=dict(relative_path=RUNTIME_STATE, immutable_files=355,
                      current_content_or_digest_retained=False, original_manifest_modified=False),
                  residency={'gui_preloads_frontend_and_paraformer': True,
                             'separate_probe_constructs_additional_sessions_on_run': True,
                             'shared_model_instances': False,
                             'qualification': 'Duplicate resident model sessions under the complete synthetic native GUI; not the in-process single-model microphone path'},
                  acceptance_scope='Public paced WAV capacity only; no physical microphone, playback, person A/B or final replacement acceptance')
    if args.action == 'inspect':
        return result, 0
    probe = loader(args.probe_file, PROBE_SHA, '_frozen_public_pipe_probe')
    original_snapshot = probe.safety_snapshot
    # Sole monkeypatch: model, frontend, endpoint, priorities, queue and public
    # WAV remain precisely those of the frozen b53803ca source and pinned GUI.
    probe.safety_snapshot = verifier.snapshot
    stream = io.StringIO()
    code, failure = 2, None
    try:
        with contextlib.redirect_stdout(stream):
            code = probe.main(probe_argv())
    except Exception as exc:
        failure = type(exc).__name__
    finally:
        probe.safety_snapshot = original_snapshot
        try:
            need(digest(read(args.probe_file)) == PROBE_SHA, 'original_public_probe_changed_after_run')
            after = verifier.snapshot(include_service_pids=False)
            need(before == after, 'candidate_or_safety_changed_during_capacity_probe')
            result['after'] = after
        except Exception as exc:
            failure = 'post_probe_safety_' + type(exc).__name__
            result['post_probe_error_code'] = error_code(exc)
    result['actual_public_probe_invoked'] = True
    result['actual_model_probe_executed'] = None  # Failure may have happened before or after model construction.
    result['safety_snapshots_verified'] = verifier.calls
    if failure is None:
        try:
            result['probe_result'] = strict_json(stream.getvalue())
            if result['probe_result'].get('actual_arm') is True:
                result['actual_model_probe_executed'] = True
        except (ValueError, TypeError):
            failure = 'probe_result_not_single_json'
    else:
        # Never return arbitrary raw stdout or exception strings.
        result['probe_stdout_sha256'] = digest(stream.getvalue().encode())
    resources = result.get('probe_result', {}).get('resources', {})
    passed = (failure is None and code == 0
              and result.get('probe_result', {}).get('status') == 'PASS_PUBLIC_PCM_PUMP_ENDPOINT_AND_ASR'
              and result['probe_result'].get('input_queue', {}).get('error') == ''
              and result['probe_result']['input_queue'].get('reader_alive') is False
              and result['probe_result']['input_queue'].get('capacity_frames') == 8
              and resources.get('numpy') == '1.21.2'
              and resources.get('onnxruntime') == '1.17.3' and resources.get('sherpa_onnx') == '1.13.8')
    result.update(status='PASS_DETACHED_GUI_PUBLIC_PIPE_ONLY' if passed else 'FAILED_PUBLIC_PIPE_OR_POSTCHECK',
                  probe_returncode=code, failure_type=failure)
    return result, 0 if passed else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'run'), nargs='?', default='inspect')
    parser.add_argument('--probe-file', type=Path, required=True)
    parser.add_argument('--control-file', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--candidate-pid', type=int, required=True)
    parser.add_argument('--candidate-birth', required=True)
    parser.add_argument('--candidate-cmdline-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        need(ROUND2_READY, 'round2_reviewed_control_and_policy_not_frozen')
        need(os.name == 'posix' and os.geteuid() == 0, 'actual_root_posix_only')
        need(os.getpriority(os.PRIO_PROCESS, 0) == 0, 'original_nice_zero_required')
        need(args.candidate_pid > 1 and re.fullmatch(r'[1-9][0-9]*', args.candidate_birth)
             and re.fullmatch(r'[a-f0-9]{64}', args.candidate_cmdline_sha256), 'explicit_candidate_identity_required')
        control = load_module(args.control_file, CONTROL_SHA, '_frozen_ui_readonly_preflight')
        # Required v2 initializer seals exactly the 71 reviewed original alias
        # paths/canonical targets; never use an arbitrary follow-symlink read.
        load_pinned(args.policy, POLICY_SHA, 'existing_ui_trial_policy')
        policy = control.read_policy(str(args.policy), POLICY_SHA)
        need(control.TARGET == TARGET and policy['boot_id'] == BOOT, 'reviewed_ui_target_changed')
        expected = dict(pid=args.candidate_pid, birth=args.candidate_birth,
                        cmdline_sha256=args.candidate_cmdline_sha256)
        result, code = execute(args, Verifier(control, policy, expected))
    except Exception as exc:
        result, code = dict(status='REFUSED_NO_ACTION', error_type=type(exc).__name__,
                            error_code=error_code(exc),
                            service_or_gui_action=False, microphone_opened=False, playback_started=False), 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
