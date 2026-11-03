"""Read-only check: active application and advancing existing camera preview."""
import json
import subprocess
import time
from pathlib import Path

root = Path('/home/root/aura-camera-check-20261006')
pid = int((root / 'preview.pid').read_text())
command = (Path('/proc') / str(pid) / 'cmdline').read_bytes()
assert b'/home/root/aura-camera-check-20261006/fullscreen_preview.py' in command
before = json.loads((root / 'fullscreen-status.json').read_text())
time.sleep(2)
after = json.loads((root / 'fullscreen-status.json').read_text())
p = subprocess.run(['xmutil', 'listapps'], stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, text=True, timeout=20)
result = {
    'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'camera_preview_pid': pid, 'before': before, 'after': after,
    'preview_advancing': after['frames'] > before['frames'],
    'xmutil_rc': p.returncode, 'xmutil_listapps': p.stdout,
    'camera_opened_by_probe': False, 'fpga_modified': False,
}
print(json.dumps(result, indent=2))
assert result['preview_advancing'] and not after['error']
assert p.returncode == 0
