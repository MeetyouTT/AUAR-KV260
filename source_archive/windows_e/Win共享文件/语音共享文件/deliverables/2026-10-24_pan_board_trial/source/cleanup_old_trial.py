import json,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
old=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4')
new=Path(str(old)+'-r2')
assert json.loads((old/'trial-state.json').read_text())['phase']=='BASELINE_RESTORED_AFTER_TRIAL_FAILURE'
assert json.loads((new/'trial-state.json').read_text())['phase']=='CANDIDATE_STOPPED_RETAINED_PHYSICAL_FEEDBACK_PENDING'
name='aura-pan-vsrv2-1236ccf4-activation.service'
p=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,LoadState'],capture_output=True,text=True)
info=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
assert info.get('MainPID')=='0'
if info.get('LoadState')=='loaded':
 p=subprocess.run(['systemctl','reset-failed',name],capture_output=True,text=True);assert p.returncode==0,p.stderr
print(json.dumps({'old_owned_failure_status_cleared':True,'failure_records_and_journal_preserved':True,
 'model_services_modified':False,'movement_commands_sent':0}))
