"""Restore the camera unit only; preserve current UI, models and biometric DB."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
remote=r'''
import json,os,subprocess,urllib.request
from pathlib import Path
d=DEPLOYMENT
u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
assert u['phase']=='IDLE' and not u['playing'] and not u['automatic_conversation']['enabled']
assert u['local_recording']['state']!='RECORDING' and not u['local_transcription']['service']['pending']
assert not u['local_transcription']['service']['voice_enrollment']['active']
unit=Path('/etc/systemd/system/aura-camera-ui.service');assert d['runtime'] in unit.read_text()
backup=Path(d['backup']);assert backup.parent.parent==Path('/home/root/aura-enrollment-photos-20261019')
link=json.loads((backup/'rollback.json').read_text())['unit_link']
subprocess.run(['systemctl','stop','aura-camera-ui.service'],check=True,timeout=45)
temp=unit.with_name(unit.name+'.frontal-rollback')
if link:temp.symlink_to(link)
else:temp.write_bytes((backup/unit.name).read_bytes());temp.chmod(0o644)
os.replace(temp,unit)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=15)
print(json.dumps({'status':'PREVIOUS_CAMERA_POLICY_STARTING','ui_restarted':False,'identity_database_changed':False}))
'''.replace('DEPLOYMENT',repr(d),1)
print(ssh('python3 -B -',remote,timeout=85))
