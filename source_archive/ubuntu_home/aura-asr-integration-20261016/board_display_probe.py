"""Read-only display/startup evidence; never modeset or restart a service."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError as exc:
        return {'error': str(exc)}


def run(args, limit=9000):
    try:
        p = subprocess.run(args, env=dict(os.environ, DISPLAY=':0'),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=6)
        return {'exit_code': p.returncode, 'output': p.stdout[-limit:]}
    except Exception as exc:
        return {'error': str(exc)}


result = {'boot_id': read('/proc/sys/kernel/random/boot_id'),
          'uptime': read('/proc/uptime'), 'connectors': {}}
for p in Path('/sys/class/drm').glob('card*-*'):
    if not (p/'status').exists():
        continue
    v = {name: read(p/name) for name in ('status', 'enabled', 'dpms', 'modes')}
    try:
        raw = (p/'edid').read_bytes()
        v['edid_bytes'] = len(raw)
        v['edid_sha256'] = hashlib.sha256(raw).hexdigest()
        v['edid_hex'] = raw.hex()
    except OSError as exc:
        v['edid_error'] = str(exc)
    result['connectors'][p.name] = v
result['xrandr'] = run(['xrandr', '--verbose'])
result['xset'] = run(['xset', 'q'], 2200)
result['touch'] = run(['xinput', 'list', '--name-only'], 1200)
result['services'] = run(['systemctl', 'show', 'aura-avatar-ui.service', 'xserver-nodm.service',
                          'aura-camera-ui.service', '-p', 'Id', '-p', 'ActiveState', '-p',
                          'SubState', '-p', 'MainPID', '-p', 'ExecStart', '-p', 'NRestarts'], 4200)
result['drm_state'] = read('/sys/kernel/debug/dri/0/state')
result['startup_log'] = run(['journalctl', '-b', '-u', 'aura-avatar-ui.service',
                             '--no-pager', '-o', 'short-monotonic', '-n', '22'], 6000)
kernel = run(['dmesg'], 200000)
lines = kernel.get('output', '').splitlines()
result['display_kernel_log'] = [line for line in lines if any(
    k in line.lower() for k in ('fd4a0000', 'dpdma', 'drm', 'edid', 'underflow', 'training', 'dpll'))][-35:]
ui = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
try:
    launch = json.loads((ui/'launch.json').read_text())
    result['launch'] = {k: launch.get(k) for k in ('pid', 'boot_id', 'supervisor_pid', 'session')}
    setup = Path(launch['session'])/'setup.json'
    result['display_setup'] = json.loads(setup.read_text()) if setup.exists() else None
    pid = launch.get('supervisor_pid')
    args = Path('/proc/%s/cmdline' % pid).read_bytes().decode().split('\0')
    result['supervisor_args'] = args
    if '--config' in args:
        conf = Path(args[args.index('--config')+1])
        result['active_config_path'] = str(conf)
        result['active_launcher_sha256'] = hashlib.sha256((conf.parent/'launcher.py').read_bytes()).hexdigest()
        config = json.loads(conf.read_text())
        result['display_config'] = {k: config.get(k) for k in ('output', 'mode', 'rate', 'edid_file',
            'edid_sha256', 'display_wait_seconds', 'verified_timing_fallback')}
except Exception as exc:
    result['startup_probe_error'] = str(exc)
try:
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state', timeout=2) as f:
        state = json.load(f)
    result['ui'] = {k: state.get(k) for k in ('ui_page', 'ui_layer', 'phase', 'error', 'ui_settings')}
except Exception as exc:
    result['ui_error'] = str(exc)
print(json.dumps(result, ensure_ascii=False))
