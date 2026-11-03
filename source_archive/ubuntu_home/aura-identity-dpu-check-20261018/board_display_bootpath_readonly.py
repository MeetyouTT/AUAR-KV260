"""Read boot display capabilities and files, without changing boot environment."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
def cmd(args):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=6)
  return {'rc':p.returncode,'text':p.stdout[-5000:]}
 except Exception as e:return {'error':str(e)}
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'kernel':os.uname().release,'cmdline':Path('/proc/cmdline').read_text().strip(),'files_modified':0,'display_commands_sent':0,'movement_commands_sent':0}
v['tools']={n:shutil.which(n) for n in ['fw_printenv','fw_setenv','dumpimage','mkimage','strings']}
v['mounts']=[s for s in Path('/proc/mounts').read_text().splitlines() if s.split()[1] in ['/','/boot','/boot/firmware','/media','/run/media/mmcblk1p1']]
v['boot_files']=[]
for base in ['/boot','/run/media/mmcblk1p1','/media/mmcblk1p1']:
 root=Path(base)
 if not root.exists():continue
 for p in root.glob('*'):
  v['boot_files'].append({'path':str(p),'directory':p.is_dir(),'bytes':p.stat().st_size})
 for rel in ['uEnv.txt','extlinux/extlinux.conf','boot.cmd']:
  p=root/rel
  if p.is_file():v[str(p)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'text':p.read_text(errors='replace')[:7000]}
 p=root/'boot.scr'
 if p.is_file():
  b=p.read_bytes();v[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'strings':[x.decode(errors='replace') for x in re.findall(rb'[ -~]{8,}',b) if any(t in x for t in [b'bootargs',b'video',b'image.ub',b'uEnv',b'extlinux',b'booti',b'bootm'])][:25]}
p=Path('/etc/fw_env.config')
if p.exists():v['fw_env_config']=p.read_text()[:1500]
if v['tools']['fw_printenv'] and p.exists():
 v['boot_environment']=cmd(['fw_printenv','bootargs','video-mode','stdout','stderr','stdin'])
v['force']=Path('/sys/kernel/debug/dri/0/DP-1/force').read_text().strip()
b=Path('/sys/kernel/debug/dri/0/DP-1/edid_override').read_bytes();v['override_bytes']=len(b);v['override_sha256']=hashlib.sha256(b).hexdigest() if b else None
v['edid_bytes']=len(Path('/sys/class/drm/card0-DP-1/edid').read_bytes())
v['display']=cmd(['env','DISPLAY=:0','xrandr','--current'])
print(json.dumps(v),flush=True)
