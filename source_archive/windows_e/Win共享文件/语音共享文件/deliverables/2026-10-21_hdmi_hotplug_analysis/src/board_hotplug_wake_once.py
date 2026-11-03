"""Separate one runtime DPMS wake from a later physical HDMI comparison."""
import hashlib,json,subprocess,time
from pathlib import Path
BOOT='975f931a-927b-4a06-b784-ebda8463177f'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
config=Path('/etc/X11/xorg.conf')
assert hashlib.sha256(config.read_bytes()).hexdigest()=='64457c25a844ef95cd4ae62bacba80b0cbec5ae1a54efdc15e3ec02775c0555a'
root=Path('/run/aura-hotplug-wake-once-20261021')/BOOT
root.mkdir(parents=True,exist_ok=False)
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
 return {'rc':p.returncode,'text':p.stdout}
def snap():
 p=Path('/sys/class/drm/card0-DP-1');edid=(p/'edid').read_bytes()
 return {'uptime':Path('/proc/uptime').read_text().split()[0],'xset':run(['env','DISPLAY=:0','xset','q']),
 'connector':{k:(p/k).read_text().strip() for k in ['enabled','dpms','status']},
 'edid_bytes':len(edid),'edid_sha256':hashlib.sha256(edid).hexdigest(),
 'drm_state':Path('/sys/kernel/debug/dri/0/state').read_text(),
 'display_clocks':[s.strip() for s in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines() if s.split() and s.split()[0] in ['dp_video_ref','dpdma_ref','dp_aclk']],
 'units':run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])}
v={'boot_id':BOOT,'before':snap()}
(root/'before.json').write_text(json.dumps(v))
v['wake']=run(['env','DISPLAY=:0','xset','dpms','force','on'])
time.sleep(2)
v['after']=snap();v.update(persistent_configuration_changes=0,reboots=0,movement_commands_sent=0)
(root/'result.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
