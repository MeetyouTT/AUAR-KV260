"""Start the existing, identified camera service after device recovery."""
import hashlib
import json
import subprocess
from pathlib import Path

root = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura')
unit = 'aura-camera-ui.service'
installed = Path('/etc/systemd/system') / unit
published = root / 'scripts/board_camera_ui' / unit
assert installed.read_bytes() == published.read_bytes(), 'Camera unit differs from owned published unit'
assert Path('/dev/video0').exists()
assert 'HD 720P Webcam' in Path('/sys/class/video4linux/video0/name').read_text()


def run(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
    return {'exit_code': p.returncode, 'output': p.stdout}


before = run(['systemctl', 'show', unit, '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID'])
actions = []
if 'ActiveState=active' not in before['output']:
    owners = run(['fuser', '/dev/video0'])
    assert owners['exit_code'] == 1 and not owners['output'].strip(), owners
    for command in [['systemctl', 'reset-failed', unit], ['systemctl', '--no-block', 'start', unit]]:
        result = run(command)
        actions.append({'args': command, **result})
        assert result['exit_code'] == 0, result
print(json.dumps({'before': before, 'actions': actions,
                  'unit_sha256': hashlib.sha256(installed.read_bytes()).hexdigest(),
                  'after': run(['systemctl', 'show', unit, '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID'])}))
