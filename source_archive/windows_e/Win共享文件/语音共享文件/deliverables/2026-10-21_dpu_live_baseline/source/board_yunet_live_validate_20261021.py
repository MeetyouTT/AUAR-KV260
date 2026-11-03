import sys
sys.argv=['board_deploy_yunet.py', '/home/root/aura-dpu-vision-20261021/staging/81fdb11903abb71e/bundle.tar.gz', '--patch-sha256', '81fdb11903abb71e039304369ce418129a9f790500f1cc026da560f63af6fa74', '--model-root', '/home/root/aura-dpu-vision-20261021/staging/3f10273827d88501/kit-974f2fb1a5641f10', '--model-sha256', '54d348bfeee01756a98bda4103c056a2d5e469a26ea887822da6edc28bdbbbee', '--manifest-sha256', '443d3de67837fa2b16d9c1caba55fb853416f784ced94054969e4cc43c02cf22', '--boot', '215c4292-ce84-4828-9827-83c32ba66564']
"""Integrate only YuNet into a copy of the actual camera runtime; timed rollback."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import urllib.request

SOURCE = Path(sys._getframe().f_code.co_filename).resolve()
SOURCE_SHA = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
JOBROOT = Path('/home/root/aura-dpu-vision-20261021/live-validation') / SOURCE_SHA[:16]
OBSERVE_SECONDS = 1800


def progress(report):
    value = {k: v for k, v in report.items() if k != 'samples'}
    value['sample_count'] = len(report.get('samples', []))
    temp = JOBROOT / 'progress.tmp'
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(JOBROOT / 'progress.json')


def cpu():
    v = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    return sum(v), v[3] + v[4]


def kernel_check(fd):
    import errno
    count = lost = 0
    for _ in range(2048):
        try:
            line = os.read(fd, 8192)
        except OSError as exc:
            if exc.errno == errno.EAGAIN:
                return {'warnings': count, 'overruns': lost, 'truncated': False}
            if exc.errno == errno.EPIPE:
                lost += 1
                continue
            raise
        count += int(b"HC couldn't access mem fast enough for slot 4 ep 3" in line)
    return {'warnings': count, 'overruns': lost, 'truncated': True}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def service(*args):
    p = subprocess.run(['systemctl', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    if p.returncode:
        raise RuntimeError('systemctl failed: ' + p.stdout.decode(errors='replace')[-1000:])
    return p.stdout.decode()


def get(port, route):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:%d%s' % (port, route), timeout=2) as response:
        return json.load(response)


def camera():
    s = get(8790, '/health')
    result = {k: s.get(k) for k in ('pid', 'service_epoch', 'capture_frames', 'detected_frames',
        'capture_hz', 'detection_hz', 'observation_age_ms', 'camera_error', 'detector_error', 'dpu_schedule')}
    result['identity_backend'] = s.get('identity', {}).get('backend')
    result['face_targets'] = s.get('identity', {}).get('face_targets')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('patch', type=Path)
    parser.add_argument('--patch-sha256', required=True)
    parser.add_argument('--model-root', type=Path, required=True)
    parser.add_argument('--model-sha256', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--boot', required=True)
    args = parser.parse_args()
    assert os.uname().machine == 'aarch64'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == args.boot
    assert str(args.patch).startswith('/home/root/aura-dpu-vision-20261021/staging/')
    assert digest(args.patch) == args.patch_sha256
    assert digest(args.model_root / 'yunet_public_int8.xmodel') == args.model_sha256
    assert digest(args.model_root / 'manifest.json') == args.manifest_sha256
    assert json.loads((args.model_root / 'board-result.json').read_text())['passed']
    before = camera()
    assert not before['camera_error'] and not before['detector_error']
    assert before['dpu_schedule'] is None, 'Refuse to replace another deployed scheduler'
    proc = Path('/proc') / str(before['pid'])
    command = proc.joinpath('cmdline').read_bytes().split(b'\0')
    script = next(Path(x.decode()) for x in command if x.endswith(b'/board_camera_motion.py'))
    original = script.parent.parent
    config_path = Path(command[command.index(b'--config') + 1].decode())
    config = json.loads(config_path.read_text())
    identity_path = Path(config['identity']['config'])
    identity = json.loads(identity_path.read_text())
    assert not identity.get('face_backend')
    assert identity.get('feature_backend', {}).get('kind') == 'windows_sface'
    with tarfile.open(args.patch, 'r:gz') as archive:
        manifest = json.load(archive.extractfile('patch-manifest.json'))
        assert set(archive.getnames()) == set(manifest['files']) | {'patch-manifest.json'}
        for rel, sha in manifest['baseline'].items():
            assert digest(original / rel) == sha, 'Runtime baseline changed: ' + rel
        root = Path('/home/root/aura-dpu-vision-20261021/runtime') / (args.patch_sha256[:16] + '-live-' + str(os.getpid()))
        root.mkdir(parents=True, exist_ok=False)
        candidate = root / 'aura'
        shutil.copytree(original, candidate, ignore=shutil.ignore_patterns('__pycache__'))
        for rel, meta in manifest['files'].items():
            path = Path(rel)
            assert not path.is_absolute() and '..' not in path.parts
            member = archive.getmember(rel)
            assert member.isfile()
            data = archive.extractfile(member).read()
            assert len(data) == meta['bytes'] and hashlib.sha256(data).hexdigest() == meta['sha256']
            ast.parse(data.decode(), filename=rel)
            target = candidate / path
            assert not target.is_symlink()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    identity['face_backend'] = {'kind': 'dpu_yunet', 'model': str(args.model_root / 'yunet_public_int8.xmodel'),
        'manifest': str(args.model_root / 'manifest.json'), 'model_sha256': args.model_sha256,
        'manifest_sha256': args.manifest_sha256}
    new_identity = root / 'board_identity.json'
    new_identity.write_text(json.dumps(identity, indent=2) + '\n')
    config['identity']['config'] = str(new_identity)
    new_config = root / 'board_camera_ui.json'
    new_config.write_text(json.dumps(config, indent=2) + '\n')
    unit = Path('/etc/systemd/system/aura-camera-ui.service')
    old_unit = unit.read_text()
    assert str(original) in old_unit and str(config_path) in old_unit
    new_unit = old_unit.replace(str(original), str(candidate)).replace(str(config_path), str(new_config))
    (root / 'camera.service.original').write_text(old_unit)
    (root / 'camera.service.candidate').write_text(new_unit)
    protected = {str(p): digest(p) for p in (config_path, identity_path,
        Path('/etc/systemd/system/aura-avatar-ui.service'))}
    for p in Path('/etc/systemd/system/aura-avatar-ui.service.d').glob('*.conf'):
        protected[str(p)] = digest(p)
    protected['/home/root/.local/share/aura/handsfree_dialogue.json'] = digest('/home/root/.local/share/aura/handsfree_dialogue.json')
    ui_pid = service('show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value').strip()
    x_pid = service('show', 'xserver-nodm.service', '-p', 'MainPID', '--value').strip()
    rollback = '''
import hashlib,os,shutil,subprocess
from pathlib import Path
root=Path(ROOT)
unit=Path('/etc/systemd/system/aura-camera-ui.service')
old=(root/'camera.service.original').read_bytes();new=(root/'camera.service.candidate').read_bytes()
current=unit.read_bytes()
assert current in (old,new),'Refuse to replace an unrelated later unit'
subprocess.run(['systemctl','stop','aura-camera-ui.service'],check=False,timeout=25)
temp=unit.with_name(unit.name+'.dpu-rollback-'+str(os.getpid()))
temp.write_bytes(old);os.replace(str(temp),str(unit))
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=10)
subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=10)
'''.replace('Path(ROOT)', 'Path(' + repr(str(root)) + ')')
    (root / 'rollback.py').write_text(rollback)
    ui = get(8783, '/api/state')
    assert ui['phase'] == 'IDLE' and not ui['playing'] and not ui['paused']
    assert ui.get('local_recording', {}).get('state') != 'RECORDING'
    assert not ui.get('local_transcription', {}).get('service', {}).get('pending')
    assert unit.read_text() == old_unit
    timer = 'aura-yunet-pilot-rollback-' + str(os.getpid())
    subprocess.run(['systemd-run', '--unit=' + timer, '--on-active=2160s',
                    '/usr/bin/python3', '-B', str(root / 'rollback.py')],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, timeout=10)
    report = {'scope': 'LIVE_YUNET_DPU_30MIN_NOT_FIELD_PRECISION_ACCEPTANCE', 'root': str(root),
        'boot_id': args.boot, 'camera_before': before, 'patch_sha256': args.patch_sha256,
        'model_sha256': args.model_sha256, 'timer': timer, 'samples': [],
        'sface_embedding_backend_changed': False, 'identity_database_changed': False,
        'phase': 'STARTING', 'complete': False, 'observe_seconds_target': OBSERVE_SECONDS}
    progress(report)
    passed = False
    started = time.monotonic()
    fd = os.open('/dev/kmsg', os.O_RDONLY | os.O_NONBLOCK)
    os.lseek(fd, 0, os.SEEK_END)
    try:
        service('stop', 'aura-camera-ui.service')
        assert unit.read_text() == old_unit
        temp = unit.with_name(unit.name + '.dpu-candidate-' + str(os.getpid()))
        temp.write_text(new_unit)
        os.replace(str(temp), str(unit))
        service('daemon-reload')
        service('start', '--no-block', 'aura-camera-ui.service')
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                state = camera()
                stats = (state.get('dpu_schedule') or {}).get('optional', {}).get('yunet', {})
                if (stats.get('calls', 0) >= 5 and state.get('face_targets', {}).get('backend') == 'DPU_YUNET_INT8'
                        and not state['camera_error'] and not state['detector_error']):
                    break
            except Exception:
                pass
            time.sleep(.4)
        else:
            raise RuntimeError('DPU face backend did not become ready')
        initial, observe = state, time.monotonic()
        first_cpu, previous_cpu = cpu(), cpu()
        previous_at = observe
        report['phase'] = 'OBSERVING'
        report['kernel_warning_count'] = 0
        report['maximum_observation_age_ms'] = 0
        for i in range(OBSERVE_SECONDS // 5):
            state = camera()
            report['last_state'] = state
            stats = (state.get('dpu_schedule') or {}).get('optional', {}).get('yunet', {})
            assert state['pid'] == initial['pid'], 'Camera process changed'
            assert not state['camera_error'] and not state['detector_error'], 'Camera/detector reported error'
            assert state['observation_age_ms'] is not None and state['observation_age_ms'] < 750, 'Primary observation expired'
            assert not stats.get('disabled') and stats.get('overruns') == 0, 'Optional DPU task disabled: ' + json.dumps(stats)
            assert state.get('face_targets', {}).get('backend') == 'DPU_YUNET_INT8', 'Face backend fell back to CPU'
            kernel = kernel_check(fd)
            report['kernel_warning_count'] += kernel['warnings']
            assert not kernel['warnings'] and not kernel['overruns'] and not kernel['truncated'], 'Kernel transport warning or lost log evidence: ' + json.dumps(kernel)
            current_cpu, current_at = cpu(), time.monotonic()
            interval_cpu = 100 * (1 - (current_cpu[1] - previous_cpu[1]) / float(max(1, current_cpu[0] - previous_cpu[0])))
            if i == 0:
                interval_cpu = None
            report['samples'].append({'elapsed_s': current_at - observe, 'cpu_pct_board': interval_cpu,
                'kernel': kernel, 'health': state})
            report['elapsed_observation_s'] = current_at - observe
            report['maximum_observation_age_ms'] = max(report['maximum_observation_age_ms'], state['observation_age_ms'])
            report['observed_yolo_hz'] = (state['detected_frames'] - initial['detected_frames']) / max(.001, current_at - observe)
            report['observed_yunet_hz'] = (state['dpu_schedule']['optional']['yunet']['calls'] - initial['dpu_schedule']['optional']['yunet']['calls']) / max(.001, current_at - observe)
            progress(report)
            previous_cpu, previous_at = current_cpu, current_at
            time.sleep(max(0, observe + (i + 1) * 5 - time.monotonic()))
        state = camera()
        kernel = kernel_check(fd)
        report['kernel_warning_count'] += kernel['warnings']
        assert not kernel['warnings'] and not kernel['overruns'] and not kernel['truncated'], 'Final kernel check failed'
        duration = time.monotonic() - observe
        report['observed_yolo_hz'] = (state['detected_frames'] - initial['detected_frames']) / duration
        report['observed_yunet_hz'] = (state['dpu_schedule']['optional']['yunet']['calls'] - initial['dpu_schedule']['optional']['yunet']['calls']) / duration
        assert report['observed_yolo_hz'] >= 9, 'Primary detection below 9 Hz'
        assert report['observed_yunet_hz'] >= 2, 'Face DPU execution below 2 Hz'
        last_cpu = cpu()
        report['cpu_pct_board_observation'] = 100 * (1 - (last_cpu[1] - first_cpu[1]) / float(last_cpu[0] - first_cpu[0]))
        assert ui_pid == service('show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value').strip()
        assert all(digest(p) == sha for p, sha in protected.items())
        assert all(digest(original / rel) == sha for rel, sha in manifest['baseline'].items())
        assert x_pid == service('show', 'xserver-nodm.service', '-p', 'MainPID', '--value').strip()
        assert not (state['dpu_schedule']['optional']['yunet'].get('disabled'))
        passed = True
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        os.close(fd)
        if not passed:
            result = subprocess.run(['python3', '-B', str(root / 'rollback.py')],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=50)
            report['rollback_exit_code'] = result.returncode
            report['rollback_output'] = result.stdout.decode(errors='replace')[-1500:]
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    restored = camera()
                    if restored['detected_frames'] > 2 and not restored['camera_error'] and not restored['detector_error']:
                        report['restored'] = restored
                        break
                except Exception:
                    pass
                time.sleep(.4)
        if passed or report.get('restored'):
            service('stop', timer + '.timer')
    report['passed'] = passed
    report['complete'] = True
    report['phase'] = 'PASSED_RETAINED' if passed else 'FAILED_REVERTED' if report.get('restored') else 'FAILED_RESTORE_PENDING'
    report['elapsed_s'] = time.monotonic() - started
    report['ui_pid_preserved'] = ui_pid == service('show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value').strip()
    report['protected_configuration_unchanged'] = all(digest(p) == sha for p, sha in protected.items())
    (root / 'deployment-result.json').write_text(json.dumps(report, indent=2) + '\n')
    progress(report)
    print(json.dumps({k: v for k, v in report.items() if k != 'samples'}), flush=True)


if __name__ == '__main__':
    if os.environ.get('AURA_DPU_LIVE_VALIDATE') == '1':
        try:
            main()
        except Exception as exc:
            progress({'complete': True, 'phase': 'FAILED', 'error': type(exc).__name__ + ': ' + str(exc)})
            raise
    else:
        JOBROOT.mkdir(parents=True, exist_ok=True)
        assert not (JOBROOT / 'progress.json').exists(), 'Validation already attempted; inspect evidence'
        name = 'aura-yunet-live-validation-' + SOURCE_SHA[:16]
        subprocess.run(['systemd-run', '--unit=' + name, '--property=RuntimeMaxSec=2100',
            '--setenv=AURA_DPU_LIVE_VALIDATE=1', '/usr/bin/python3', '-B', str(SOURCE)], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
        print(json.dumps({'started': True, 'unit': name, 'progress': str(JOBROOT / 'progress.json')}))
