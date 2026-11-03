"""Verify the candidate boot and independent application frame progress."""
import hashlib,json,re,subprocess,time,urllib.request
from pathlib import Path
root=Path('/boot/aura-hdmi-preinit-20261021')
meta=json.loads((root/'before.json').read_text())
assert Path('/sys/module/zynqmp_dpsub/parameters/initial_aux_delay_ms').read_text().strip()=='5000'
assert Path('/sys/module/zynqmp_dpsub/parameters/power_on_delay_ms').read_text().strip()=='4'
assert hashlib.sha256(Path('/boot/uEnv.txt').read_bytes()).hexdigest()==meta['candidate_uenv_sha256']
assert hashlib.sha256((Path('/boot')/meta['candidate_image_name']).read_bytes()).hexdigest()==meta['candidate_image_sha256']
assert {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in meta['protected_hashes']}==meta['protected_hashes']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url,keys):
 try:
  with op.open(url,timeout=2) as r:s=json.load(r)
  return {k:s.get(k) for k in keys}
 except Exception as e:return {'error':str(e)}
def sample():
 raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
 return {'uptime':Path('/proc/uptime').read_text().split()[0],'edid_bytes':len(raw),'edid_sha256':hashlib.sha256(raw).hexdigest(),'gui':get('http://127.0.0.1:8783/api/state',['phase','ui_page','error','avatar_display']),'camera':get('http://127.0.0.1:8790/health',['pid','capture_frames','capture_hz','detection_hz','identity_recognition','camera_error','detector_error'])}
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'before':sample()};time.sleep(8);v['after']=sample()
v['units']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True,timeout=5)
v['display']=subprocess.check_output(['env','DISPLAY=:0','xrandr','--current'],text=True,timeout=10)
d=subprocess.check_output(['dmesg'],text=True)
v['delay_log']=[x for x in d.splitlines() if 'AURA initial AUX' in x]
stamps=[float(re.search(r'^\[\s*([0-9.]+)\]',x)[1]) for x in v['delay_log']]
v['measured_initial_wait_seconds']=round(stamps[1]-stamps[0],6) if len(stamps)==2 else None
v.update(protected_files_unchanged=True,files_modified=0,display_commands_sent=0,movement_commands_sent=0,coldboot_verified=False,physical_panel_verified=False)
print(json.dumps(v),flush=True)
