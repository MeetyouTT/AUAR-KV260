"""Read-only fresh status after a maintenance gate refused."""
import json,subprocess,urllib.request
from pathlib import Path
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def p(unit):
 x=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result'],text=True)
 return dict(a.split('=',1) for a in x.splitlines() if '=' in a)
u=get(8783,'/api/state');m=u.get('manual_pan',{});r=m.get('readback',{});h=get(8790,'/health')
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera_unit':p('aura-camera-ui.service'),'camera_health_pid':h.get('pid'),
 'owner_fenced':h.get('dpu_schedule',{}).get('owner_fenced'),'identity_ready':h.get('identity',{}).get('ready'),
 'gui_unit':p('aura-avatar-ui.service'),'gui_phase':u.get('phase'),'playing':u.get('playing'),'audio':u.get('audio_output_state'),
 'pan':{k:m.get(k) for k in ('state','pulse_us','target_us','minimum_us','maximum_us','automatic_following','panel_open','backend_pid')},
 'readback':{k:r.get(k) for k in ('flags','width_us','target_us','lease_left_ms','active','armed','epoch','ack_seq','reason')},
 'history_entries':len(m.get('history',[]))},sort_keys=True))
