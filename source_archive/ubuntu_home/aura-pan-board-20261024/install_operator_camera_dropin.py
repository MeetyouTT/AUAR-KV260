"""Stage the owned bootstrap only after the exact old checkpoint passed."""
import hashlib,json,subprocess
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');R=OPS/'pan-face-edge-v5/native-operator-v1';p=R/'stage-state.json'
s=json.loads(p.read_text());assert s['phase']=='CAMERA_STOPPED_CHECKPOINT_PASS'
assert subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()=='0'
m=R/'runtime-manifest.json';digest=hashlib.sha256(m.read_bytes()).hexdigest();assert digest==s['runtime_manifest_sha256']
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in json.loads(m.read_text())['files'].items())
entry=R/'native_entry_operator.py';drop=Path('/etc/systemd/system/aura-camera-ui.service.d/zzzzzzzzzzzzzzzzzzzzzzzz-aura-identity-operator-v1.conf');assert not drop.exists()
code="import hashlib,json;from pathlib import Path;p=Path("+repr(str(m))+");assert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(digest)+";assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in json.loads(p.read_text())['files'].items())"
raw=('[Service]\nExecStart=\nExecStartPre=/usr/bin/python3 -B -c "'+code+'"\nExecStart=/usr/bin/python3 -B '+str(entry)+'\nRestart=no\nSendSIGKILL=no\nKillMode=process\nTimeoutStopSec=infinity\n').encode()
with drop.open('xb') as f:f.write(raw)
subprocess.run(['systemctl','daemon-reload'],check=True)
shown=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','ExecStart','-p','MainPID','-p','LoadState','-p','LoadError'],text=True)
assert 'MainPID=0' in shown and str(entry) in shown and 'LoadState=loaded' in shown
s.update(dropin=str(drop),dropin_sha256=hashlib.sha256(raw).hexdigest());p.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':'OPERATOR_ENTRY_STAGED_CHECKPOINT_PRESERVED','dropin_sha256':s['dropin_sha256'],'camera_pid':0,'gui_restarted':False}))
