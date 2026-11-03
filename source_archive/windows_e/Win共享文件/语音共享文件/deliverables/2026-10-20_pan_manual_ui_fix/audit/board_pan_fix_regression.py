"""One bounded UI regression sequence, returning to1450us; no retry or following."""
import json,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-pan-manual-ui-20261020/fix-v2');out=root/'regression.json'
assert not out.exists()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def state():
 with opener.open(base+'/api/state',timeout=1) as r:return json.load(r)
def post(value):
 request=urllib.request.Request(base+'/api/command',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':base})
 with opener.open(request,timeout=4) as r:v=json.load(r)
 assert v.get('ok'),v
 return v
def wait_ready(count,seconds=5):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  s=state();p=s['manual_pan']
  assert p['state'] not in ('FAULT','UNAVAILABLE'),p
  if p['state']=='READY' and len(p['history'])==count:return s
  time.sleep(.05)
 raise RuntimeError('Finite step readiness timed out')
s=state();p=s['manual_pan']
assert p['state']=='READY' and p['pulse_us']==1450 and not p['history'] and p['readback']['flags']==0
report={'status':'STARTING','initial':p,'steps':[],'scope':'Two20us steps and two5us steps; stop/reconnect;final1450;lease100ms','automatic_following':False}
try:
 post({'type':'ui_page','page':'vision'});post({'type':'pan_dialog'})
 for index,(direction,step,target) in enumerate([('right',20,1470),('left',20,1450),('right',5,1455),('left',5,1450)]):
  post({'type':'pan_jog','direction':direction,'step_us':step})
  s=wait_ready(index+1);p=s['manual_pan'];row=p['history'][-1]
  assert p['pulse_us']==target and row['final_us']==target and row['commands_accepted']>=35 and row['failure'] is None,row
  assert row['final']['flags']==0 and row['final']['lease_left_ms']==0
  report['steps'].append(row)
 pid=p['backend_pid']
 post({'type':'pan_reconnect'})
 deadline=time.monotonic()+12
 while time.monotonic()<deadline:
  s=state();p=s['manual_pan']
  if p['state']=='READY' and p['backend_pid']!=pid:break
  time.sleep(.1)
 else:raise RuntimeError('Explicit reconnect timed out')
 assert p['pulse_us']==1450 and p['history']==[] and p['readback']['flags']==0 and p['readback']['lease_left_ms']==0
 time.sleep(.3);final=state()['manual_pan'];assert not final['history'] and final['state']=='READY'
 report.update(status='UI_COARSE_FINE_RECONNECT_PASS_FINAL1450_OUTPUT_OFF',final=final,previous_backend_pid=pid)
except BaseException as e:
 report.update(status='FAILED_NO_RETRY',error=type(e).__name__+': '+str(e))
 try:post({'type':'pan_stop'});report['failure_state']=state()['manual_pan']
 except Exception:pass
finally:
 out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 summary=dict(report)
 summary['steps']=[{k:r.get(k) for k in ['direction','target_us','final_us','commands_accepted','duration_ms','timing','failure']} for r in report['steps']]
 print(json.dumps(summary),flush=True)
