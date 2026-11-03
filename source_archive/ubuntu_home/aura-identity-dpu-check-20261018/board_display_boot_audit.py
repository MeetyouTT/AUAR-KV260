"""Read-only display evidence."""
import base64
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

env = dict(os.environ, DISPLAY=':0')
def run(args, limit=18000):
    try:
        result = subprocess.run(args, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=4)
        return dict(rc=result.returncode, text=result.stdout[-limit:])
    except Exception as exc:
        return dict(error=type(exc).__name__+': '+str(exc))

v = dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
         uptime=Path('/proc/uptime').read_text().split()[0], display_commands_sent=0,
         movement_commands_sent=0, files_modified=0)
v['unit'] = run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID',
                 '-p', 'ActiveState', '-p', 'NRestarts', '-p', 'ExecStart'])
pid = int(run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value'])['text'].strip())
argv = Path('/proc/%d/cmdline' % pid).read_bytes().decode().split('\0')
config_path = Path(argv[argv.index('--config')+1])
config = json.loads(config_path.read_text())
launcher = config_path.with_name('launcher.py')
v['startup'] = dict(config_path=str(config_path), launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),
    config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
    config={k:config.get(k) for k in ['runtime', 'display', 'output', 'mode', 'rate', 'edid_file',
        'edid_sha256', 'startup_display_retrain', 'display_retrain_off_seconds', 'display_recovery_marker',
        'edid_grace_seconds', 'display_stable_seconds', 'verified_timing_fallback']})
env['DISPLAY'] = config.get('display', ':0')
v['markers'] = {}
for name in {config.get('display_recovery_marker', '/run/aura-display-startup.json'), '/run/aura-display-startup.json'}:
    p = Path(name)
    if p.exists():
        try: v['markers'][name] = json.loads(p.read_text())
        except ValueError: v['markers'][name] = dict(invalid_json=True)
runtime = Path(config['runtime'])
if (runtime/'launch.json').exists():
    launch = json.loads((runtime/'launch.json').read_text())
    v['launch'] = {k:launch.get(k) for k in ['pid', 'supervisor_pid', 'session', 'log']}
    session = Path(launch['session'])
    if (session/'setup.json').exists(): v['setup'] = json.loads((session/'setup.json').read_text())
v['connectors'] = []
for edid in Path('/sys/class/drm').glob('card*-*/edid'):
    raw = edid.read_bytes(); parent = edid.parent
    row = dict(path=str(parent), edid_bytes=len(raw), edid_sha256=hashlib.sha256(raw).hexdigest(),
               edid_base64=base64.b64encode(raw).decode())
    for field in ['status', 'enabled', 'modes', 'dpms']:
        if (parent/field).exists(): row[field] = (parent/field).read_text().strip()
    v['connectors'].append(row)
v['xrandr'] = run(['xrandr', '--verbose'], 12000)
v['boot_journal'] = run(['journalctl', '-b', '-u', 'aura-avatar-ui.service', '--no-pager', '-o', 'cat', '-n', '55'], 10000)
kernel = run(['dmesg'], 24000)
v['kernel_display'] = [line for line in kernel.get('text','').splitlines()
    if re.search(r'edid|drm|display|hdmi|dp_sub|dpsub|pixel|zynqmp.*dp|clock.*-13', line, re.I)][-65:]
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open('http://127.0.0.1:8783/api/state', timeout=1) as response: ui=json.load(response)
    v['ui']={k:ui.get(k) for k in ['phase','ui_page','sequence','error']}
except Exception as exc: v['ui']={'unavailable':type(exc).__name__}
guard=Path('/home/root/aura-pan-incident-20261020/lock-status.json')
if guard.exists():
    s=json.loads(guard.read_text()); v['motion_quarantine']=dict(record=s,
        same_boot=s.get('boot_id')==v['boot_id'], process_exists=Path('/proc/%s'%s.get('pid')).exists())
v['artifacts']={'active-launcher.py':dict(base64=base64.b64encode(launcher.read_bytes()).decode(),
    sha256=hashlib.sha256(launcher.read_bytes()).hexdigest())}
print(json.dumps(v), flush=True)
