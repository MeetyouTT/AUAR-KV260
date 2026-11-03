import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import json,subprocess
from pathlib import Path
stage=Path(STAGE)
report=json.loads((stage/'deployment.json').read_text()) if (stage/'deployment.json').exists() else {'status':'NO_DEPLOYMENT_FILE'}
print(json.dumps({'report':report,'effective':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths','-p','ActiveState'],text=True),
 'watchdog_rollback':(stage/'watchdog_rollback.json').exists(),'committed':(stage/'committed').exists()}))
'''.replace('STAGE',repr(c['stage']))
value=json.loads(ssh('python3 -B -',script,timeout=15))
(HERE/'trial_state_after_error.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'report_status':value['report']['status'],'error':value['report'].get('error'),
                 'committed':value['committed'],'watchdog_rollback':value['watchdog_rollback'],'effective':value['effective']}))
