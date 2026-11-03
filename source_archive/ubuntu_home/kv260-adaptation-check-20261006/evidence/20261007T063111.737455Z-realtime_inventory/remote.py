"""Read-only inventory before replacing the explicitly owned camera preview."""
import hashlib
import json
import subprocess
from pathlib import Path

root = Path('/home/root/aura-camera-check-20261006')
pid = int((root / 'preview.pid').read_text())
command = (Path('/proc') / str(pid) / 'cmdline').read_bytes()
assert b'/home/root/aura-camera-check-20261006/fullscreen_preview.py' in command
models = Path('/home/root/aura-adaptation-20261006/identity')
files = {}
for name in ['face_compat.py', 'yunet_2022mar.onnx']:
    path = models / name
    if path.is_file():
        files[name] = {'bytes': path.stat().st_size,
                       'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
import cv2
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo
Gst.init(None)
factories = {name: Gst.ElementFactory.find(name) is not None for name in
             ['v4l2src', 'appsink', 'appsrc', 'videoconvert', 'ximagesink']}
app = subprocess.run(['xmutil', 'listapps'], capture_output=True, text=True, timeout=20)
display = subprocess.run(['xset', '-display', ':0', 'q'], capture_output=True, text=True, timeout=10)
print(json.dumps({'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'preview_pid': pid, 'preview_cmd': command.decode().replace('\u0000', ' '),
                  'preview_status': json.loads((root / 'fullscreen-status.json').read_text()),
                  'opencv': cv2.__version__, 'factories': factories, 'model_files': files,
                  'identity_entries': sorted(p.name for p in models.iterdir()),
                  'xmutil_rc': app.returncode, 'xmutil_listapps': app.stdout,
                  'display_rc': display.returncode, 'display': display.stdout,
                  'camera_opened': False, 'fpga_modified': False}, indent=2))
assert all(factories.values()) and app.returncode == 0 and display.returncode == 0
