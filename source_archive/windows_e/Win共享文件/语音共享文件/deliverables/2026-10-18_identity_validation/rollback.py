"""Restore the exact previous units after stopping conversation; keep user DB."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
remote=r'''
import json,os,subprocess,urllib.request
from pathlib import Path
d=DEPLOYMENT;backup=Path(d['backup'])
assert backup.parent.parent==Path('/home/root/aura-identity-validation-20261018')
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
assert not s.get('automatic_conversation',{}).get('enabled') and s['local_recording']['state']!='RECORDING'
assert not s['local_transcription']['service']['pending']
current=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
assert d['runtime'] in current,'Active release differs; refusing to replace unrelated work'
metadata=json.loads((backup/'rollback.json').read_text())
subprocess.run(['systemctl','stop','aura-avatar-ui.service','aura-camera-ui.service'],check=True,timeout=40)
for n in ('aura-camera-ui.service','aura-avatar-ui.service'):
 path=Path('/etc/systemd/system')/n;temporary=path.with_name(path.name+'.identity-rollback')
 link=metadata['unit_links'].get(n)
 if link:temporary.symlink_to(link)
 else:temporary.write_bytes((backup/n).read_bytes());temporary.chmod(0o644)
 os.replace(temporary,path)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service','aura-avatar-ui.service'],check=True,timeout=15)
print(json.dumps({'status':'PREVIOUS_UNITS_RESTORED_STARTING','identity_database_deleted':False,
 'pc_services_restarted':False,'backup':str(backup)}))
'''.replace('DEPLOYMENT',repr(d))
print(ssh('python3 -',remote,timeout=85))
