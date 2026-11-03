import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import json,subprocess
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
value={'report':json.loads((stage/'deployment.json').read_text()),
       'stage_log':(root/'stage.log').read_text()[-5500:] if (root/'stage.log').exists() else '',
       'entry_source':(root/'aura/tools/board_avatar_pan.py').read_text(),
       'journal':subprocess.check_output(['journalctl','-u','aura-avatar-ui.service','-n','22','--no-pager'],text=True)[-4000:]}
print(json.dumps(value))
'''.replace('CANDIDATE',repr(c))
value=json.loads(ssh('python3 -B -',script,timeout=20))
(HERE/'trial_failure_detail.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':value['report']['status'],'error':value['report'].get('error'),'stage_log':value['stage_log'],'journal':value['journal']}))
print(value['entry_source'])
