import hashlib,json,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path('/home/root/aura-pan-ui-v2-20261024/observed-ecfbdef064d157b6')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
assert json.loads((ROOT/'trial-state.json').read_text())['phase']=='ACCEPTED_MANUAL_READY_NO_AUTOMATIC_MOTION'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));address='http://127.0.0.1:8783'
def state():
 with op.open(address+'/api/state',timeout=3) as response:return json.load(response)
def command(value):
 request=urllib.request.Request(address+'/api/command',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':address})
 try:
  with op.open(request,timeout=5) as response:return response.status,json.load(response)
 except urllib.error.HTTPError as error:return error.code,json.loads(error.read())
before=state()['manual_pan'];assert before['state']=='READY' and not before['history']
code,rejection=command({'type':'pan_jog','direction':'right','step_us':20})
assert code==400 and '请直接点击转轴按钮' in rejection.get('error',''),(code,rejection)
time.sleep(.4);after=state()['manual_pan']
assert after['state']=='READY' and not after['history'] and after['pulse_us']==before['pulse_us']
assert all(after['readback'][k]==before['readback'][k] for k in ['flags','lease_left_ms','epoch','ack_seq','width_us'])
code,opened=command({'type':'pan_dialog'});assert code==200 and opened.get('ok'),(code,opened)
time.sleep(.4);final=state()
assert final['manual_pan']['panel_open'] and final['manual_pan']['state']=='READY'
result={'remote_jog_correctly_rejected':True,'rejection':rejection,'panel_opened':True,
 'no_jog_history':not final['manual_pan']['history'],'final_pan':final['manual_pan'],
 'new_motion_commands_sent':0,'external_waveform_verified':False}
print(json.dumps(result,ensure_ascii=False))
