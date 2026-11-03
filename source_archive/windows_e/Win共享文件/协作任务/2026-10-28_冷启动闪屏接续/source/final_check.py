import hashlib,json,subprocess,urllib.request
from pathlib import Path
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
h=get(8790,'/health');u=get(8783,'/api/state');s=h['dpu_schedule'];x=s['protection_handoff'];c=Path('/sys/class/drm/card0-DP-1')
unit={n:subprocess.run(['systemctl','show',n,'-p','MainPID','-p','ActiveState','-p','NRestarts'],stdout=subprocess.PIPE,text=True).stdout for n in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']}
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime_s':float(Path('/proc/uptime').read_text().split()[0]),'camera':{k:h[k] for k in ['pid','capture_hz','detection_hz','capture_frames','detected_frames','camera_error','detector_error']},'services':unit,'ui':{k:u[k] for k in ['phase','audio_output_state','playing']},'pan':{k:u['manual_pan'].get(k) for k in ['state','automatic_following','pulse_us']},'listening':{k:u['handsfree_dialogue'].get(k) for k in ['enabled','microphone_open']},'connector':{k:(c/k).read_text().strip() for k in ['status','enabled','dpms']},'edid_bytes':len((c/'edid').read_bytes()),'native_history':{k:x.get(k) for k in ['source_boot','current_boot','seed_sha256','previous_kernel_history']},'faults':{'primary':s['primary_period_overruns'],'optional':{k:v['overruns'] for k,v in s['optional'].items()}}}
paths=['/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f/startup/config.json','/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f/startup/launcher.py']
d['protected_sha256']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
print(json.dumps(d))
