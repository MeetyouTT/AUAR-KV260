import hashlib,json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');G=R/'gui-reference-bound-v2';A=G/'runtime/aura'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
cfg=json.loads((G/'startup/config.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
face=json.loads((A/'config/pan_face.local.json').read_text());assert face['duration_s']==30 and face['mode']=='continuous_face_zone'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
with o.open(base+'/api/state',timeout=3) as f:before=json.load(f)
m=before['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(q,timeout=3) as f:reply=json.load(f)
assert reply.get('ok'),reply
time.sleep(1)
with o.open(base+'/api/state',timeout=3) as f:after=json.load(f)
s=json.loads((R/'state.json').read_text());s.update(phase='CURRENT_BOOT_ATTENDED_FACE_WINDOW_RUNNING',automatic_following=after['manual_pan']['automatic_following'])
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'start_reply':reply,'before_readback':m['readback'],
 'after_manual':after['manual_pan'],'duration_s':30,'left_camera_ratio':.1,'right_camera_ratio':.8064720153808593,'target_kind':'face'}))
