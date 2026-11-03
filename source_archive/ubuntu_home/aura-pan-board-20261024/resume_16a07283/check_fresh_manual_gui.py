import hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');s=json.loads((R/'state.json').read_text());G=Path(s['gui_release'])
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','NRestarts'],text=True).strip()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
try:
 u=get(8783,'/api/state');m=u['manual_pan'];r=m.get('readback') or {};h=get(8790,'/health');d=h['dpu_schedule']
 ready=m['state']=='READY' and r.get('flags')==0 and r.get('lease_left_ms')==0
 if ready:
  cfg=json.loads((G/'startup/config.json').read_text());A=G/'runtime/aura';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  assert all(sha(A/p)==digest for p,digest in cfg['component_sha256'].items())
  assert h['pid']==13537 and not d['owner_fenced'] and r['width_us']==1445 and r['ack_seq']==42 and r['epoch']==3
  assert not m['automatic_following'] and [m['minimum_us'],m['maximum_us']]==[1445,1465] and not m['history']
  s.update(phase='CURRENT_BOOT_MANUAL_READY_OUTPUT_STOPPED_FOLLOW_LOCKED',current_gui_pid=int(unit.split('MainPID=')[1].splitlines()[0]),
   automatic_following=False,physical_control_rebound=True,center_reference_us=1420,center_command_applied=False)
  (R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
 result={'status':'MANUAL_READY_OUTPUT_STOPPED_FOLLOW_LOCKED' if ready else 'WAITING_GUI_STARTUP','unit':unit,
  'manual':m,'camera_pid':h['pid'],'identity_ready':h['identity']['ready'],'primary_overruns':d['primary_period_overruns'],
  'optional_overruns':{k:d['optional'][k]['overruns'] for k in ('sface','yunet')},'preview':u['ui_runtime'].get('preview_metrics'),
  'page':u['ui_page'],'center_reference_us':1420,'center_command_applied':False,'motor_commands_sent':0}
except (OSError,ValueError,KeyError) as e:result={'status':'WAITING_GUI_STARTUP','unit':unit,'reason':type(e).__name__}
print(json.dumps(result))
