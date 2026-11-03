"""Use the reviewed passive reboot observer to verify the native first mode."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).parent
source=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_preinit_candidate/src/warmboot_once.py')
spec=importlib.util.spec_from_file_location('passive_reboot',source)
observer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)
observer.PACKAGE=ROOT
observer.CAPTURE_SUFFIX='native-firstmode-warmboot'
observer.STATUS_FILE='../latest-native-firstmode-warmboot.json'
observer.OPERATION='verify_native_firstmode_original_kernel'
observer.PREFLIGHT='''import hashlib,json,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bec99c5a-5292-4a3e-b180-c52187d6c47b'
assert not Path('/sys/module/zynqmp_dpsub/parameters/initial_aux_delay_ms').exists()
root=Path('/boot/aura-native-firstmode-20261021')
manifest=json.loads((root/'manifest.json').read_text())
for item in manifest['targets']:
 assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['after_sha256']
for name,sha in manifest['protected'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
assert s['phase']=='IDLE' and not s.get('playing'),'Application busy'
record={'preflight_passed':True,'ui_phase':s['phase'],'boot_id_before':'bec99c5a-5292-4a3e-b180-c52187d6c47b','reboot_command_sent_at_preflight':False}
with (root/'reboot-request.json').open('x') as f:f.write(json.dumps(record)+'\\n')
print(json.dumps(record))
'''
observer.POSTCHECK='''import hashlib,json,re,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def api(url,keys):
 try:
  with op.open(url,timeout=2) as r:d=json.load(r)
  return {k:d.get(k) for k in keys}
 except Exception as e:return {'unavailable':str(e)}
deadline=time.monotonic()+65
while True:
 units=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True,timeout=4)
 if units.count('ActiveState=active')==3 or time.monotonic()>=deadline:break
 time.sleep(1)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
v={'boot_id':boot,'version':Path('/proc/version').read_text().strip(),'cmdline':Path('/proc/cmdline').read_text().strip(),'units':units,'physical_panel_verified':False,'movement_commands_sent':0}
v['fbdev_emulation']=Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation').read_text().strip()
v['framebuffers']=[p.name for p in Path('/sys/class/graphics').glob('fb[0-9]*')]
p=Path('/var/log/Xorg.0.log');text=p.read_text(errors='replace') if p.exists() else ''
v['xorg_initial_modes']=re.findall(r'Output DP-1 using initial mode (\\S+)',text)
v['xorg_native_config']=[s for s in text.splitlines() if re.search(r'AURA-HDMI|initial mode|Depth 16|Modeline.*1024x600',s)]
v['display']=subprocess.run(['env','DISPLAY=:0','xrandr','--verbose'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5).stdout
raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes();v['edid_bytes']=len(raw);v['edid_sha256']=hashlib.sha256(raw).hexdigest()
v['gui']=api('http://127.0.0.1:8783/api/state',['phase','playing','ui_page','error','avatar_display'])
v['camera']=api('http://127.0.0.1:8790/health',['capture_frames','capture_hz','detection_hz','camera_error','detector_error'])
m=json.loads(Path('/boot/aura-native-firstmode-20261021/manifest.json').read_text())
v['installed_targets_verified']=all(hashlib.sha256(Path(i['path']).read_bytes()).hexdigest()==i['after_sha256'] for i in m['targets'])
v['protected_files_verified']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==s for p,s in m['protected'].items())
kernel=subprocess.check_output(['dmesg'],text=True)
v['kernel_display']=[s for s in kernel.splitlines() if re.search(r'fb0|frame buffer|zynqmp-display|Kernel command line|underflow|training.*(?:error|fail)',s,re.I)]
v['native_first_mode_verified']=(boot!='bec99c5a-5292-4a3e-b180-c52187d6c47b' and v['fbdev_emulation']=='N' and not v['framebuffers'] and v['xorg_initial_modes']==['1024x600'] and '1024x768' not in v['display'] and '49.000MHz -HSync -VSync *current' in v['display'] and v['installed_targets_verified'] and v['protected_files_verified'])
print(json.dumps(v),flush=True)
'''

if __name__=='__main__':
    observer.main()
