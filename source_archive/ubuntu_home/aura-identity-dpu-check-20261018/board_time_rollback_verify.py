"""Verify the restored running version and existing camera/voice status."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-ui-time-rollback-20261021/before-2559')
old=json.loads((root/'result.json').read_text());assert old['status']=='FILES_ROLLED_BACK_WAITING_DISPLAY_RESTART'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==old['boot_id']
env=dict(os.environ,DISPLAY=':0')
def cmd(args):return subprocess.check_output(args,env=env,stderr=subprocess.STDOUT,text=True,timeout=6)
def api(port,path='/api/state'):
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:'+str(port)+path,timeout=1) as response:return json.load(response)
deadline=time.monotonic()+20;state={};error=''
while time.monotonic()<deadline:
 try:
  state=api(8783)
  if state.get('backend')=='gtk3-gstreamer' and cmd(['systemctl','is-active','aura-avatar-ui.service']).strip()=='active':break
 except Exception as exc:error=str(exc)
 time.sleep(.5)
else:raise RuntimeError('Restored UI readiness pending: '+error)
v={'status':'RESTORED_VERSION_RUNNING_PHYSICAL_PENDING','boot_id':old['boot_id'],
 'ui':{k:state.get(k) for k in ['phase','ui_page','ui_layer','backend','error','avatar_display']},
 'units':{n:cmd(['systemctl','show',n,'-p','MainPID','-p','ActiveState','-p','NRestarts']) for n in old['before']},
 'targets':{},'display':cmd(['xrandr','--current']),
 'voice':{name:{k:state.get(name,{}).get(k) for k in ['enabled','state','error']} for name in ['handsfree_dialogue','automatic_conversation']},
 'movement_commands_sent':0,'physical_panel_verified':False}
for name,expected in old['targets'].items():
 actual=hashlib.sha256(Path(name).read_bytes()).hexdigest();assert actual==expected;v['targets'][name]=actual
assert '1024x600+0+0' in v['display'];assert state['ui_page']=='main' and state['ui_layer']=='presentation'
health=api(8790,'/health');v['camera']={k:health.get(k) for k in ['pid','capture_hz','detection_hz','camera_error','detector_error','identity_recognition']}
assert not health.get('camera_error') and not health.get('detector_error')
assert cmd(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value']).strip()=='987'
config=Path('/home/root/aura-render24-budget-20261020/e06409743174/startup/config.json')
v['config_sha256']=hashlib.sha256(config.read_bytes()).hexdigest();assert v['config_sha256']=='eb5b8e02589728e72466a7d5ea575cbf08f62bdbce72cda4b3015865b304e49f'
v['preflight']=json.loads(cmd(['python3','-B',str(config.with_name('launcher.py')),'--config',str(config),'--preflight']))
(root/'verification.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
