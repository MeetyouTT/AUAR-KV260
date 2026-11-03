import hashlib,json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');G=R/'gui-reference-bound-v2';A=G/'runtime/aura'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
startup=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==h for n,h in startup['component_sha256'].items())
cfg=json.loads((A/'config/pan_face.local.json').read_text());assert cfg['manifest_sha256']=='524ad777aec14dc2d853708412bcef4f75e1e6937d528674cc154b361b8ce76d' and cfg['duration_s']==0
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
with o.open(base+'/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(q,timeout=3) as f:reply=json.load(f)
assert reply.get('ok'),reply
time.sleep(1)
with o.open(base+'/api/state',timeout=3) as f:after=json.load(f)
s=json.loads((R/'state.json').read_text());s.update(phase='V11_EDGE_TRIGGERED_RECENTER_ENABLED',automatic_following=after['manual_pan']['automatic_following'])
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'reply':reply,'manual':after['manual_pan'],
 'target_center_ratio':.5,'center_tolerance_ratio':.03,'maximum_speed_us_s':30,'duration_s':0}))
