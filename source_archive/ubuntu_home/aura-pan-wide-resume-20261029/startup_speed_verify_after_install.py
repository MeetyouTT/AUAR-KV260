import hashlib
import json
import subprocess
from pathlib import Path


def run(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=20)
    assert result.returncode == 0, (args, result.stdout[-1200:])
    return result.stdout


boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == '605eaf50-c66a-4559-bfc9-5ae177e0f305', boot
unit_text = run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'ActiveState',
                 '-p', 'MainPID', '-p', 'ExecStart', '-p', 'DropInPaths', '-p', 'UnitFileState'])
unit = dict(line.split('=', 1) for line in unit_text.splitlines() if '=' in line)
dropin = '/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-aura-avatar-startup-speed-20261029.conf'
root = Path('/home/root/aura-avatar-startup-speed-20261029')
expected = {
    'launcher.py': '5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03',
    'config.json': '12af11467b3ca0c0a1e6b57ac203e887d658a9799a159e39dfa90dbff60037d4',
    'dropin.conf': '48b46dace7d5d280c06bf2fe1559b4040366ee8770c611b707b028452704295f',
}
digests = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in expected}
assert digests == expected, digests
assert unit.get('ActiveState') == 'active' and unit.get('MainPID') == '1296', unit
assert unit.get('UnitFileState') == 'enabled', unit
assert str(root/'launcher.py') in unit.get('ExecStart', ''), unit
dropins = unit.get('DropInPaths', '').split()
assert dropins and dropins[-1] == dropin, dropins[-1:] 
runtime = Path('/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime')
launch = json.loads((runtime/'launch.json').read_text())
assert launch['supervisor_pid'] == 1296
gui = Path('/proc')/str(launch['pid'])
assert gui.exists() and b'board_avatar_pan.py' in (gui/'cmdline').read_bytes()
print(json.dumps({'boot_id': boot, 'service': unit, 'dropin_is_last': True,
                  'files': digests, 'current_gui_pid': launch['pid'],
                  'current_gui_supervisor_pid': launch['supervisor_pid'],
                  'service_or_board_restart_requested': False}))
