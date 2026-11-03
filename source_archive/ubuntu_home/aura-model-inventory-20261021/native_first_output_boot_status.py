import json,subprocess,time,urllib.request
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
root=Path('/home/root/aura-display-sequence-20261024/deferred/15d8d8f6a596610a')
plan=json.loads((root/'plan.json').read_text());report=root/('report-'+boot+'.json')
result={'boot':boot,'uptime':float(Path('/proc/uptime').read_text().split()[0]),'plan':plan,
 'report_exists':report.exists(),'trial_report':json.loads(report.read_text()) if report.exists() else None}
p=Path('/home/root/aura-native-coldboot-20261024/376e4921416108f4/shutdown.json')
if p.exists():
 v=json.loads(p.read_text());result['shutdown']={k:v.get(k) for k in ['safe_to_disconnect_power','poweroff_scheduled','failure','checkpoint_sha256']}
units={}
for u in ['xserver-nodm.service','aura-avatar-ui.service','aura-camera-ui.service']:
 text=subprocess.check_output(['systemctl','show',u,'-p','MainPID','-p','ControlPID','-p','ActiveState','-p','SubState','-p','Result'],text=True)
 units[u]=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
result['services']=units
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for k,port,path,fields in [('camera',8790,'/health',['pid','detected_frames','detection_hz','camera_error','detector_error']),('gui',8783,'/api/state',['phase','ui_page','backend','playing'])]:
 try:
  with op.open('http://127.0.0.1:'+str(port)+path,timeout=2) as stream:value=json.load(stream)
  result[k]={n:value.get(n) for n in fields}
 except Exception as e:result[k]={'unavailable':type(e).__name__}
print(json.dumps(result))
