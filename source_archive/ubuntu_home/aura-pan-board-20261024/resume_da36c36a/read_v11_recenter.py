import json,subprocess,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
with o.open(base+'/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];follow=m.get('face_follow') or {};report=None
if follow.get('report'):
 p=Path(follow['report']);p.relative_to(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v11r1/runs'))
 if p.is_file() and p.stat().st_size:report=json.loads(p.read_text())
with o.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
zone=Path('/home/root/aura-pan-current-20261024/da36c36a/face-zone-display-status.json')
display=json.loads(zone.read_text()) if zone.exists() else None
print(json.dumps({'manual':m,'report':report,'zone_display':display,'camera_pid':h['pid'],
 'primary_overruns':h['dpu_schedule']['primary_period_overruns'],'optional_overruns':{k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()},
 'identity_ready':h['identity']['ready'],'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'read_only':True,'motor_commands_sent':0}))
