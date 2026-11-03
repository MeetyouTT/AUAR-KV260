"""Restore previous UI only; current face service and user DB stay in place."""
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
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
assert not s['automatic_conversation']['enabled'] and s['local_recording']['state']!='RECORDING'
assert not s['local_transcription']['service']['pending']
unit=Path('/etc/systemd/system/aura-avatar-ui.service');assert d['runtime'] in unit.read_text()
backup=Path(d['backup']);metadata=json.loads((backup/'rollback.json').read_text())
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,timeout=40)
temp=unit.with_name(unit.name+'.voice-rollback')
if metadata['unit_link']:temp.symlink_to(metadata['unit_link'])
else:temp.write_bytes((backup/unit.name).read_bytes());temp.chmod(0o644)
os.replace(temp,unit)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=15)
print(json.dumps({'status':'PREVIOUS_UI_WITHOUT_QUERY_STARTING','camera_restarted':False,'identity_database_deleted':False}))
'''.replace('DEPLOYMENT',repr(d))
print(ssh('python3 -',remote,timeout=85))

