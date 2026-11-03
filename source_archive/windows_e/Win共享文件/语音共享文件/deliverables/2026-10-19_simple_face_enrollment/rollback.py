"""Restore the previous board units; never delete or restore identity data."""
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
state=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
assert state['phase']=='IDLE' and not state['playing'] and state['local_recording']['state']!='RECORDING'
assert not state['automatic_conversation']['enabled']
backup=Path(d['backup']);assert backup.parent.parent==Path('/home/root/aura-simple-enrollment-20261019')
links=json.loads((backup/'rollback.json').read_text())['unit_links']
paths={name:Path('/etc/systemd/system')/name for name in links}
for path in paths.values():assert str(backup.parent) in path.read_text()
subprocess.run(['systemctl','stop',*paths],check=True,timeout=45)
for name,path in paths.items():
 temp=path.with_name(path.name+'.face-rollback')
 if links[name]:temp.symlink_to(links[name])
 else:temp.write_bytes((backup/name).read_bytes());temp.chmod(0o644)
 os.replace(temp,path)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
subprocess.run(['systemctl','start','--no-block',*paths],check=True,timeout=15)
print(json.dumps({'status':'PREVIOUS_BOARD_UNITS_RESTORED_STARTING','identity_database_untouched':True}))
'''.replace('DEPLOYMENT',repr(d),1)
print(ssh('python3 -B -',remote,timeout=90))
