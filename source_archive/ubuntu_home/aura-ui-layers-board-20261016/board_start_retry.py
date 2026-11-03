"""Retry only the owned GUI once its old control port is free."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import socket
import subprocess
import time

stage=Path('/home/root/aura-ui-layers-20261016/update-38df07b20542959b')
manifest=json.loads((stage/'payload/manifest.json').read_text())
unit=Path('/etc/systemd/system/aura-avatar-ui.service')
assert hashlib.sha256(unit.read_bytes()).hexdigest()==manifest['files']['startup/aura-avatar-ui.service']['sha256']
assert subprocess.check_output(['systemctl','show',unit.name,'-p','MainPID','--value'],text=True).strip()=='0'
source=str(Path(manifest['runtime'])/'aura/tools/board_avatar_gtk.py').encode()
for process in Path('/proc').iterdir():
    if not process.name.isdigit():continue
    try:args=(process/'cmdline').read_bytes().split(b'\0')
    except OSError:continue
    assert source not in args,'Existing owned GUI process '+process.name
connections=[line for line in Path('/proc/net/tcp').read_text().splitlines() if ':224F ' in line.upper()]
with socket.socket() as probe:
    probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    probe.bind(('127.0.0.1',8783))
subprocess.run(['systemctl','reset-failed',unit.name],check=True)
subprocess.run(['systemctl','--no-block','start',unit.name],check=True)
result={'status':'RETRY_START_REQUESTED','old_port_records':connections}
print(json.dumps(result))
