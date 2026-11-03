import json
from maintenance import H,save,capture
from board_guard import ssh
script=r'''
import json,subprocess
from pathlib import Path
stage=Path('/home/root/aura-board-vision-20261030/06391079cfddb734')
result={'unit':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Result'],text=True)}
lines=subprocess.check_output(['journalctl','-u','aura-avatar-ui.service','-n','65','--no-pager','-o','cat'],text=True).splitlines()
result['startup_diagnostics']=[line for line in lines if any(word in line.lower() for word in ('error','failed','traceback','mismatch','launcher','config','exception'))]
result['candidate_logs']={}
for name in ('startup/launcher.log','startup/stderr.log','startup/stdout.log','deployment.json'):
    p=stage/name
    if p.is_file():result['candidate_logs'][name]=p.read_text(errors='replace')[-7000:]
print(json.dumps(result))
'''
value=json.loads(ssh('python3 -B -',script,timeout=15));save('board_first_failure_diagnostics.json',value)
print(json.dumps(value))
try:
    current=capture();save('board_after_rollback.json',current)
    print(json.dumps({'rollback_safe':current['safe'],'runtime':current['actual_runtime'],'mismatches':current['mismatches'],'ui':current['ui']['MainPID']}))
except Exception as exc:print(type(exc).__name__+': '+str(exc))
