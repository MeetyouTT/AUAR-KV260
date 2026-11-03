import hashlib,json,os,subprocess,time
from pathlib import Path
startup=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/startup/config.json');cfg=json.loads(startup.read_text())
runtime=Path(cfg['runtime']);launch=json.loads((runtime/'launch.json').read_text())
session=Path(launch['session']);setup=json.loads((session/'setup.json').read_text())
edid=Path(cfg['edid_file']);raw=edid.read_bytes()
env=dict(os.environ,DISPLAY=cfg['display'])
run=subprocess.run(['xrandr','--verbose'],env=env,capture_output=True,text=True,timeout=8)
fields=['output','mode','rate','startup_display_retrain','display_recovery_marker','display_retrain_off_seconds','display_stable_seconds','display_wait_seconds','edid_grace_seconds','edid_sha256','verified_timing_fallback']
print(json.dumps({'scope':'read-only cold-start display record after user-confirmed physical HDMI recovery',
 'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),
 'display_configuration':{k:cfg.get(k) for k in fields},'startup_setup':setup,
 'current_edid_bytes':len(raw),'current_edid_sha256':hashlib.sha256(raw).hexdigest(),
 'current_connector_status':edid.with_name('status').read_text().strip(),
 'xrandr_exit':run.returncode,'xrandr_verbose':run.stdout,
 'kernel_display_lines':subprocess.check_output(['journalctl','-b','-k','--no-pager','-o','cat'],text=True).splitlines()[-200:]}))
