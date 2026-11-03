import json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');o=urllib.request.build_opener(urllib.request.ProxyHandler({}));u=None;error=None
try:
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
except Exception as e:error=type(e).__name__+': '+str(e)[:180]
with o.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Result'],text=True)
out=dict(gui_unit=unit,api_error=error,camera_pid=h['pid'],primary_overruns=h['dpu_schedule']['primary_period_overruns'],pcm_state=Path('/proc/asound/card1/pcm0p/sub0/status').read_text().splitlines()[0])
if u is not None:
 b=json.loads((R/'idle-gui-audio-reconnect-before.json').read_text());m=u['manual_pan']
 out.update(phase=u.get('phase'),audio_output_state=u.get('audio_output_state'),readback=m.get('readback'),manual_state=m['state'],following=m['automatic_following'])
 if m['state']=='READY' and not m['automatic_following'] and m['readback']==b['readback'] and u.get('audio_output_state')=='IDLE_READY':
  s=json.loads((R/'state.json').read_text());pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
  s.update(phase='R12_SOURCE_V14_READY_OUTPUT_STOPPED',current_gui_pid=pid,idle_audio_reconnect_completed=True,automatic_following=False)
  (R/'state.json').write_text(json.dumps(s,indent=2)+'\n');out['status']='GUI_AUDIO_RECONNECT_READY'
if out.get('status')!='GUI_AUDIO_RECONNECT_READY':
 out['recent_unit_log']=subprocess.check_output(['journalctl','-u','aura-avatar-ui.service','-n','12','--no-pager','-o','cat'],text=True)[-3500:]
print(json.dumps(out))
