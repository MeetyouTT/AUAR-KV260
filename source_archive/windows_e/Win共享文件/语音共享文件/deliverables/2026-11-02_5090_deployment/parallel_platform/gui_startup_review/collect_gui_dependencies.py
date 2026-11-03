"""Hash-checked installed source/config reads for GUI constructor analysis; no imports."""
import datetime
import hashlib
import json
from pathlib import Path

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA = '07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
raw = (ROOT/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == STARTUP_SHA
startup = json.loads(raw)
AURA = Path(startup['runtime'])/'aura'
NAMES = [
    'tools/yuki_business_candidate.py', 'tools/board_business_gui.py',
    'tools/formal_yuki.py', 'tools/formal_native_yuki.py',
    'tools/production_listening.py', 'tools/production_memory_presentation.py',
    'tools/production_frontend_selection.py', 'tools/voice_first_recording.py',
    'tools/handsfree_recording.py', 'tools/barge_in_recording.py', 'tools/board_recording.py',
    'tools/gstreamer_audio.py', 'tools/gstreamer_audio_worker.py', 'tools/gstreamer_persistent_engine.py',
    'tools/production_business_ui.py', 'tools/production_output_format.py',
    'board/motion/manual_live_config.py', 'board/motion/current_reference_release.py',
    'board/motion/manual_release.py', 'board/motion/rated_range_release.py',
    'board/runtime/board_business.py', 'board/runtime/board_speaker_business.py',
    'board/runtime/audio/automatic_capture.py', 'board/runtime/audio/voice_channel.py',
    'board/runtime/audio/channel_jobs.py', 'common/board_production_bootstrap.py',
    'common/conversation_store.py', 'common/conversation_selection.py',
    'config/pan_face.local.json', 'config/pan_direction.current.json', 'config/board_ui_services.json',
]
files = {}
for name in NAMES:
    path = AURA/name
    entry = {'path': str(path), 'relative': name, 'exists': path.is_file()}
    if path.is_file():
        assert not path.is_symlink() and path.suffix in ('.py', '.json')
        raw = path.read_bytes()
        assert len(raw) <= 600000
        actual = hashlib.sha256(raw).hexdigest()
        expected = startup['component_sha256'].get(name)
        if expected is not None:
            assert actual == expected, 'Installed dependency differs: ' + name
        entry.update(sha256=actual, startup_pinned=expected is not None,
                     text=raw.decode('utf-8'), bytes=len(raw))
    files[name] = entry
print(json.dumps({'schema': 'aura-gui-dependencies-readonly-1', 'boot_id': BOOT,
    'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'startup_sha256': STARTUP_SHA,
    'files': files, 'board_mutations': False, 'project_imported': False,
    'device_opened': False, 'database_opened': False, 'motion_requested': False}, sort_keys=True))
