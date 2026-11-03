"""Read current display and two camera/UI samples; no service or device changes."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path

assert os.uname().machine=='aarch64'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='c006a771-c3e4-4d4f-97d7-ade3dd774619'
def read(path):
    try:return Path(path).read_text().strip()
    except OSError as e:return {'error':type(e).__name__}
def get(port,path):
    try:
        with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
    except Exception as e:return {'error':type(e).__name__}
def run(args):
    try:
        p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=4)
        return {'rc':p.returncode,'text':p.stdout[-16000:]}
    except Exception as e:return {'error':type(e).__name__}
def sample():
    h=get(8790,'/health');u=get(8783,'/api/state')
    return {'monotonic':time.monotonic(),'boot_id':read('/proc/sys/kernel/random/boot_id'),
        'camera':{k:h.get(k) for k in ['error','pid','capture_frames','detected_frames','capture_hz','detection_hz','camera_error','detector_error']},
        'ui':{k:u.get(k) for k in ['error','phase','audio_output_state','playing','ui_page','automatic_following']},
        'preview':u.get('ui_runtime',{}).get('preview_metrics',{}),
        'pan':{k:u.get('manual_pan',{}).get(k) for k in ['state','automatic_following','pulse_us','error']},
        'listening':{k:u.get('handsfree_dialogue',{}).get(k) for k in ['enabled','microphone_open']}}
d={'scope':'read-only display queries and two filtered HTTP samples','uptime':read('/proc/uptime'),'before':sample()}
time.sleep(2)
d['after']=sample()
d['services']=run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])
d['xrandr']=run(['xrandr','--verbose']);d['xset']=run(['xset','q'])
d['drm_state']=read('/sys/kernel/debug/dri/0/state')
d['connectors']={}
for c in Path('/sys/class/drm').glob('card*-*'):
    if not (c/'status').exists():continue
    v={k:read(c/k) for k in ['status','enabled','dpms','modes']}
    try:
        b=(c/'edid').read_bytes();v['edid']={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    except OSError as e:v['edid']={'error':type(e).__name__}
    d['connectors'][c.name]=v
print(json.dumps(d))
