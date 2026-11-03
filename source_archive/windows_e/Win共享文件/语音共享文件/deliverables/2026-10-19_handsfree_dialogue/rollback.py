"""Restore previous board UI/camera units, retaining all user data."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
remote=r'''
import json,os,subprocess,time,urllib.request,uuid
from pathlib import Path
d=DEPLOYMENT
get=lambda:json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
s=get();assert not s['local_transcription']['service'].get('voice_enrollment',{}).get('active')
# The current feature owns this listener. Normal cancel pauses it permanently.
r=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':'event','event':'cancel'}).encode(),
 headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
with urllib.request.urlopen(r,timeout=4) as response:response.read()
for _ in range(40):
 s=get()
 if s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']:break
 time.sleep(.1)
assert not s['playing'] and not s['automatic_conversation']['enabled']
units=json.loads((Path(d['backup'])/'rollback.json').read_text())
for name in units:subprocess.run(['systemctl','stop',name],check=True,timeout=40)
for name,old in units.items():
 path=Path('/etc/systemd/system')/name;tmp=path.with_name(path.name+'.rollback-'+uuid.uuid4().hex[:6])
 if old['link']:tmp.symlink_to(old['link'])
 else:tmp.write_text(old['text']);tmp.chmod(0o644)
 os.replace(tmp,path)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
for name in ('aura-camera-ui.service','aura-avatar-ui.service'):
 subprocess.run(['systemctl','start','--no-block',name],check=True,timeout=20)
print(json.dumps({'status':'PREVIOUS_BOARD_UNITS_STARTING','database_deleted':False,'photos_deleted':False}))
'''.replace('DEPLOYMENT',repr(d),1)
print(ssh('python3 -B -',remote,timeout=130))
