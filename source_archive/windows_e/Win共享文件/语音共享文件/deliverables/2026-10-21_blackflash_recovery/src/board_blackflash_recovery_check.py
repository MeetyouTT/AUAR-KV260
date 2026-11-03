"""Verify the one-time recovery and its cancelled fallback timer."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
root=Path('/home/root/aura-display-recovery-20261021')/boot
record=json.loads((root/'result.json').read_text())
def cmd(args):
 p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=4)
 return {'rc':p.returncode,'text':p.stdout}
def sample():
 raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
 v={'uptime':Path('/proc/uptime').read_text().split()[0],'edid_bytes':len(raw),'edid_sha256':hashlib.sha256(raw).hexdigest() if raw else None}
 v['units']=cmd(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
 v['ui']={k:s.get(k) for k in ['phase','ui_page','ui_layer','error','avatar_display']}
 return v
v={'boot_id':boot,'before':sample()};time.sleep(8);v['after']=sample()
v['timer']=cmd(['systemctl','show',record['timer']+'.timer','-p','LoadState','-p','ActiveState','-p','SubState'])
v['display']=cmd(['xrandr','--current']);v['dpms']=cmd(['xset','q'])
v['config_hashes']={}
for name in ['/etc/X11/xorg.conf','/home/root/aura-speech-motion-20261021/922dab49a74f/startup/config.json','/home/root/aura-speech-motion-20261021/922dab49a74f/startup/launcher.py']:
 v['config_hashes'][name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
v.update(files_modified=0,display_commands_sent=0,movement_commands_sent=0)
print(json.dumps(v),flush=True)
