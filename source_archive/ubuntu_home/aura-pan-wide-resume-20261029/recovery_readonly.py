import json,subprocess,urllib.request
from pathlib import Path
def get(port,path):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
 except Exception as e:return {'error':type(e).__name__}
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=8);return {'rc':p.returncode,'text':p.stdout[-16000:],'error':p.stderr[-700:]}
h=get(8790,'/health');u=get(8783,'/api/state');s=h.get('dpu_schedule',{})
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0],'camera':{k:h.get(k) for k in ['pid','capture_hz','detection_hz','capture_frames','detected_frames','camera_error','detector_error']},'identity_ready':h.get('identity',{}).get('ready'),'ui':{k:u.get(k) for k in ['phase','audio_output_state','avatar_display']},'native_handoff':s.get('protection_handoff'),'faults':{'primary':s.get('primary_period_overruns'),'optional':{k:v.get('overruns') for k,v in s.get('optional',{}).items()}},'previous_boots':run(['journalctl','--list-boots','--no-pager']),'previous_kernel':run(['journalctl','-k','-b','-1','-n','55','--no-pager','-o','cat']),'last_boot_record':run(['last','-x','-n','5'])}
print(json.dumps(d))
