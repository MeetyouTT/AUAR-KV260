"""Restore just the UI unit backed up by this performance deployment."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
d=json.loads((HERE/'performance_deployment.json').read_text())
remote=r'''
import json,os,subprocess,urllib.request
from pathlib import Path
d=DEPLOYMENT
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
assert s['phase']=='IDLE' and not s['playing'] and not s['automatic_conversation']['enabled']
assert s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']
unit=Path('/etc/systemd/system/aura-avatar-ui.service');assert d['runtime'] in unit.read_text()
backup=Path(d['backup']);meta=json.loads((backup/'rollback.json').read_text())
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,timeout=40)
tmp=unit.with_name(unit.name+'.performance-rollback')
if meta['unit_link']:tmp.symlink_to(meta['unit_link'])
else:tmp.write_bytes((backup/'aura-avatar-ui.service').read_bytes());tmp.chmod(0o644)
os.replace(tmp,unit)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=15)
print(json.dumps({'status':'PREVIOUS_UI_STARTING','camera_restarted':False,'pc_restarted':False}))
'''.replace('DEPLOYMENT',repr(d),1)
print(ssh('python3 -B -',remote,timeout=85))
