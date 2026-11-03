"""Read a small live snapshot without requesting private identity or media."""
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
def run(a):
 p=subprocess.run(a,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
 return p.stdout
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
h=get(8790,'/health');u=get(8783,'/api/state');c=Path('/sys/class/drm/card0-DP-1')
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0],'camera':{k:h[k] for k in ['pid','capture_frames','detected_frames','capture_hz','detection_hz','camera_error','detector_error']},'ui':{k:u[k] for k in ['phase','audio_output_state','playing']},'pan':{k:u['manual_pan'].get(k) for k in ['state','automatic_following','pulse_us']},'connector':{k:(c/k).read_text().strip() for k in ['status','enabled','dpms']},'edid_bytes':len((c/'edid').read_bytes()),'edid_sha256':hashlib.sha256((c/'edid').read_bytes()).hexdigest(),'xrandr':run(['xrandr','--verbose']),'drm_state':Path('/sys/kernel/debug/dri/0/state').read_text(),'kernel_lines':[s for s in run(['dmesg']).splitlines() if any(t in s.lower() for t in ['usb disconnect','new full-speed','new high-speed','underflow','train failed','dpdma','dpsub','hpd'])][-25:]}
d['service_pids']={n:run(['systemctl','show',n,'-p','MainPID','--value']).strip() for n in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']}
print(json.dumps(d))
