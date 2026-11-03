"""Read pinned runtime sources/configuration for a recoverable candidate merge."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
def pid(unit):
    return subprocess.run(['systemctl','show',unit,'-p','MainPID','--value'],check=True,stdout=subprocess.PIPE,text=True,timeout=5).stdout.strip()
artifacts = {}
camera = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura')
working = subprocess.run(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'],
                         check=True,stdout=subprocess.PIPE,text=True,timeout=5).stdout.strip()
avatar = Path(working).resolve()
assert str(avatar).startswith('/home/root/aura-') and avatar.name == 'aura'
for name, path in [('camera-config.json', camera/'config/board_camera_ui.json'),
                   ('ui-config.json',avatar/'config/board_avatar_gtk.json'),
                   ('ui-unit.txt',Path('/etc/systemd/system/aura-avatar-ui.service')),
                   ('camera-unit.txt',Path('/etc/systemd/system/aura-camera-ui.service')),
                   ('current-board-avatar-gtk.py',avatar/'tools/board_avatar_gtk.py'),
                   ('current-board-recording.py',avatar/'tools/board_recording.py'),
                   ('current-channel-jobs.py',avatar/'board/runtime/audio/channel_jobs.py'),
                   ('current-voice-channel.py',avatar/'board/runtime/audio/voice_channel.py')]:
    data = path.read_bytes()
    artifacts[name] = {'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
for rel in ['tools/board_avatar_worker.py','board/runtime/audio/automatic_capture.py',
            'board/runtime/audio/vad.py','board/runtime/audio/capture.py']:
    path = avatar/rel
    if path.is_file():
        data = path.read_bytes()
        artifacts['active-'+path.name] = {'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
for path in (avatar/'tests/framework').glob('test_auto*.py'):
    data = path.read_bytes()
    artifacts[path.name] = {'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=3) as response:ui=json.load(response)
print(json.dumps({'status':'READ_ONLY_RUNTIME_SOURCES','camera_pid':pid('aura-camera-ui.service'),
 'ui_pid':pid('aura-avatar-ui.service'),'ui_page':ui.get('ui_page'),'phase':ui.get('phase'),
 'playing':ui.get('playing'),'recording_state':ui.get('local_recording',{}).get('state'),
 'voice_pending':ui.get('local_transcription',{}).get('service',{}).get('pending'),
 'automatic_conversation':ui.get('automatic_conversation',{}),
 'active_avatar_root':str(avatar),
 'free_bytes':__import__('shutil').disk_usage('/home/root').free,'artifacts':artifacts}),flush=True)
