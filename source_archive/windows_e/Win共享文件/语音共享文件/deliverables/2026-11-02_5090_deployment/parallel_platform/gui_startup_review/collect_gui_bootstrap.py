"""Read installed GUI startup sources and public configuration; never import them."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
BUSINESS = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA = '07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT

def read(path, cap=600000):
    p = Path(path)
    result = {'path': str(p), 'exists': p.exists(), 'symlink': p.is_symlink()}
    if p.is_file() and not p.is_symlink():
        assert p.suffix not in ('.db', '.sqlite', '.sqlite3')
        raw = p.read_bytes()
        result.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        if len(raw) <= cap and b'\0' not in raw[:4096]:
            result['text'] = raw.decode('utf-8', 'replace')
    return result

def run(argv):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=8)
    return {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

raw = (BUSINESS/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == STARTUP_SHA
startup = json.loads(raw)
runtime = Path(startup['runtime'])
aura = runtime/'aura'
names = ['tools/board_avatar_pan.py', 'tools/board_avatar_gtk.py', 'tools/face_pan_controls.py',
         'tools/pan_controls.py', 'tools/production_board_business_gui.py',
         'board/runtime/audio/face_gallery_readback.py',
         'board/motion/manual_process.py', 'board/motion/manual_vsrv.py',
         'board/motion/manual.py', 'board/motion/service.py', 'board/motion/follow.py',
         'config/board_avatar_gtk.json', 'config/pan_manual.local.json',
         'config/pan_face_follow.local.json', 'config/face_gallery_readback.local.json',
         'config/board_business.local.json', 'config/model_inference.local.json']
files = {str(BUSINESS/'startup/launcher.py'): read(BUSINESS/'startup/launcher.py')}
for name in names:
    files[str(aura/name)] = read(aura/name)
files[str(BUSINESS/'startup/config.json')] = read(BUSINESS/'startup/config.json')
camera_proc = Path('/proc/1333')
camera = {'pid': 1333, 'birth_ticks': int((camera_proc/'stat').read_text().rsplit(')',1)[1].split()[19]),
          'command_sha256': hashlib.sha256((camera_proc/'cmdline').read_bytes()).hexdigest()}
assert camera['birth_ticks'] == 2359
assert camera['command_sha256'] == 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
result = {'schema': 'aura-gui-startup-readonly-1', 'boot_id': BOOT,
          'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'startup_sha256': STARTUP_SHA, 'runtime': str(runtime), 'files': files,
          'relevant_components': {p: s for p, s in startup['component_sha256'].items()
               if re.search(r'pan|business|production|handsfree|inference|listening|audio|capture', p)},
          'config_inventory': sorted(p.name for p in (aura/'config').iterdir() if p.is_file()),
          'gui_unit': run(['systemctl', 'show', 'aura-avatar-ui.service',
              '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,ExecStart,WorkingDirectory,Environment,Restart']),
          'camera_unit': run(['systemctl', 'show', 'aura-camera-ui.service', '--property=MainPID,ActiveState,Job']),
          'camera_owner': camera,
          'listening_preference': json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()),
          'firmware_name': Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
          'vart': Path('/etc/vart.conf').read_text(),
          'audio_cards_metadata': Path('/proc/asound/cards').read_text(),
          'board_mutations': False, 'device_opened': False, 'database_opened': False,
          'project_imported': False, 'motion_requested': False}
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
