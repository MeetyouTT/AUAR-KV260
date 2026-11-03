import hashlib,json,os,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
s=json.loads((R/'state.json').read_text());assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get():
 with o.open(base+'/api/state',timeout=3) as f:return json.load(f)['manual_pan']
def command(name):
 req=urllib.request.Request(base+'/api/command',data=json.dumps({'type':name}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(req,timeout=3) as f:return json.load(f)
m=get();assert m['automatic_following']
assert 'continuous-v10r8/runs/' in m['face_follow']['report']
reply=command('pan_stop');end=time.monotonic()+8
while time.monotonic()<end:
 stopped=get()
 if not stopped['automatic_following'] and stopped['state']=='READY':break
 time.sleep(.1)
assert stopped['state']=='READY' and not stopped['automatic_following'] and stopped['readback']['flags']==0 and stopped['readback']['lease_left_ms']==0,stopped
cfg=json.loads((A/'config/pan_face.local.json').read_text());p=Path(cfg['arguments']['direction-evidence'])
d=json.loads(p.read_text());assert d['boot_id']==s['boot'] and d['status']=='HUMAN_DIRECTION_CONFIRMED'
old=d['axis_camera_mirrored_control_polarity'];assert old==-1
backup=R/'direction-before-r8-human-correction.json';assert not backup.exists()
with backup.open('xb') as f:f.write(p.read_bytes())
d.update(axis_camera_mirrored_control_polarity=1,latest_closed_loop_user_feedback='转轴方向反了',
 polarity_correction_reason='User observed reverse automatic following; invert automatic control only',
 polarity_correction_mono_ms=int(time.monotonic()*1000),previous_auto_polarity=old)
t=p.with_name(p.name+'.direction-corrected');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');os.replace(t,p)
s.update(phase='R8_DIRECTION_CORRECTED_OUTPUT_STOPPED',automatic_following=False,automatic_control_polarity=1,
 direction_correction_user_feedback='转轴方向反了',current_last_command_us=stopped['readback']['width_us'])
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
assert get()['readback']==stopped['readback']
print(json.dumps({'status':s['phase'],'previous_auto_polarity':old,'new_auto_polarity':1,'manual_left_sign':stopped['left_sign'],
 'direction_evidence_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'stopped':stopped['readback'],'center_command_applied':False}))
