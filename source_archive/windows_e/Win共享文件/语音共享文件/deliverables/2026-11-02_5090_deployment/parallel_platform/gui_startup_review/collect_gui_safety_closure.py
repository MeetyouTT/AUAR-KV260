"""Read exact pinned startup dependencies; never import project modules or open devices."""
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
names = [
    'board/motion/vsrv_transport.py', 'board/motion/vsrv_driver.py',
    'board/motion/follow_readback.py', 'board/motion/input_freshness.py',
    'tools/follow_process_cleanup.py', 'board/runtime/device_observer.py',
    'tools/streaming_controller.py', 'tools/formal_yuki.py',
    'tools/barge_in_recording.py', 'tools/yuki_business_candidate.py',
    'board/runtime/audio/board_frontend_auto.py',
]
files = {}
for name in names:
    path = AURA/name
    assert path.is_file() and not path.is_symlink() and path.suffix == '.py', 'Source unavailable: '+name
    raw = path.read_bytes()
    assert len(raw) <= 600000
    sha = hashlib.sha256(raw).hexdigest()
    assert sha == startup['component_sha256'][name]
    files[name] = {'path':str(path),'relative':name,'text':raw.decode(),
                   'sha256':sha,'bytes':len(raw),'startup_pinned':True}
manual = json.loads((AURA/'config/pan_manual.local.json').read_bytes())
path = Path(manual['release_manifest'])
assert path.suffix == '.json' and not path.is_symlink()
raw = path.read_bytes()
assert len(raw) < 65536
assert hashlib.sha256(raw).hexdigest() == manual['release_manifest_sha256']
files['selected_manual_release.json'] = {'path':str(path),'text':raw.decode(),
    'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'manual_config_pinned':True}
assert hashlib.sha256((ROOT/'startup/config.json').read_bytes()).hexdigest() == STARTUP_SHA
print(json.dumps({'schema':'aura-gui-safety-closure-readonly-1','files':files,
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,
    'startup_sha256':STARTUP_SHA,'board_mutations':False,'database_opened':False,
    'device_opened':False,'project_imported':False,'motion_requested':False},sort_keys=True))
