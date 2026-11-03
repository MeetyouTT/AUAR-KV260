"""Read camera identity and deployed files before a scoped hotplug fix."""
import base64
import hashlib
import json
import subprocess
from pathlib import Path

root = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura')
paths = [root/'board/vision/ui_camera_service.py', root/'config/board_camera_ui.json',
         root/'scripts/board_camera_ui/aura-camera-ui.service',
         Path('/etc/systemd/system/aura-camera-ui.service'),
         Path('/lib/udev/rules.d/60-persistent-v4l.rules')]
files = {}
for p in paths:
    if p.is_file():
        data = p.read_bytes()
        files[str(p)] = {'sha256': hashlib.sha256(data).hexdigest(), 'base64': base64.b64encode(data).decode()}
videos = []
for p in Path('/sys/class/video4linux').glob('video*'):
    entry = {'node': p.name, 'name': (p/'name').read_text().strip(), 'index': (p/'index').read_text().strip()}
    for parent in (p/'device').resolve().parents:
        if (parent/'idVendor').exists():
            entry['usb'] = {'path': parent.name, **{n: (parent/n).read_text().strip() for n in ['idVendor','idProduct','serial','product']}}
            break
    videos.append(entry)
links = {str(p): str(p.resolve()) for base in ['by-id','by-path'] for p in Path('/dev/v4l',base).glob('*')}
units = subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True)
print(json.dumps({'files': files, 'videos': videos, 'links': links, 'service': units,
                  'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
