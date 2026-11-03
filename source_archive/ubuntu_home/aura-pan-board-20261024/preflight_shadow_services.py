"""Read-only service and owner gate for a camera-only shadow restart."""
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

def props(unit):
    raw=subprocess.check_output(['systemctl','show',unit,'-p','MainPID,ActiveState,SubState,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],text=True)
    return dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
def get(port,path):
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with op.open('http://127.0.0.1:%s%s'%(port,path),timeout=3) as r:return json.load(r)
c=props('aura-camera-ui.service');u=props('aura-avatar-ui.service');h=get(8790,'/health');g=get(8783,'/api/state')
s=h.get('dpu_schedule',{});i=h.get('identity',{});m=g.get('manual_pan',{})
try:f=get(8790,'/v1/motion/observation');feed={'http':200,'state':f.get('state')}
except urllib.error.HTTPError as e:feed={'http':e.code}
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera':{k:c.get(k) for k in ('MainPID','ActiveState','SubState','Result','ExecMainStatus','Restart','KillMode','SendSIGKILL','TimeoutStopUSec')},
 'camera_health':{'pid':h.get('pid'),'native_critical':s.get('native_critical'),'owner_fenced':s.get('owner_fenced'),'identity_ready':i.get('ready'),'worker_alive':i.get('face_targets',{}).get('worker_alive'),'gaps':i.get('face_targets',{}).get('freshness_metrics',{}).get('counters',{}).get('observed_gap_intervals')},
 'gui':{k:u.get(k) for k in ('MainPID','ActiveState','SubState','Result')},
 'gui_state':{'phase':g.get('phase'),'playing':g.get('playing'),'audio':g.get('audio_output_state')},
 'manual_pan':{k:m.get(k) for k in ('state','pulse_us','minimum_us','maximum_us','automatic_following','mechanical_reference_calibrated')},
 'motion_feed':feed},sort_keys=True))
