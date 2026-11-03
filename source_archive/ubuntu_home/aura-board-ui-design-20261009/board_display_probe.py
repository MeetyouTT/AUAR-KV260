"""Read-only display readiness and current camera health after an external reboot."""
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
def run(args):
    try:
        r=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
        return {'rc':r.returncode,'output':r.stdout[-7000:]}
    except Exception as e:return {'error':str(e)}
out={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'drm':[]}
for p in sorted(Path('/sys/class/drm').glob('card*-*')):
    if not (p/'status').exists():continue
    d=(p/'edid').read_bytes() if (p/'edid').exists() else b''
    out['drm'].append({'path':str(p),'status':(p/'status').read_text().strip(),
        'edid_bytes':len(d),'edid_sha256':hashlib.sha256(d).hexdigest() if d else None,
        'modes':(p/'modes').read_text() if (p/'modes').exists() else ''})
out['xrandr']=run(['xrandr','--current']);out['display_power']=run(['xset','q']);out['touch']=run(['xinput','list'])
out['xserver']=run(['systemctl','show','xserver-nodm.service','-p','ActiveState','-p','SubState','-p','MainPID'])
try:
    with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=2) as s:out['camera_health']=json.load(s)
except Exception as e:out['camera_error']=str(e)
print(json.dumps(out))
