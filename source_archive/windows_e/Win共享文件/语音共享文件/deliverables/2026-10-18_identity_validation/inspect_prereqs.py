import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
path=Path(re.search(r'--config (\S+)',unit).group(1));cfg=json.loads(path.read_text());root=Path(cfg['runtime'])
names=['tools/board_avatar_gtk.py','board/interaction/ui_contract.py','board/interaction/services.py']
state=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
report={'ui_config_path':str(path),'ui_config':cfg,
 'ui_sources':{n:hashlib.sha256((root/'aura'/n).read_bytes()).hexdigest() for n in names if (root/'aura'/n).is_file()},
 'ui_phase':state.get('phase'),'automatic':state.get('automatic_conversation'),
 'static_log':(Path(c['stage'])/'static_reference.log').read_text(),
 'memory_db_exists':Path('/home/root/.local/share/aura/identities.sqlite3').exists(),
 'camera_properties':subprocess.check_output(['systemctl','show','aura-camera-ui.service','--property=MainPID,ActiveState'],text=True)}
print(json.dumps(report))
'''.replace('CANDIDATE',repr(c))
r=json.loads(ssh('python3 -',remote,timeout=30))
(HERE/'prereqs.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True))
