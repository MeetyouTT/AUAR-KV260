"""Read-only display/boot detail."""
import hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
def run(args):
    try:
        p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=4)
        return {'rc':p.returncode,'text':p.stdout+p.stderr}
    except Exception as exc:return {'error':type(exc).__name__}
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
   'display_commands_sent':0,'movement_commands_sent':0,'files_modified':0}
kernel=run(['dmesg'])
v['kernel_display']=[line for line in kernel.get('text','').splitlines()
    if re.search(r'edid|hdmi|dpdma|dpsub|zynqmp.*(display|dp)|dpll|pixel.clock|link.train|dp.*(error|fail)',line,re.I)]
v['fb']=run(['fbset','-i'])
x=run(['xdpyinfo']);v['x_depth']=[line for line in x.get('text','').splitlines()
    if re.search(r'depth|dimensions|resolution|bits_per_rgb|visual id|class:|red, green, blue masks',line,re.I)][:32]
v['drm_state']=run(['cat','/sys/kernel/debug/dri/0/state'])
v['boot_commandline']=Path('/proc/cmdline').read_text().strip()
v['firmware']=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
log=Path('/var/log/Xorg.0.log')
if log.exists():v['xorg_display']=[line for line in log.read_text(errors='replace').splitlines()
    if re.search(r'EDID|default mode|Modeline|Depth|bits per pixel|RGB|\(EE\)|\(WW\)|glamor|shadow',line,re.I)][-65:]
v['xorg_configs']={str(p):p.read_text()[:2200] for p in Path('/etc/X11').glob('xorg.conf.d/*.conf')}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with op.open('http://127.0.0.1:8783/api/state',timeout=1) as r:s=json.load(r)
    pan=s.get('manual_pan',{});v['pan']={k:pan.get(k) for k in ['state','error','backend_pid','readback']}
except Exception as exc:v['pan']={'unavailable':type(exc).__name__}
pid=int(run(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'])['text'].strip())
args=Path('/proc/%d/cmdline'%pid).read_bytes().decode().split('\0')
c=json.loads(Path(args[args.index('--config')+1]).read_text());root=Path(c['runtime'])/'aura'
for name in ['tools/board_screen_capture.py','tools/native_pixels.cpp','tools/native_pixels.py','tools/libaura_pixels.so']:
    p=root/name
    if p.exists():v.setdefault('source_hashes',{})[name]=hashlib.sha256(p.read_bytes()).hexdigest()
pc=root/'config/pan_manual.local.json'
if pc.exists():
    p=json.loads(pc.read_text());v['pan_config']={k:p.get(k) for k in ['enabled','boot_id']}
print(json.dumps(v),flush=True)
