#!/usr/bin/env python3
"""Supervise the existing cached GTK UI in its own systemd service."""
import argparse
import errno
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request

STOP = threading.Event()


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(temporary), str(path))


def emit(kind, **values):
    print(json.dumps(dict(event=kind, **values), ensure_ascii=False), flush=True)


def notify(message):
    address = os.environ.get('NOTIFY_SOCKET')
    if not address:
        return
    if address.startswith('@'):
        address = '\0'+address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as stream:
        stream.connect(address)
        stream.sendall(message.encode())


def run(args, env):
    result = subprocess.run(args, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=8)
    if result.returncode:
        raise RuntimeError(str(args)+': '+result.stdout[-1000:])
    return result.stdout


def api(config, message=None):
    base = 'http://127.0.0.1:'+str(config['port'])
    request = base+'/api/state'
    if message is not None:
        request = urllib.request.Request(
            base+'/api/command', data=json.dumps(message).encode(),
            headers={'Content-Type': 'application/json', 'Origin': base})
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.load(response)


def check_port_unused(port, wait_seconds=70):
    deadline = time.monotonic()+wait_seconds
    while not STOP.is_set():
        try:
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(('127.0.0.1', port))
            return
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE or time.monotonic() >= deadline:
                raise
            # The old exclusive HTTP server can leave this port in TIME_WAIT.
            # Wait within TimeoutStartSec, without killing another process.
            STOP.wait(.25)
    raise RuntimeError('UI startup cancelled while waiting for its control port')


def preflight(config):
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported launcher configuration')
    root = Path(config['runtime']).resolve(strict=True)
    source = root/'aura/tools/board_avatar_pan.py'
    if hashlib.sha256(source.read_bytes()).hexdigest() != config['gui_sha256']:
        raise ValueError('Installed GUI source SHA256 mismatch')
    for relative, expected in config.get('component_sha256', {}).items():
        component = root/'aura'/relative
        if hashlib.sha256(component.read_bytes()).hexdigest() != expected:
            raise ValueError('UI component SHA256 mismatch: '+relative)
    if os.uname().release != config['kernel_release']:
        raise ValueError('Touch module does not match this kernel')
    module = Path(config['touch_module'])
    if hashlib.sha256(module.read_bytes()).hexdigest() != config['touch_module_sha256']:
        raise ValueError('Installed touch module SHA256 mismatch')
    for name in ('xrandr', 'xinput', 'xset', 'modprobe'):
        if not shutil.which(name):
            raise RuntimeError('Required command unavailable: '+name)
    return root, source


def display_boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def display_retrain_needed(config):
    if not config.get('startup_display_retrain', False):
        return False
    marker = Path(config['display_recovery_marker'])
    try:
        saved = json.loads(marker.read_text())
    except (OSError, ValueError):
        return True
    if not isinstance(saved, dict):
        return True
    return any(saved.get(key) != value for key, value in {
        'boot_id': display_boot_id(), 'output': config['output'],
        'mode': config['mode'], 'edid_sha256': config['edid_sha256'],
    }.items())


