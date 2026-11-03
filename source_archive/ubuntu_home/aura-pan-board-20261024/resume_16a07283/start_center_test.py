import hashlib,json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r4')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();s=json.loads((R/'state.json').read_text())
assert s['phase']=='FACE_CENTER_TEST_UI_READY_OUTPUT_STOPPED' and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
assert sha(P/'deployment-manifest.json')=='f48911f46064f711ec26d2b5e18327cd42fa1b7664c40dfcc5ddeff4e35f206c'
assert all(sha(row['destination'])==row['sha256'] for row in json.loads((P/'deployment-manifest.json').read_text())['files'])
c=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==h for n,h in c['component_sha256'].items())
fc=json.loads((A/'config/pan_face.local.json').read_text());assert fc['release_root']==str(P) and fc['duration_s']==20
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert m['left_sign']==-1 and h['pid']==13537 and not h['dpu_schedule']['owner_fenced']
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
p=get(8790,'/v1/motion/face/observation')
if p.get('state')!='READY':
 print(json.dumps({'status':'WAITING_FOR_CONFIRMED_FACE_NO_MOTION','face_state':p.get('state'),'motor_commands_sent':0}));raise SystemExit(0)
request=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(request,timeout=4) as r:reply=json.load(r)
assert reply.get('ok'),reply
time.sleep(.4);after=get(8783,'/api/state')['manual_pan']
assert after['automatic_following']
s.update(phase='FACE_CENTER_UI_TEST_RUNNING',center_test_started_mono_ms=int(time.monotonic()*1000),
 center_test_report=(after.get('face_follow') or {}).get('report'),automatic_following=True)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'duration_s':20,'reference':'face_center_for_both_lines','gui_stop_button_active':True,
 'center_reference_us':1420,'center_command_applied':False,'reply':reply,'manual':after}))
