from pathlib import Path
import json
import subprocess

root = Path('/home/root/aura-yuki-validation-20261030')
assert root.resolve() == root and not root.is_symlink()
with (root / 'launcher.log').open('a') as log:
    process = subprocess.Popen(['python3', str(root / 'probe_build/board_build.py')],
                               stdin=subprocess.DEVNULL, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True,
                               close_fds=True)
(root / 'build-pid.json').write_text(json.dumps({'pid': process.pid}))
print(json.dumps({'validation_build_pid': process.pid, 'root': str(root)}))