def configure_display(config, env):
    started = time.monotonic()
    deadline = started+config['display_wait_seconds']
    grace = config.get('edid_grace_seconds', 0)
    stable_seconds = config.get('display_stable_seconds', 0)
    off_seconds = config.get('display_retrain_off_seconds', 1)
    if not (0 <= grace <= 30 and 0 <= stable_seconds <= 10 and 0.2 <= off_seconds <= 2):
        raise ValueError('Invalid display startup wait limits')
    needs_retrain = display_retrain_needed(config)
    retrained = False
    stable_since = None
    stable_identity = None
    last_error = 'X display not ready'
    while not STOP.is_set() and time.monotonic() < deadline:
        try:
            modes = run(['xrandr', '--verbose'], env)
            edid = Path(config['edid_file']).read_bytes()
            fallback = False
            if Path(config['edid_file']).with_name('status').read_text().strip() != 'connected':
                raise RuntimeError('Display output is disconnected')
            if not edid and config.get('verified_timing_fallback'):
                # This exact timing was read from this screen's verified EDID,
                # not generated by cvt or guessed from its advertised resolution.
                names = run(['xinput','list','--name-only'],env).splitlines()
                if config['touch_name'] not in names:
                    raise RuntimeError('Verified WaveShare touch device is absent')
                if time.monotonic()-started < grace:
                    raise RuntimeError('Waiting for live screen EDID before timing fallback')
                timing = config['verified_timing_fallback']
                expected = ['49.000','1024','1072','1168','1312','600','603','613','624','-HSync','-VSync']
                if timing != expected or config['mode'] != '1024x600':
                    raise ValueError('Unreviewed fallback display timing')
                if config['mode'] not in modes:
                    run(['xrandr','--newmode',config['mode']]+timing,env)
                    run(['xrandr','--addmode',config['output'],config['mode']],env)
                    modes = run(['xrandr','--verbose'],env)
                patterns = (r'1024x600\s+\([^\n]+\)\s+49\.000MHz\s+-HSync\s+-VSync',
                    r'h: width\s+1024 start\s+1072 end\s+1168 total\s+1312',
                    r'v: height\s+600 start\s+603 end\s+613 total\s+624')
                if not all(re.search(pattern,modes) for pattern in patterns):
                    raise RuntimeError('Existing display mode does not match verified timing')
                fallback = True
            elif hashlib.sha256(edid).hexdigest() != config['edid_sha256']:
                raise RuntimeError('Expected screen EDID not ready')
            if config['mode'] not in modes:
                raise RuntimeError('Expected screen mode not ready')
            identity = (fallback, hashlib.sha256(edid).hexdigest())
            now = time.monotonic()
            if identity != stable_identity:
                stable_identity, stable_since = identity, now
            if now-stable_since < stable_seconds:
                STOP.wait(min(1, stable_seconds-(now-stable_since)))
                continue
            enable = ['xrandr', '--output', config['output'], '--mode', config['mode'],
                      '--rate', config['rate']]
            if needs_retrain and not retrained:
                # A same-mode request can leave the original scanout untouched.
                # Record before disabling: a service crash must not cause a
                # series of output-off pulses in the same boot.
                atomic_json(config['display_recovery_marker'], {
                    'boot_id':display_boot_id(), 'output':config['output'],
                    'mode':config['mode'], 'edid_sha256':config['edid_sha256'],
                    'mode_source':'previously_verified_timing' if fallback else 'live_edid',
                    'software_modeset_verified':False, 'physical_panel_verified':False})
                retrained = True
                try:
                    run(['xrandr', '--output', config['output'], '--off'], env)
                    STOP.wait(off_seconds)
                finally:
                    # Even cancellation or a failed disable must attempt restore.
                    run(enable, env)
                if STOP.is_set():
                    raise RuntimeError('Display startup cancelled after output restore')
            else:
                run(enable, env)
            current = run(['xrandr', '--current'], env)
            if config['output']+' connected primary '+config['mode']+'+0+0' not in current:
                raise RuntimeError('Display mode readback mismatch')
            run(['xset', 'dpms', 'force', 'on'], env)
            setup = {'display':current,'edid_sha256':None if fallback else config['edid_sha256'],
                     'mode_source':'previously_verified_timing' if fallback else 'live_edid',
                     'edid_missing':fallback, 'startup_output_retrained':retrained,
                     'display_wait_elapsed_seconds':round(time.monotonic()-started, 3),
                     'physical_panel_verified':False}
            if config.get('startup_display_retrain', False):
                atomic_json(config['display_recovery_marker'], {
                    'boot_id':display_boot_id(), 'output':config['output'],
                    'mode':config['mode'], 'edid_sha256':config['edid_sha256'],
                    'mode_source':setup['mode_source'], 'software_modeset_verified':True,
                    'physical_panel_verified':False})
            return setup
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            last_error = str(exc)
            stable_identity = stable_since = None
            STOP.wait(1)
    raise RuntimeError('Display startup timed out: '+last_error)


def map_touch(config, env):
    names = run(['xinput', 'list', '--name-only'], env).splitlines()
    if config['touch_name'] not in names:
        return None
    identifier = run(['xinput', 'list', '--id-only', config['touch_name']], env).strip()
    run(['xinput', 'map-to-output', config['touch_name'], config['output']], env)
    return identifier


def stop_child(child, config):
    if child.poll() is not None:
        return
    for message in ({'type': 'event', 'event': 'cancel'}, {'type': 'save_evidence'}):
        try:
            result = api(config, message)
            if message['type'] == 'save_evidence' and result.get('queued') and result.get('report'):
                deadline = time.monotonic()+5
                while not Path(result['report']).exists() and child.poll() is None and time.monotonic()<deadline:
                    time.sleep(.05)
                if not Path(result['report']).exists():
                    emit('STOP_DIAGNOSTIC_INCOMPLETE', report=result['report'])
        except (OSError, ValueError) as exc:
            emit('STOP_API_UNAVAILABLE', error=str(exc))
    child.terminate()
    try:
        child.wait(timeout=6)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=3)


