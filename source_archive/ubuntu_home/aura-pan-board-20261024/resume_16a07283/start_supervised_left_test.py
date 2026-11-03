import hashlib,json,os,shutil,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r5')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();s=json.loads((R/'state.json').read_text())
assert s['phase']=='LEFT_FRAME_RIGHT_POINT_TEST_STOPPED_FEEDBACK_PENDING' and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
assert sha(P/'deployment-manifest.json')=='6421f774d513b35c82a71328f3d5a133f37f57db720a33b9574266cb9a731b4a'
assert all(sha(row['destination'])==row['sha256'] for row in json.loads((P/'deployment-manifest.json').read_text())['files'])
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0 and m['left_sign']==-1
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced']
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
c=G/'startup/config.json';cfg=json.loads(c.read_text());assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
q=A/'config/pan_face.local.json';face=json.loads(q.read_text());assert face['release_root']==str(P) and face['duration_s']==20
backup=G/'before-supervised-left-window';backup.mkdir(mode=0o700);shutil.copy2(c,backup/c.name);shutil.copy2(q,backup/q.name)
face['duration_s']=90;tmp=q.with_name(q.name+'.90s');tmp.write_text(json.dumps(face,indent=2)+'\n');os.replace(tmp,q)
cfg['component_sha256']['config/pan_face.local.json']=sha(q);tmp=c.with_name(c.name+'.90s');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(tmp,c)
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
request=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with op.open(request,timeout=4) as r:reply=json.load(r)
assert reply.get('ok'),reply
time.sleep(.4);after=get(8783,'/api/state')['manual_pan'];assert after['automatic_following']
s.update(phase='SUPERVISED_LEFT_FRAME_TEST_RUNNING',supervised_test_started_mono_ms=int(time.monotonic()*1000),
 supervised_test_duration_s=90,startup_config_sha256=sha(c),automatic_following=True)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'actual_gui_following':after['automatic_following'],'duration_s':90,'gui_stop_button_active':True,
 'reference':'left_face_box_edge_right_face_center','starting_readback':m['readback'],'face_follow':after.get('face_follow')}))
