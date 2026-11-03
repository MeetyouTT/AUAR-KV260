"""Confirm the dedicated shadow staging targets do not already exist."""
import json
from pathlib import Path
import subprocess

ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
release=ops/'pan-follow-shadow-live'
dropin=Path('/etc/systemd/system/aura-camera-ui.service.d/zzzzzzzzzzzz-aura-pan-follow-shadow.conf')
entry=ops/'native_entry_pan_shadow.py'
assert ops.is_dir()
assert not release.exists() and not entry.exists() and not dropin.exists()
props=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Restart','-p','KillMode','-p','SendSIGKILL'],text=True)
print(json.dumps({'ops_root_exists':True,'release_path_available':True,
 'entry_path_available':True,'dropin_path_available':True,
 'camera_unit':dict(line.split('=',1) for line in props.splitlines() if '=' in line)},sort_keys=True))
