"""Refresh only this task's inactive candidate sources and their strict pins."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
files={n:(HERE/'candidate_source'/n if n=='tools/board_avatar_gtk.py' else AURA/n).read_text(encoding='utf-8') for n in c['changes']}
files['tests/framework/test_portrait_offload.py']=(AURA/'tests/framework/test_portrait_offload.py').read_text(encoding='utf-8')
script=r'''
import base64,hashlib,json,os,subprocess
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);files=json.loads(base64.b64decode(DATA))
assert c['startup'] not in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
config=Path(c['startup'])/'config.json';cfg=json.loads(config.read_text())
for relative,text in files.items():
    p=root/'aura'/relative;assert p.resolve().is_relative_to(root.resolve())
    p.write_text(text);cfg['component_sha256'][relative]=hashlib.sha256(p.read_bytes()).hexdigest()
config.write_text(json.dumps(cfg,indent=2))
pre=subprocess.run(['python3','-B',str(config.with_name('launcher.py')),'--config',str(config),'--preflight'],env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
assert pre.returncode==0,pre.stdout+pre.stderr
print(json.dumps({'candidate_refreshed_files':len(files),'preflight':pre.stdout.strip(),'production_changed':False}))
'''.replace('CANDIDATE',repr(c)).replace('DATA',repr(base64.b64encode(json.dumps(files).encode()).decode()))
print(ssh('python3 -B -',script,timeout=40))
