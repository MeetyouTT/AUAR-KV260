import hashlib,json,re,subprocess,time,urllib.request
from pathlib import Path
v={'scope':'cached-only display snapshot; no AUX/DDC/USB/splitter writes or modeset',
 'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),
 'uptime':Path('/proc/uptime').read_text().split()[0]}
def read(p):
 try:return Path(p).read_text().strip()
 except OSError:return None
v['connectors']={}
for p in Path('/sys/class/drm').glob('card*-DP-*'):
 raw=(p/'edid').read_bytes();v['connectors'][p.name]={k:read(p/k) for k in ['status','enabled','dpms','modes']}
 v['connectors'][p.name].update(edid_bytes=len(raw),edid_sha256=hashlib.sha256(raw).hexdigest())
state=read('/sys/kernel/debug/dri/0/state') or ''
v['scanout']=[s.strip() for s in state.splitlines() if any(k in s for k in ['format=','size=','pitch=','crtc-pos=','mode:']) or s.strip().startswith(('enable=','active='))]
v['display_clocks']=[s.strip() for s in (read('/sys/kernel/debug/clk/clk_summary') or '').splitlines() if s.split() and s.split()[0] in ['dp_video_ref','dpdma_ref','dp_aclk']]
v['hashes']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['/boot/uEnv.txt','/etc/X11/xorg.conf']}
v['fbdev_emulation']=read('/sys/module/drm_kms_helper/parameters/fbdev_emulation')
v['fb_nodes']=[p.name for p in Path('/sys/class/graphics').glob('fb*')]
v['xorg_initial_mode']=[s.strip() for s in (read('/var/log/Xorg.0.log') or '').splitlines() if 'initial mode' in s.lower()]
v['usb_devices']={p.name:{k:read(p/k) for k in ['idVendor','idProduct','product','busnum','devnum']} for p in Path('/sys/bus/usb/devices').glob('*') if (p/'idVendor').exists()}
v['units']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts'],text=True)
kernel=subprocess.check_output(['dmesg'],text=True)
v['kernel_display']=[s for s in kernel.splitlines() if re.search(r'zynqmp-display|dpdma|aux.*(?:fail|error)|training|underflow|drm.*(?:edid|hotplug)',s,re.I)][-50:]
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for key,port,path,fields in [('camera',8790,'/health',['pid','detected_frames','capture_hz','detection_hz','camera_error','detector_error']),('gui',8783,'/api/state',['phase','playing','ui_page','backend'])]:
 try:
  with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as response:h=json.load(response)
  v[key]={n:h.get(n) for n in fields}
 except Exception as e:v[key]={'unavailable':type(e).__name__}
print(json.dumps(v))
