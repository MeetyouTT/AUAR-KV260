"""Compare selected readback metadata and extra constructor sources, without databases."""
import datetime
import hashlib
import json
import os
from pathlib import Path

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA = '07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
raw = (ROOT/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == STARTUP_SHA
startup = json.loads(raw); AURA = Path(startup['runtime'])/'aura'
config = json.loads((AURA/'config/board_avatar_gtk.json').read_bytes())
spec = config['board_business']['face_readback']

def binding(path):
    path = Path(path)
    assert path.suffix == '.json' and not path.is_symlink()
    raw = path.read_bytes(); assert len(raw) < 65536
    value = json.loads(raw)
    issues = []
    for name, expected in value['source_sha256'].items():
        source = Path(name)
        assert source.suffix not in ('.db', '.sqlite', '.sqlite3') and not source.is_symlink()
        assert source.stat().st_size <= 64000000
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            issues.append(str(source))
    camera = Path('/proc/1333')
    actual_cmd = hashlib.sha256((camera/'cmdline').read_bytes()).hexdigest()
    actual_birth = (camera/'stat').read_text().rsplit(')',1)[1].split()[19]
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
            'board_boot_id': value['board_boot_id'], 'camera_pid': value['camera_pid'],
            'camera_start_ticks': value['camera_start_ticks'], 'camera_cmdline_sha256': value['camera_cmdline_sha256'],
            'source_files': len(value['source_sha256']), 'source_issues': issues,
            'matches_current_boot': value['board_boot_id'] == BOOT,
            'matches_actual_camera_identity': value['camera_pid'] == 1333 and value['camera_start_ticks'] == actual_birth and value['camera_cmdline_sha256'] == actual_cmd,
            'actual_camera_birth': actual_birth, 'actual_command_sha256': actual_cmd,
            'private_database_opened': False}

names = ['tools/realtime_audio.py', 'board/runtime/board_dialogue_client.py',
         'common/board_timeline_clock.py', 'board/runtime/audio/board_asr.py',
         'board/runtime/audio/board_frontend_process.py', 'board/runtime/audio/board_frontend_capture_process.py',
         'board/runtime/audio/board_capture.py', 'board/runtime/audio/board_speaker_onnx.py',
         'board/interaction/ui_services.py', 'common/handsfree_settings.py',
         'tools/board_avatar_worker.py', 'tools/native_yuki.py',
         'common/board_memory.py']
files = {}
for name in names:
    path = AURA/name; entry = {'path': str(path), 'relative': name, 'exists': path.is_file()}
    if path.is_file():
        assert not path.is_symlink() and path.suffix == '.py'
        raw = path.read_bytes(); assert len(raw) <= 600000
        expected = startup['component_sha256'].get(name)
        actual = hashlib.sha256(raw).hexdigest()
        if expected is not None: assert actual == expected
        entry.update(sha256=actual, startup_pinned=expected is not None, text=raw.decode('utf-8'), bytes=len(raw))
    files[name] = entry
selected = binding(spec['path']); local = binding(AURA/'config/face_gallery_readback.local.json')
private_root = Path(config['board_business']['private_root'])
result = {'schema': 'aura-gui-selected-context-readonly-1', 'boot_id': BOOT,
          'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'startup_sha256': STARTUP_SHA, 'selected_binding': selected, 'local_component_binding': local,
          'selected_metadata_hash_matches_config': selected['sha256'] == spec['sha256'],
          'selected_binding_is_local_component': Path(spec['path']) == AURA/'config/face_gallery_readback.local.json',
          'files': files, 'private_root_metadata': {'owner_uid': private_root.stat().st_uid,
              'mode': oct(private_root.stat().st_mode & 0o777), 'is_symlink': private_root.is_symlink()},
          'board_mutations': False, 'project_imported': False, 'database_opened': False,
          'device_opened': False, 'motion_requested': False}
print(json.dumps(result, sort_keys=True))
