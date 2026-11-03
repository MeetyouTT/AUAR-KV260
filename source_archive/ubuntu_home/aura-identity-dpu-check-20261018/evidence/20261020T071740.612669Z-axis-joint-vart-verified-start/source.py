"""One guarded, reversible DPU/VSRV + same-camera-feed bench activation. NO ARM."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import traceback
import urllib.request

BOOT = '3e1add36-b917-4289-91dc-699348528782'
FDT_SHA = '501cf86ec839373df57862f829d34c8b5ab90a0eeeb6db0ac679bce831899929'
CAMERA = Path('/home/root/aura-enrollment-photos-20261019/candidate-6f1aa1842d53/runtime/aura')
SOURCE_SHA = '8aa94461e6b505857a199d91a0d35c78364d4621e1c7894c0d2798706ac38a8f'
STAGE = Path('/home/root/aura-pan-follow-20261019/test-2f1e928a6ec30f9b/aura')
JOINT = Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
TX = Path('/home/root/aura-pan-follow-20261020/activation-axis-03')
UNIT = Path('/etc/systemd/system/aura-camera-ui.service')
TIMER = 'aura-pan-revert-axis-03'
JOINT_VART = 'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-v1/aura-visual-servo-b4096-v1.xclbin\n'
PAYLOAD = {
    'common/motion_observation.py': 'c676a81093793ee7046d1937c56478efe27a94505c9fd62696e82fc426acf9dc',
    'board/motion/__init__.py': 'bf49004e89b57c75db31346f3c4663c21af0584297d829b7c0ace623fc0a3fa6',
    'board/motion/camera_feed.py': '2bf8983cf195af94d4a6faefc48eefdbc9b2a02ffcd863f9ffac006dc495f3e7',
    'board/motion/follow.py': '6d43ad1aeb15258d318fd1a5d5b96cdfedeb310d517b3d043d4a3aee77647e7d',
    'board/motion/vsrv_driver.py': '17c3a5f59e8dfb449698a2a94d42308b86f28654c6f766dfd31b187003b2b88d',
    'tools/board_camera_motion.py': '1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005',
    'tools/board_pan_follow.py': 'c9896ef2d70792f1d992920ea1fb36eeb480780d8e0b060ebe3ea1cf44dc53e8',
    'config/pan_follow.shadow.json': 'dc27952c0b3ef94a6230e6030a45c94a3572d6ad6479a67bd58a554f0604f49a',
}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, timeout=45):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('Command failed '+str(args[:3])+': '+result.stderr[-700:])
    return result.stdout.strip()


def get(port, path):
    with OPENER.open('http://127.0.0.1:%d%s' % (port, path), timeout=2) as stream:
        return json.load(stream)


def save(name, value):
    path = TX/(name+'.json')
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2)+'\n')
    temp.replace(path)


def guard():
    assert os.uname().machine == 'aarch64' and os.geteuid() == 0
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
    assert sha(Path('/sys/firmware/fdt')) == FDT_SHA
    assert sha(JOINT/'common.py') == 'f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
    assert sha(JOINT/'load.py') == '39280c42c39ca5644193cdca105f85b13ac647c78605f252793271a5223d20ae'


def checked_common():
    sys.path.insert(0, str(JOINT))
    import common
    common.BOOT = BOOT
    common.guard()
    common.check_runtime()
    return common


def camera_health():
    value = get(8790, '/health')
    assert not value['camera_error'] and not value['detector_error'], 'Camera/detector error'
    assert value['identity_recognition'] is True, 'Identity service not ready'
    assert 0 <= value['observation_age_ms'] < 500, 'Camera observation stale: '+str(value['observation_age_ms'])
    return {key: value.get(key) for key in ('pid', 'service_epoch', 'camera_epoch', 'detected_frames',
            'observation_age_ms', 'detection_hz', 'identity_recognition', 'camera_error', 'detector_error')}


def rollback():
    # The timer is an independent backstop. Never undo a newer Windows unit.
    guard()
    if (TX/'committed.json').exists():
        return {'status': 'COMMITTED_TRANSACTION_NO_REVERT'}
    common = checked_common()
    run(['systemctl', 'stop', 'aura-camera-ui.service'], 15)
    common.no_clients()
    if common.active() == [common.APP]:
        with common.open_registers() as io:
            from vsrv_driver import VSRVDriver
            VSRVDriver(io, 0x14da0e60, BOOT).stop()
        run(['xmutil', 'unloadapp'])
    if common.active() == []:
        run(['xmutil', 'loadapp', common.BASELINE])
    assert common.active() == [common.BASELINE]
    assert common.firmware() == common.BASELINE+'.bit.bin'
    if UNIT.read_bytes() == (TX/'camera-unit.new').read_bytes():
        UNIT.write_bytes((TX/'camera-unit.before').read_bytes())
    assert Path('/etc/vart.conf').read_bytes() == (TX/'vart.conf.before').read_bytes()
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'start', 'aura-camera-ui.service'], 15)
    health = None
    for _ in range(30):
        try:
            health = camera_health()
            break
        except Exception:
            time.sleep(.5)
    assert health is not None, 'Official platform restored; camera readiness not confirmed'
    value = {'status': 'OFFICIAL_PLATFORM_AND_CAMERA_RESTORED', 'camera': health,
             'firmware': common.firmware(), 'pwm_command_emitted': False}
    save('rollback', value)
    return value


def worker():
    report = {'status': 'STARTING', 'boot_id': BOOT, 'pwm_command_emitted': False,
              'arm_command_emitted': False, 'qualification_scope': 'CONTROLLED_BENCH_NO_PWM'}
    switch_prepared = False
    try:
        guard()
        common = checked_common()
        assert common.active() == [common.BASELINE] and common.firmware() == common.BASELINE+'.bit.bin'
        assert run(['systemctl', 'show', 'aura-camera-ui.service', '-p', 'WorkingDirectory', '--value']) == str(CAMERA)
        assert sha(CAMERA/'board/vision/ui_camera_service.py') == SOURCE_SHA
        assert not list(Path('/etc/systemd/system/aura-camera-ui.service.d').glob('*.conf'))
        health = camera_health()
        identity = get(8790, '/v1/ui/status').get('modules', {}).get('identity', {})
        assert identity.get('state') not in ('ENROLLING', 'SAMPLING'), 'Identity enrollment is in progress'
        gui = get(8783, '/api/state')
        assert gui.get('phase') == 'IDLE' and not gui.get('playing')
        assert gui.get('automatic_conversation', {}).get('state') == 'STOPPED'
        gui_pid = run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value'])
        gui_root = Path(run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'WorkingDirectory', '--value']))
        preserved = {str(path): sha(path) for path in (CAMERA/'board').rglob('*.py')
                     if path == CAMERA/'board/vision/ui_camera_service.py' or 'identity' in path.parts}
        for path in [gui_root/'tools/board_avatar_gtk.py', gui_root/'config/board_avatar_gtk.json']:
            if path.exists():
                preserved[str(path)] = sha(path)
        old_unit = UNIT.read_bytes()
        entry = str(CAMERA/'board/vision/ui_camera_service.py').encode()
        assert old_unit.count(entry) == 1
        new_unit = old_unit.replace(entry, str(CAMERA/'tools/board_camera_motion.py').encode())
        (TX/'camera-unit.before').write_bytes(old_unit)
        (TX/'camera-unit.new').write_bytes(new_unit)
        (TX/'vart.conf.before').write_bytes(Path('/etc/vart.conf').read_bytes())
        save('preserved-source-hashes', preserved)
        args = shlex.split(next(line.split('=', 1)[1] for line in old_unit.decode().splitlines() if line.startswith('ExecStart=')))
        config = Path(args[args.index('--config')+1])
        assert config.is_file()
        report['before'] = health
        report['camera_root'] = str(CAMERA)
        report['gui_root'] = str(gui_root)
        report['config_sha256'] = sha(config)
        for name, digest in PAYLOAD.items():
            assert sha(STAGE/name) == digest, name
            target = CAMERA/name
            assert not target.is_symlink()
            if target.exists():
                assert sha(target) == digest, 'Different existing motion file: '+name
        # Install additive files only; never overwrite an existing different file.
        created = []
        for name in PAYLOAD:
            target = CAMERA/name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write((STAGE/name).read_bytes())
                created.append(name)
        report['created_files'] = created
        script = Path(__file__).resolve()
        run(['systemd-run', '--unit='+TIMER, '--on-active=180s', '/usr/bin/python3', '-B', str(script), '--rollback'], 10)
        switch_prepared = True
        save('phase', {'phase': 'STOP_CAMERA_AND_CHECK_NO_DPU_CLIENTS'})
        assert UNIT.read_bytes() == old_unit and sha(config) == report['config_sha256']
        run(['systemctl', 'stop', 'aura-camera-ui.service'], 15)
        common.no_clients()
        assert all(sha(Path(path)) == digest for path, digest in preserved.items())
        save('phase', {'phase': 'LOAD_JOINT_WITH_PWM_DISABLED'})
        # Reuse the audited load sequence and all its baseline/runtime/slot guards.
        captured = {}
        def capture(name, value):
            captured[name] = value
            save('joint-'+name, value)
        common.save = capture
        path = JOINT/'load.py'
        exec(compile(path.read_bytes(), str(path), 'exec'), {'__name__': '__main__', '__file__': str(path)})
        assert captured.get('loaded', {}).get('passed') is True
        report['joint'] = captured['loaded']
        joint_vart = Path('/etc/vart.conf').read_text()
        report['joint_vart_conf'] = joint_vart
        assert joint_vart == JOINT_VART, 'VART config must select the exact hashed joint runtime'
        save('phase', {'phase': 'CHECK_CURRENT_DPU_MODEL_WITH_CAMERA_STOPPED'})
        checked = subprocess.run(args+['--check'], cwd=str(CAMERA), capture_output=True, text=True, timeout=40)
        (TX/'camera-check.stdout').write_text(checked.stdout)
        (TX/'camera-check.stderr').write_text(checked.stderr)
        assert checked.returncode == 0, 'Current camera model preflight failed'
        check = json.loads(checked.stdout.strip().splitlines()[-1])
        assert check['status'] == 'PASS' and check['camera_opened'] is False
        report['model_check'] = check
        common.no_clients()
        assert UNIT.read_bytes() == old_unit and sha(config) == report['config_sha256']
        UNIT.write_bytes(new_unit)
        run(['systemctl', 'daemon-reload'])
        save('phase', {'phase': 'RESTART_SAME_CAMERA_WITH_READ_ONLY_MOTION_FEED'})
        run(['systemctl', 'start', 'aura-camera-ui.service'], 15)
        after = None
        for _ in range(40):
            try:
                after = camera_health()
                packet = get(8790, '/v1/motion/observation')
                assert packet['board_boot_id'] == BOOT and packet['source_kind'] == 'actual'
                assert packet['state'] not in ('CAMERA_ERROR', 'DETECTOR_ERROR', 'INCONSISTENT_SOURCE')
                if after['detected_frames'] >= 5:
                    break
                after = None
            except Exception:
                after = None
            time.sleep(.5)
        assert after is not None, 'Camera/feed readiness deadline'
        # Collect real coordinates only; no images/face templates/identity names.
        save('phase', {'phase': 'TEN_SECOND_LIVE_SHADOW_NO_PWM'})
        shadow = subprocess.Popen(['/usr/bin/python3', '-B', str(CAMERA/'tools/board_pan_follow.py'), '--live',
                                   '--duration', '10', '--output', str(TX/'live-shadow.jsonl')],
                                  cwd=str(CAMERA), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        states, frames, rows = {}, set(), 0
        until = time.monotonic()+10
        with (TX/'live-source.jsonl').open('x') as stream:
            while time.monotonic() < until:
                packet = get(8790, '/v1/motion/observation')
                assert packet['board_boot_id'] == BOOT and packet['source_kind'] == 'actual'
                stream.write(json.dumps({'received_mono_ms': int(time.monotonic()*1000), 'observation': packet})+'\n')
                states[packet['state']] = states.get(packet['state'], 0)+1
                frames.add((packet['camera_epoch'], packet['source_frame_id']))
                rows += 1
                time.sleep(.05)
        shadow_stdout, shadow_stderr = shadow.communicate(timeout=5)
        (TX/'shadow.stdout').write_text(shadow_stdout)
        (TX/'shadow.stderr').write_text(shadow_stderr)
        assert shadow.returncode == 0, 'Shadow evaluation process failed'
        report['live_source'] = {'duration_s': 10, 'rows': rows, 'distinct_frames': len(frames), 'states': states}
        report['shadow'] = json.loads((TX/'live-shadow.jsonl.summary.json').read_text())
        time.sleep(1)
        save('phase', {'phase': 'FINAL_HEALTH_AND_PRESERVATION_CHECK'})
        final = camera_health()
        final_guards = {
            'camera_progressed': final['detected_frames'] > after['detected_frames'],
            'gui_pid_unchanged': run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value']) == gui_pid,
            'preserved_sources_unchanged': all(sha(Path(path)) == digest for path, digest in preserved.items()),
            'config_unchanged': sha(config) == report['config_sha256'],
            'unit_is_candidate': UNIT.read_bytes() == new_unit,
            'vart_selects_verified_joint': Path('/etc/vart.conf').read_text() == JOINT_VART,
            'joint_is_active': common.active() == [common.APP]}
        report['final_guards'] = final_guards
        assert all(final_guards.values()), 'Final guards: '+repr(final_guards)
        with common.open_registers() as io:
            from vsrv_driver import VSRVDriver
            report['final_vsrv'] = VSRVDriver(io, 0x14da0e60, BOOT).stop()
        assert report['final_vsrv']['flags'] == 0 and report['final_vsrv']['lease_left_ms'] == 0
        report.update(status='JOINT_AND_REAL_CAMERA_FEED_READY_PWM_DISABLED', after=final,
                      firmware=common.firmware(), gui_pid_unchanged=gui_pid,
                      preserved_sources_unchanged=len(preserved), mechanical_reference_verified=False)
        save('committed', {'boot_id': BOOT, 'firmware': common.firmware(), 'pwm_enabled': False})
        run(['systemctl', 'stop', TIMER+'.timer'], 10)
    except BaseException as exc:
        report.update(status='ACTIVATION_FAILED', error=type(exc).__name__+': '+str(exc))
        (TX/'failure-traceback.txt').write_text(traceback.format_exc())
        if switch_prepared:
            try:
                report['rollback'] = rollback()
                run(['systemctl', 'stop', TIMER+'.timer'], 10)
            except BaseException as rollback_exc:
                report['rollback_error'] = type(rollback_exc).__name__+': '+str(rollback_exc)
    save('result', report)
    print(json.dumps(report), flush=True)


def main():
    guard()
    if len(sys.argv) > 1:
        with Path('/run/aura-pan-activation.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if sys.argv[1:] == ['--worker']:
                worker()
            elif sys.argv[1:] == ['--rollback']:
                print(json.dumps(rollback()), flush=True)
            else:
                raise ValueError('Unknown execution mode')
        return
    TX.mkdir(parents=True, exist_ok=False)
    os.chmod(TX, 0o700)
    # The staging launcher provides the exact checked source as `f`.
    script = Path(globals()['f']).resolve()
    assert script.name == 'source.py' and script.is_file()
    with (TX/'worker.log').open('xb') as log:
        process = subprocess.Popen(['/usr/bin/python3', '-B', str(script), '--worker'],
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    print(json.dumps({'status': 'NO_PWM_ACTIVATION_WORKER_STARTED', 'worker_pid': process.pid,
                      'transaction': str(TX), 'script': str(script), 'pwm_enabled': False}), flush=True)


if __name__ == '__main__':
    main()
