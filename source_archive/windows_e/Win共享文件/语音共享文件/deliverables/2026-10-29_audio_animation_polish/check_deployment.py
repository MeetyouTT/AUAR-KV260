import json
from board_guard import H,ssh
c=json.loads((H/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import json,subprocess
from pathlib import Path
stage=Path(STAGE);path=stage/'deployment.json'
report=json.loads(path.read_text()) if path.exists() else {}
print(json.dumps({'transaction_status':report.get('status'),'error':report.get('error'),'rollback_error':report.get('rollback_error'),
 'unit':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','Result'],text=True),
 'stage_tail':(stage/'runtime/stage.log').read_text(errors='replace')[-2000:] if (stage/'runtime/stage.log').exists() else '',
 'supervisor_log':subprocess.check_output(['journalctl','-u','aura-avatar-ui.service','-n','12','--no-pager','-o','cat'],text=True)[-2500:]}))
'''.replace('STAGE',repr(c['stage']))
print(ssh('python3 -B -',script,timeout=15))
