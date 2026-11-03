import hashlib,json,subprocess,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
h=get(8790,'/health');u=get(8783,'/api/state')
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecStart','-p','NRestarts'],text=True)
units=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
cfg=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/startup/config.json')
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera_pid':h['pid'],
 'owner_fenced':h['dpu_schedule']['owner_fenced'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()},'gui_unit':units,
 'phase':u['phase'],'playing':u.get('playing'),'audio_state':u.get('audio_output_state'),
 'manual_state':u['manual_pan']['state'],'automatic_following':u['manual_pan']['automatic_following'],
 'old_gui_config_sha256':hashlib.sha256(cfg.read_bytes()).hexdigest(),'motor_commands':0,'MMIO_opened':False}))
