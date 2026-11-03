"""Explicit ABI-compatible rollback retaining the exact new owner's history."""
import hashlib,json,runpy,sys
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
ROOT=OPS/'pan-face-edge-v5/native-operator-v1'
settings=json.loads((ROOT/'settings.json').read_text());meta=json.loads((OPS/'meta.json').read_text())
sys.path.insert(0,str(Path(meta['candidate_root'])/'aura'))
from board.vision import native_startup as ns
original=ns.preflight
def preflight(config,**kwargs):
    native=config['native_execution'];pin=native['seed'];raw=Path(pin['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==pin['sha256']
    unit=json.loads(raw)['source_unit_sha256']
    assert unit in (settings['unit_sha256'],settings['predecessor_unit_sha256'])
    assert native['library_sha256']==settings['old_library_sha256']
    native['source_unit_sha256']=unit
    try:return original(config,**kwargs)
    finally:native['source_unit_sha256']=settings['predecessor_unit_sha256']
ns.preflight=preflight
entry=OPS/'native_entry_pan_face_v5.py';sys.argv=[str(entry)];runpy.run_path(str(entry),run_name='__main__')
