"""Apply the user's face-center rule on both lines; no actuator commands."""
import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'continuous-v10r5';OLD=F/'continuous-v10r4';E=F/'zone-editor-v8/face_zone_editor.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='6421f774d513b35c82a71328f3d5a133f37f57db720a33b9574266cb9a731b4a'
assert sha(E)=='b2aecb8d3727f78de6a2bf58deab01d82623097ae0b76e91da7dff65429306d3'
s=json.loads((R/'state.json').read_text());assert s['phase']=='FACE_CENTER_TEST_STOPPED_FEEDBACK_PENDING'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
pm=json.loads((P/'deployment-manifest.json').read_text())
for row in pm['files']:
 dest=Path(row['destination']);name=dest.relative_to(P);src=OLD/name
 if not dest.exists():
  assert sha(src)==row['sha256'];dest.parent.mkdir(exist_ok=True,parents=True)
  with dest.open('xb') as out:out.write(src.read_bytes())
 assert sha(dest)==row['sha256']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
m=get(8783,'/api/state')['manual_pan'];h=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced']
c=G/'startup/config.json';cfg=json.loads(c.read_text());assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
assert json.loads((A/'config/pan_manual.local.json').read_text())['automatic_following_enabled'] is True
backup=G/'before-left-frame-v5';backup.mkdir(mode=0o700)
q=A/'config/pan_face.local.json';before_q=q.read_bytes();before_c=c.read_bytes();shutil.copy2(q,backup/q.name);shutil.copy2(c,backup/c.name)
face=json.loads(before_q);assert face['release_root']==str(OLD)
face.update(release_root=str(P),manifest_sha256=sha(P/'deployment-manifest.json'),mode='continuous_face_zone',duration_s=20)
face['stopped_readback_predecessors']=[{'root':str(OLD),'sha256':'f48911f46064f711ec26d2b5e18327cd42fa1b7664c40dfcc5ddeff4e35f206c'}]+face.get('stopped_readback_predecessors',[])
assert q.read_bytes()==before_q;tmp=q.with_name(q.name+'.center-v4');tmp.write_text(json.dumps(face,indent=2)+'\n');os.replace(tmp,q)
cfg['component_sha256']['config/pan_face.local.json']=sha(q)
assert c.read_bytes()==before_c;tmp=c.with_name(c.name+'.center-v4');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(tmp,c)
env=dict(os.environ,PYTHONPATH=str(A),PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-B',str(G/'startup/launcher.py'),'--config',str(c),'--preflight'],env=env,capture_output=True,text=True,timeout=25)
assert p.returncode==0,p.stderr[-800:]
status_path=R/'face-zone-display-status.json';old_tick=json.loads(status_path.read_text()).get('updated_mono_ms',0) if status_path.exists() else 0
subprocess.run(['systemctl','stop','aura-face-zone-editor.service'],check=True,capture_output=True,timeout=10)
subprocess.run(['systemd-run','--quiet','--collect','--unit=aura-face-zone-editor','--property=Restart=no','/usr/bin/python3','-B',str(E),'--settings',str(R/'face-zone-settings.json')],check=True,capture_output=True,timeout=5)
end=time.monotonic()+6;display=None
while time.monotonic()<end:
 try:
  display=json.loads(status_path.read_text())
  if display.get('updated_mono_ms',0)>old_tick:break
 except (OSError,ValueError):pass
 time.sleep(.1)
assert display and display.get('updated_mono_ms',0)>old_tick
settings=json.loads((R/'face-zone-settings.json').read_text());assert settings['left_camera_ratio']==.1 and settings['right_ratio']==.7158253629442671
assert settings['left_reference']=='face_box_left_edge' and settings['right_reference']=='face_center'
assert get(8783,'/api/state')['manual_pan']['readback']==m['readback']
s.update(phase='LEFT_FACE_FRAME_RIGHT_CENTER_STAGED_OUTPUT_STOPPED',control_reference='left_face_box_edge_right_face_center',zone_editor_version=8,
 startup_config_sha256=sha(c),physical_consumer_root=str(P),physical_consumer_sha256=sha(P/'deployment-manifest.json'),
 latest_user_boundary_instruction='左侧人脸框左沿触线，右侧人脸中心点越线',automatic_following=False,boundary_live_diagnostics=str(status_path))
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'reference':'left_face_box_edge_right_face_center','line_positions_unchanged':True,
 'gui_pins':len(cfg['component_sha256']),'physical_files':len(pm['files']),'display':display,'readback':m['readback'],
 'camera_pid':h['pid'],'gui_restarted':False,'motor_commands_sent':0,'center_command_applied':False}))
