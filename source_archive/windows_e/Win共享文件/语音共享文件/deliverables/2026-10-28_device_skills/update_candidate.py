import base64,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((H/'candidate.json').read_text());name='tools/voice_first_recording.py';raw=(H/'candidate_source'/name).read_bytes()
script=r'''
import base64,hashlib,json,subprocess
from pathlib import Path
c=C;name=NAME;raw=base64.b64decode(RAW);root=Path(c['runtime'])/'aura'
assert c['source_startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert hashlib.sha256((root/name).read_bytes()).hexdigest()==c['pins'][name]
(root/name).write_bytes(raw);cfgp=Path(c['startup'])/'config.json';cfg=json.loads(cfgp.read_text())
cfg['component_sha256'][name]=hashlib.sha256(raw).hexdigest();cfgp.write_text(json.dumps(cfg,indent=2))
c['pins']=cfg['component_sha256'];(Path(c['stage'])/'candidate.json').write_text(json.dumps(c,indent=2));print(json.dumps(c))
'''.replace('C;',repr(c)+';').replace('NAME',repr(name)).replace('RAW',repr(base64.b64encode(raw).decode()))
v=json.loads(ssh('python3 -B -',script));(H/'candidate.json').write_text(json.dumps(v,indent=2));print('Candidate social interruption fix updated; not deployed')
