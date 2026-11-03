import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import json
from pathlib import Path
root=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1')
config=json.loads((root/'startup/config.json').read_text())
value={'config':config,'launcher_source':(root/'startup/launcher.py').read_text(),
       'runtime_entries':[{'name':p.name,'symlink':p.is_symlink(),'directory':p.is_dir()} for p in (root/'runtime').iterdir()]}
print(json.dumps(value))
'''
value=json.loads(ssh('python3 -B -',script,timeout=15))
(HERE/'board_launcher.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'config':value['config'],'runtime_entries':value['runtime_entries']}))
print(value['launcher_source'])
