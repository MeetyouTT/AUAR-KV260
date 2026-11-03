#!/usr/bin/env python3
"""Supervise the existing cached GTK UI in its own systemd service."""
import argparse
import fcntl
import hashlib
import json
import os
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


def check_port_unused(port):
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', port))


def preflight(config):
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported launcher configuration')
    root = Path(config['runtime']).resolve(strict=True)
    source = root/'aura/tools/board_avatar_gtk.py'
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


def configure_display(config, env):
    deadline = time.monotonic()+config['display_wait_seconds']
    last_error = 'X display not ready'
    while not STOP.is_set() and time.monotonic() < deadline:
        try:
            modes = run(['xrandr', '--verbose'], env)
            edid = Path(config['edid_file']).read_bytes()
            if hashlib.sha256(edid).hexdigest() != config['edid_sha256']:
                raise RuntimeError('Expected screen EDID not ready')
            if config['mode'] not in modes:
                raise RuntimeError('Expected screen mode not ready')
            run(['xrandr', '--output', config['output'], '--mode', config['mode'],
                 '--rate', config['rate']], env)
            current = run(['xrandr', '--current'], env)
            if config['output']+' connected primary '+config['mode']+'+0+0' not in current:
                raise RuntimeError('Display mode readback mismatch')
            run(['xset', 'dpms', 'force', 'on'], env)
            return {'display': current, 'edid_sha256': config['edid_sha256']}
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            last_error = str(exc)
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
            api(config, message)
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
