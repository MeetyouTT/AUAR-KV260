"""Pinned native camera launch; never automatically replace uncertain owners."""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import sys
import time

root=Path(__file__).resolve().parent
meta=json.loads((root/'meta.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot != meta['source_boot'],'The old protection domain cannot be unlocked in place'
config=json.loads(Path(meta['candidate_config']).read_text())
checkpoint=Path(config['native_execution']['checkpoint_output'])
if checkpoint.exists():
    assert not checkpoint.is_symlink() and checkpoint.stat().st_uid==os.geteuid()
    raw=checkpoint.read_bytes();assert len(raw)<=262144
    previous=json.loads(raw);assert previous['schema']=='aura-native-protection-checkpoint-2'
    config['native_execution']['seed']={'path':str(checkpoint),'sha256':hashlib.sha256(raw).hexdigest()}
entry=Path(meta['candidate_root'])/'aura/board/vision/ui_camera_service.py'
assert hashlib.sha256(entry.read_bytes()).hexdigest()==meta['candidate_ui_sha256']
run=root/('native-run-'+boot+'-'+str(os.getpid()))
run.mkdir(mode=0o700)
config_path=run/'config.json';config_path.write_text(json.dumps(config,indent=2)+'\n')
sys.path.insert(0,str(Path(meta['candidate_root'])/'aura'))
sys.setswitchinterval(.001)
sys.argv=[str(entry),'--config',str(config_path)]
try:
    runpy.run_path(str(entry),run_name='__main__')
finally:
    binding=sys.modules.get('board.vision.native_binding')
    retained=getattr(binding,'_RETAINED',{}) if binding else {}
    if retained:
        # Keep the process, lock and all native references alive. Neither
        # systemd Restart nor an outer timeout may create a replacement owner.
        (run/'UNSAFE_OWNER_RETAINED.json').write_text(json.dumps({'boot':boot,'pid':os.getpid(),
            'scope':'unconfirmed native completion or lifecycle; automatic replacement forbidden'})+'\n')
        def hold(*_):pass
        signal.signal(signal.SIGTERM,hold);signal.signal(signal.SIGINT,hold)
        while True:signal.pause()
