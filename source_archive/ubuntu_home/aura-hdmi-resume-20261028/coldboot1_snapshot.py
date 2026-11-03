"""Read-only display/startup snapshot; no UI commands or device writes."""
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path

def run(args):
    try:
        p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=6)
        return {'rc':p.returncode,'text':p.stdout[-18000:]}
    except Exception as e:return {'error':type(e).__name__}

def file_info(path,body=False):
    p=Path(path)
    try:
        b=p.read_bytes();r={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        if body:r['text']=b.decode(errors='replace')[:16000]
        return r
    except OSError as e:return {'error':type(e).__name__}

d={'scope':'read-only; no device writes','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0],'kernel':run(['uname','-r']),'services':{},'files':{},'connectors':{}}
for unit in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']:
    d['services'][unit]=run(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts','-p','ExecStart'])
for path in ['/proc/cmdline','/sys/module/drm_kms_helper/parameters/fbdev_emulation','/sys/module/zynqmp_dpsub/parameters/power_on_delay_ms','/sys/kernel/debug/dri/0/state','/etc/X11/xorg.conf','/boot/uEnv.txt']:
    d['files'][path]=file_info(path,True)
for p in Path('/sys/class/drm').glob('card*-*'):
    if (p/'status').exists():d['connectors'][p.name]={k:file_info(p/k,k!='edid') for k in ['status','enabled','dpms','modes','edid']}
d['xrandr']=run(['xrandr','--verbose'])
d['xset']=run(['xset','q'])
d['startup_unit']=run(['systemctl','cat','aura-avatar-ui.service'])
d['xserver_unit']=run(['systemctl','cat','xserver-nodm.service'])
d['xorg_display_lines']=[line for line in Path('/var/log/Xorg.0.log').read_text(errors='replace').splitlines() if any(s in line.lower() for s in ['1024','edid','modeline','error','warning','depth'])][-65:]
k=run(['dmesg']);d['kernel_display_lines']=[line for line in k.get('text','').splitlines() if any(s in line.lower() for s in ['drm','dpdma','dpsub','display','underflow','zynqmp-dp','train','hpd'])][-45:]
try:
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:s=json.load(r)
    d['ui_state_keys']=list(s)
    d['ui_state']={k:s.get(k) for k in ['phase','playing','paused','audio_output_state','automatic_following','motor_active','listener_enabled','microphone_open']}
except Exception as e:d['ui_error']=type(e).__name__
print(json.dumps(d))
