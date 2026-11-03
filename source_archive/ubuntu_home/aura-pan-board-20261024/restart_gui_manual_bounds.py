"""Load the matching manual range, leaving camera and hardware output stopped."""
import json,subprocess,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');h=get(8790,'/health');m=u['manual_pan'];assert u['phase']=='IDLE' and not u['playing']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
config=json.loads((N/'runtime/aura/config/pan_manual.local.json').read_text());assert config['manual_maximum_us']==1505
assert h['pid']==153151 and h['identity']['ready'] and not h['dpu_schedule']['owner_fenced']
before=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
subprocess.run(['systemctl','restart','--no-block','aura-avatar-ui.service'],check=True)
print(json.dumps({'status':'FINAL_GUI_MANUAL_BOUNDS_RESTARTING','old_gui_pid':before,'camera_pid':h['pid'],
 'camera_restarted':False,'motion_commands':0,'manual_bounds_us':[1425,1505]}))