def supervise(config):
    root, source = preflight(config)
    env = dict(os.environ, DISPLAY=config['display'], PYTHONUNBUFFERED='1')
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: STOP.set())
    with Path(config['lock_file']).open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():
                continue
            try:
                args = (process/'cmdline').read_bytes().split(b'\0')
            except OSError:
                continue
            if str(source).encode() in args:
                raise RuntimeError('Existing UI process: '+process.name)
        check_port_unused(config['port'])
        if not Path('/sys/module/hid_multitouch').exists():
            run(['modprobe', 'hid-multitouch'], env)
        notify('STATUS=Waiting for the existing X display')
        setup = configure_display(config, env)
        touch_id = map_touch(config, env)
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        sessions = root/'managed-runs'
        sessions.mkdir(exist_ok=True)
        session = sessions/(boot+'-'+str(time.monotonic_ns()))
        session.mkdir()
        if (root/'launch.json').exists():
            shutil.copy2(str(root/'launch.json'), str(session/'previous-launch.json'))
        setup.update(boot_id=boot, touch_id=touch_id, supervisor_pid=os.getpid())
        atomic_json(session/'setup.json', setup)
        log = session/'stage.log'
        pointer = root/'stage.log'
        if pointer.is_symlink():
            pointer.resolve(strict=True).relative_to(sessions.resolve())
        elif pointer.exists():
            raise RuntimeError('Prior unmanaged stage.log must be backed up before activation')
        with log.open('xb') as stream:
            temporary = root/('stage.log.tmp-'+str(os.getpid()))
            temporary.symlink_to(log)
            os.replace(str(temporary), str(pointer))
            args = [sys.executable, '-B', str(source), '--evidence-root', str(session/'evidence')]
            child = subprocess.Popen(args, cwd=str(root/'aura'), env=env,
                                     stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
        info = {'pid': child.pid, 'args': args, 'evidence': str(session/'evidence'),
                'log': str(log), 'boot_id': boot, 'supervisor_pid': os.getpid(),
                'service': config['service_name'], 'session': str(session)}
        atomic_json(root/'launch.json', info)
        emit('CHILD_STARTING', **info)
        ready = False
        deadline = time.monotonic()+config['ready_wait_seconds']
        last_scan = 0.0
        try:
            while not STOP.is_set():
                code = child.poll()
                if code is not None:
                    emit('CHILD_EXITED', returncode=code, was_ready=ready)
                    return 0 if code == 0 and ready else 1
                now = time.monotonic()
                if not ready:
                    try:
                        state = api(config)
                        ready = state.get('backend') == 'gtk3-gstreamer' and state.get('cached_only') is True
                    except (OSError, ValueError):
                        pass
                    if ready:
                        atomic_json(session/'ready.json', dict(info, state=state))
                        notify('READY=1\nSTATUS=GTK UI ready on '+config['mode'])
                        emit('READY', pid=child.pid, volume=state.get('ui_settings', {}).get('volume'))
                    elif now > deadline:
                        raise RuntimeError('GUI API readiness timed out')
                if now-last_scan > 3:
                    try:
                        names = run(['xinput', 'list', '--name-only'], env).splitlines()
                        current_id = (run(['xinput', 'list', '--id-only', config['touch_name']], env).strip()
                                      if config['touch_name'] in names else None)
                        if current_id != touch_id:
                            touch_id = map_touch(config, env)
                            emit('TOUCH_DEVICE_CHANGED', touch_id=touch_id)
                    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                        emit('TOUCH_MAPPING_UNAVAILABLE', error=str(exc))
                    last_scan = now
                STOP.wait(.25 if not ready else 1)
        finally:
            notify('STOPPING=1')
            stop_child(child, config)
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    try:
        if args.preflight:
            root, source = preflight(config)
            emit('PREFLIGHT_PASS', runtime=str(root), source=str(source))
            return 0
        return supervise(config)
    except Exception as exc:
        emit('FAILED', error=type(exc).__name__+': '+str(exc))
        return 1


if __name__ == '__main__':
    sys.exit(main())
