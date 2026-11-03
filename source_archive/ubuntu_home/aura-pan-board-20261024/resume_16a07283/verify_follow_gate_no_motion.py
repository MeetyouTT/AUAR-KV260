"""Pinned disabled follow must fail before closing the manual owner."""
import hashlib,json,time,urllib.error,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_BOOT_MANUAL_READY_OUTPUT_STOPPED_FOLLOW_LOCKED'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
cfg=json.loads((G/'startup/config.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
manual_cfg=json.loads((A/'config/pan_manual.local.json').read_text());assert manual_cfg['automatic_following_enabled'] is False
assert sha(A/'tools/face_pan_controls.py')=='8b4ce76a2e8a148bb2344c803497c2518e7d5b639b6ca42c5a20908b2e68f2e4'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));address='http://127.0.0.1:8783'
def state():
 with o.open(address+'/api/state',timeout=3) as r:return json.load(r)['manual_pan']
before=state();assert before['state']=='READY' and not before['automatic_following']
request=urllib.request.Request(address+'/api/command',data=json.dumps({'type':'pan_face_follow'}).encode(),headers={'Content-Type':'application/json','Origin':address})
try:
 with o.open(request,timeout=4) as r:reply=json.load(r)
except urllib.error.HTTPError as error:reply=json.load(error)
assert reply.get('ok') is not True and reply.get('error')=='人脸随动尚未开放，请先完成方向确认',reply
time.sleep(.3);after=state()
assert after['state']=='READY' and not after['automatic_following'] and before['backend_pid']==after['backend_pid']
assert before['readback']==after['readback'] and after['readback']['flags']==0 and after['readback']['lease_left_ms']==0
print(json.dumps({'status':'LIVE_FOLLOW_GATE_REJECTION_PASS','reply':reply,'backend_pid_unchanged':True,'readback_unchanged':True,
 'manual_state':after['state'],'readback':after['readback'],'automatic_following':False,'physical_ARM':0,'physical_COMMIT':0,'MMIO_opened_by_probe':False}))
