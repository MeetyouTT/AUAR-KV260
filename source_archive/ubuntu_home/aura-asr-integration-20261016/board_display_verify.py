"""Read back the inactive startup fix and its board software test output."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

release=Path('/home/root/aura-ui-startup-20261009/releases/d2e45eb7fee4fa08')
stage=Path('/home/root/aura-display-coldboot-20261017/release-d2e45eb7fee4fa08')
manifest=json.loads((release/'release_manifest.json').read_text())
files={name:hashlib.sha256((release/name).read_bytes()).hexdigest() for name in manifest['files']}
assert all(files[n]==row['sha256'] for n,row in manifest['files'].items())
unit=Path('/etc/systemd/system/aura-avatar-ui.service')
assert unit.read_bytes()==(release/'aura-avatar-ui.service').read_bytes()
pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
args=Path('/proc/%d/cmdline'%pid).read_bytes().decode().split('\0')
artifacts={}
for name,path in [('board_display_tests.log',stage/'board_display_tests.log')]:
    data=path.read_bytes()
    artifacts[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                     'base64':base64.b64encode(data).decode()}
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'installed_release':str(release),'installed_unit':unit.read_text(),'files':files,
    'supervisor_pid':pid,'active_args':args,'recovery_marker_exists':Path('/run/aura-display-startup.json').exists(),
    'artifacts':artifacts}))
