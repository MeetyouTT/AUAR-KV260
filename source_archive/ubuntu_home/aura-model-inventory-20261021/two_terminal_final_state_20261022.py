import json,time,subprocess,urllib.request,hashlib
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:s=json.load(f)
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
raw=subprocess.check_output(['journalctl','-k','-n','1000','-o','json','--no-pager'],timeout=5).decode();rows=[json.loads(x) for x in raw.splitlines() if x.strip()];warn=[x for x in rows if "WARN: HC couldn't access mem fast enough" in x.get('MESSAGE','')]
print(json.dumps({'read_only':True,'mono':time.monotonic(),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'pid':s['pid'],'camera_error':s.get('camera_error'),'detector_error':s.get('detector_error'),'face_health':s.get('identity',{}).get('face_targets'),'schedule':s.get('dpu_schedule'),'ui':{k:u.get(k) for k in ('phase','playing','paused','audio_output_state')},'recording_state':u.get('local_recording',{}).get('state'),'transcription_pending':u.get('local_transcription',{}).get('service',{}).get('pending'),'last_usb_warning_mono_us':warn[-1].get('__MONOTONIC_TIMESTAMP') if warn else None,'camera_unit_sha256':hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()}))
