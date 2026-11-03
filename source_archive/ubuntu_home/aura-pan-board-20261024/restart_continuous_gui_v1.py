"""Restart only the owned GUI; preserve native camera and stopped actuator."""
import json,subprocess,time,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');h=get(8790,'/health');m=u['manual_pan'];r=m['readback'];assert u['phase']=='IDLE' and not u['playing']
assert m['state']=='READY' and not m['automatic_following'] and r['flags']==0 and r['lease_left_ms']==0
assert h['pid']==153151 and h['identity']['ready'] and not h['dpu_schedule']['owner_fenced']
unit='aura-avatar-ui.service';pid=lambda:subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()
before=int(pid());state={'phase':'GUI_RESTARTING','camera_pid':h['pid'],'gui_pid_before':before,'readback':r,'primary_before':h['dpu_schedule']['primary_period_overruns'],
 'optional_before':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')}}
p=N/'continuous-stage.json';assert not p.exists();p.write_text(json.dumps(state,indent=2)+'\n')
subprocess.run(['systemctl','stop','--no-block',unit],check=True);end=time.monotonic()+25
while time.monotonic()<end and pid()!='0':time.sleep(.2)
assert pid()=='0';assert get(8790,'/health')['pid']==h['pid']
subprocess.run(['systemctl','start','--no-block',unit],check=True)
state['phase']='GUI_STARTING';p.write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps({'phase':state['phase'],'camera_pid_preserved':h['pid'],'gui_old_pid':before,'movement_commands':0}))
