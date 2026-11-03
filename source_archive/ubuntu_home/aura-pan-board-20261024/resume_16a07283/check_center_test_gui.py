import hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');s=json.loads((R/'state.json').read_text());G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Result'],text=True).strip()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
try:
 u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health');cfg=json.loads((G/'startup/config.json').read_text())
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 ready=m['state']=='READY' and not m['automatic_following'] and m.get('readback')==s['pre_follow_readback']
 if ready:
  assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
  assert sha(A/'tools/face_pan_controls.py')=='9374b8d37e60c967aa3b248f9540ce511aa7d5b0b8cc2e56e2d88ac0451adb55'
  mc=json.loads((A/'config/pan_manual.local.json').read_text());fc=json.loads((A/'config/pan_face.local.json').read_text())
  assert mc['automatic_following_enabled'] is True and mc['left_button_pulse_sign']==-1 and fc['duration_s']==20
  assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced'] and m['left_sign']==-1
  s.update(phase='FACE_CENTER_TEST_UI_READY_OUTPUT_STOPPED',current_gui_pid=int(unit.split('MainPID=')[1].splitlines()[0]))
  (R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
 report={'status':'FACE_CENTER_TEST_UI_READY_OUTPUT_STOPPED' if ready else 'WAITING_GUI_STARTUP','unit':unit,'manual':m,
  'camera_pid':h['pid'],'identity_ready':h['identity']['ready'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
  'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},'motor_commands_sent':0}
except (OSError,ValueError,KeyError) as error:report={'status':'WAITING_GUI_STARTUP','unit':unit,'reason':type(error).__name__}
print(json.dumps(report))
