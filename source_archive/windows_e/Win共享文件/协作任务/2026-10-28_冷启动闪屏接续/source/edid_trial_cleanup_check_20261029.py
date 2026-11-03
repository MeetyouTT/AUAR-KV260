"""Inspect rollback effects and the transient timer without changing display state."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
BOOT='3336afd3-7926-40b3-b5fd-e17b86256830'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path('/run/aura-hdmi-edid-trials/da17ffa826824b7da2c069721b4a5c84')
def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
    return {'rc':p.returncode,'text':p.stdout[-12000:]}
o=Path('/sys/kernel/debug/dri/0/DP-1/edid_override').read_bytes();c=Path('/sys/class/drm/card0-DP-1');b=(c/'edid').read_bytes()
d={'boot_id':BOOT,'override_bytes':len(o),'sysfs_edid_bytes':len(b),'sysfs_edid_sha256':hashlib.sha256(b).hexdigest(),'connector':{k:(c/k).read_text().strip() for k in ['status','enabled','dpms']},'drm_state':Path('/sys/kernel/debug/dri/0/state').read_text(),'xset':run(['env','DISPLAY=:0','xset','q']),'files':{}}
for name in ['meta.json','applied.json','restored.json','failed.json']:
    p=root/name
    if p.exists():d['files'][name]=json.loads(p.read_text())
unit='aura-edid-restore-da17ffa826824b7da2c069721b4a5c84'
d['timer']=run(['systemctl','show',unit+'.timer','-p','LoadState','-p','ActiveState'])
d['restore_service']=run(['systemctl','show',unit+'.service','-p','LoadState','-p','ActiveState','-p','Result','-p','ExecMainStatus'])
d['rollback_journal']=run(['journalctl','-b','-u',unit+'.service','-u',unit+'.timer','--no-pager','-o','short-monotonic'])
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
d['camera']={k:h.get(k) for k in ['pid','capture_frames','capture_hz','detection_hz','camera_error','detector_error']}
d['services']=run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])
print(json.dumps(d))
