"""Build a separately owned stream release without changing the r4 app source."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
STREAM = ROOT/'stream_v2'
OPS = '/home/root/aura-native-live-20261024/ops/be72669aa53de735'
RELEASE = 'pan-follow-shadow-stream-v2'
names = ['motion_stream.py', 'camera_wrapper.py', 'shadow_follow.py', 'run_shadow_stream.py', 'config.json']
pins = {name: hashlib.sha256((STREAM/name).read_bytes()).hexdigest() for name in names}
entry = (ROOT/'shadow_runtime/native_entry_shadow.py').read_text()
entry = entry.replace("ops_root / 'pan-follow-shadow-live'", "ops_root / '"+RELEASE+"'")
entry = entry.replace("motion_wrapper = aura / 'tools/board_camera_motion.py'", "motion_wrapper = shadow_root / 'camera_wrapper.py'")
entry = re.sub(r'SHADOW_PINS = \{.*?\n\}', 'SHADOW_PINS = '+repr(pins), entry, count=1, flags=re.S)
assert "'pan-follow-shadow-live'" not in entry
assert 'original(str(original_entry)' in entry and "native_pin" in entry and "meta['candidate_ui_sha256']" in entry
compile(entry, 'native_entry_stream.py', 'exec')
(STREAM/'native_entry_stream.py').write_text(entry)
files = [('stream_v2/native_entry_stream.py', OPS+'/native_entry_pan_stream_v2.py')]
files += [('stream_v2/'+name, OPS+'/'+RELEASE+'/'+name) for name in names]
rows = []
for name, dest in files:
    data = (ROOT/name).read_bytes()
    rows.append({'source':str(ROOT/name),'source_rel':name,'destination':dest,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
manifest = {'schema':'aura-pan-follow-shadow-transfer-1','ops_root':OPS,'release':RELEASE,'files':rows}
manifest['manifest_sha256'] = hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(ROOT/'stream-v2-bundle-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'release':RELEASE,'manifest_sha256':manifest['manifest_sha256'],'files':len(rows),'bytes':sum(x['bytes'] for x in rows)}))
