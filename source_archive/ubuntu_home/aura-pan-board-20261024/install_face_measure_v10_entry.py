import hashlib,json,subprocess
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');R=OPS/'pan-face-edge-v5/face-source-v10';p=R/'stage-state.json'
s=json.loads(p.read_text());assert s['phase']=='CAMERA_STOPPED_CHECKPOINT_PASS'
assert subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()=='0'
manifest=R/'deployment-manifest.json';digest=hashlib.sha256(manifest.read_bytes()).hexdigest();assert digest=='e69fa7f4aaad799856d546ba870b959362b1cf2039270d2f58a7f7141fd50cd6'
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in json.loads(manifest.read_text())['pins'].items())
drop=Path('/etc/systemd/system/aura-camera-ui.service.d/zzzzzzzzzzzzzzzzzzzzzzzzzzzzz-aura-face-measure-v10.conf');assert not drop.exists()
code="import hashlib,json;from pathlib import Path;p=Path("+repr(str(manifest))+");assert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(digest)+";assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in json.loads(p.read_text())['pins'].items())"
raw=('[Service]\nExecStart=\nExecStartPre=/usr/bin/python3 -B -c "'+code+'"\nExecStart=/usr/bin/python3 -B '+str(R/'entry.py')+'\nRestart=no\nSendSIGKILL=no\nKillMode=process\nTimeoutStopSec=infinity\n').encode()
with drop.open('xb') as f:f.write(raw)
subprocess.run(['systemctl','daemon-reload'],check=True);s.update(dropin=str(drop),dropin_sha256=hashlib.sha256(raw).hexdigest());p.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':'FACE_MEASURE_V6_ENTRY_PREPARED','dropin_sha256':s['dropin_sha256'],'camera_pid':0,'gui_restarted':False}))
