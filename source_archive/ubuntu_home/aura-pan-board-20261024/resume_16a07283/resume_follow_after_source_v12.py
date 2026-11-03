import json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
S=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face-source-v12/stage-state.json')
source=json.loads(S.read_text());assert source['phase']=='CAMERA_READY_WITH_MOTION_FEED'
s=json.loads((R/'state.json').read_text());assert s['boot']==source['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
h=get(8790,'/health');m=get(8783,'/api/state')['manual_pan']
assert h['pid']==source['camera_pid'] and not h['dpu_schedule']['owner_fenced']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0 and m['left_sign']==-1
request=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(request,timeout=3) as r:reply=json.load(r)
assert reply.get('ok'),reply
time.sleep(.7);after=get(8783,'/api/state')['manual_pan'];assert after['automatic_following']
s.update(phase='CONTINUOUS_R7_SOURCE_V12_RUNNING',current_camera_pid=h['pid'],face_source_version=12,automatic_following=True,
 source_v12_restart_mono_ms=int(time.monotonic()*1000),source_v12_checkpoint_sha256=source['checkpoint_sha256'])
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'manual':after,'camera_pid':h['pid'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},'identity_ready':h['identity']['ready'],'center_command_applied':False}))
