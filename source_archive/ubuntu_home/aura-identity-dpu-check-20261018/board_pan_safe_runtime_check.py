"""Resolve the actually running UI from argv; read files only, no control I/O."""
import hashlib
import json
import subprocess
from pathlib import Path

names = ['board/motion/manual.py', 'board/motion/manual_process.py',
         'board/motion/manual_vsrv.py', 'board/motion/vsrv_driver.py',
         'tools/pan_controls.py', 'tools/board_avatar_gtk.py', 'tools/libaura_pixels.so']
value = {'processes': [], 'movement_commands_sent': 0, 'files_modified': 0}
value['service'] = subprocess.check_output([
    'systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID', '-p', 'ActiveState',
    '-p', 'ActiveEnterTimestamp', '-p', 'NRestarts', '-p', 'ExecStart'], text=True)
for process in Path('/proc').iterdir():
    if not process.name.isdigit():
        continue
    try:
        args = (process/'cmdline').read_bytes().split(b'\0')
        scripts = [Path(arg.decode()) for arg in args if arg.endswith(b'/tools/board_avatar_pan.py')]
        if not scripts:
            continue
        root = scripts[0].resolve().parents[1]
        stat = (process/'stat').read_text().rsplit(')', 1)[1].split()
        value['processes'].append(dict(pid=int(process.name), ppid=int(stat[1]),
            start_ticks=int(stat[19]), runtime=str(root), hashes={
                rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in names}))
    except (OSError, UnicodeError):
        pass
value['interlock'] = json.loads(Path('/home/root/aura-pan-incident-20261020/lock-status.json').read_text())
print(json.dumps(value), flush=True)
