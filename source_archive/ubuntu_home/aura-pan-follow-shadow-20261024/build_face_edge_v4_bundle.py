import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT/'face_edge_v4';OPS='/home/root/aura-native-live-20261024/ops/be72669aa53de735';RELEASE='pan-face-edge-v4'
names=['face_edge_control.py','face_source.py','face_flow.py','motion_stream.py','camera_wrapper.py','run_face_shadow.py','face_motion.py','run_face_motion.py','face_pan_controls.py','config.json']
pins={n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in names}
entry=(ROOT/'shadow_runtime/native_entry_shadow.py').read_text().replace("ops_root / 'pan-follow-shadow-live'","ops_root / '"+RELEASE+"'").replace("motion_wrapper = aura / 'tools/board_camera_motion.py'","motion_wrapper = shadow_root / 'camera_wrapper.py'")
entry=re.sub(r'SHADOW_PINS = \{.*?\n\}','SHADOW_PINS = '+repr(pins),entry,count=1,flags=re.S);compile(entry,'native_entry_face.py','exec');(D/'native_entry_face.py').write_text(entry)
files=[('face_edge_v4/native_entry_face.py',OPS+'/native_entry_pan_face_v4.py')]+[('face_edge_v4/'+n,OPS+'/'+RELEASE+'/'+n) for n in names]
rows=[]
for src,dest in files:
 raw=(ROOT/src).read_bytes();rows.append({'source':str(ROOT/src),'source_rel':src,'destination':dest,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
m={'schema':'aura-pan-follow-shadow-transfer-1','ops_root':OPS,'release':RELEASE,'files':rows};m['manifest_sha256']=hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(ROOT/'face-edge-v4-bundle-manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({'release':RELEASE,'files':len(rows),'manifest_sha256':m['manifest_sha256']}))
