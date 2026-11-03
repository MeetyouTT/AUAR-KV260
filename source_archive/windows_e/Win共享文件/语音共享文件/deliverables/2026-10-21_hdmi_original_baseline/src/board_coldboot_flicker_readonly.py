"""Read display and service state without changing board configuration."""
import hashlib,json,os,re,subprocess,time,urllib.request
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
def cmd(args):
 try:
  p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=4)
  return {'rc':p.returncode,'text':p.stdout[-12000:]}
 except Exception as e:return {'error':str(e)}
def sample():
 v={'uptime':Path('/proc/uptime').read_text().split()[0]}
 v['units']=cmd(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts'])
 v['connector']=[]
 for p in Path('/sys/class/drm').glob('card*-*/edid'):
  b=p.read_bytes();v['connector'].append({'path':str(p.parent),'edid_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),**{k:p.with_name(k).read_text().strip() for k in ['status','enabled','dpms'] if p.with_name(k).exists()}})
 try:
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
  v['ui']={k:s.get(k) for k in ['phase','ui_page','ui_layer','error','avatar_display']}
 except Exception as e:v['ui']={'error':str(e)}
 return v
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'before':sample(),'xrandr':cmd(['xrandr','--verbose']),'dpms':cmd(['xset','q'])}
v['journal']=cmd(['journalctl','-b','-u','aura-avatar-ui.service','-u','xserver-nodm.service','--no-pager','-o','short-monotonic','-n','70'])
v['kernel']=[s for s in cmd(['dmesg']) .get('text','').splitlines() if re.search(r'edid|drm|hdmi|display|dpdma|underflow|zynqmp.*dp',s,re.I)]
p=Path('/var/log/Xorg.0.log');v['xorg']=[s for s in p.read_text(errors='replace').splitlines() if re.search(r'EDID|1024|modeline|mode|error|fail|ARMSOC',s,re.I)][-70:]
for name in ['/etc/X11/xorg.conf','/run/aura-display-startup.json']:
 p=Path(name)
 if p.exists():v[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'text':p.read_text()[:5000]}
time.sleep(3);v['after']=sample();v.update(files_modified=0,display_commands_sent=0,movement_commands_sent=0)
print(json.dumps(v),flush=True)
