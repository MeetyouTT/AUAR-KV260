"""Read camera ownership and error class after a preflight connection refusal."""
import json,subprocess
def output(args):return subprocess.check_output(args,text=True,timeout=6).strip()
value={}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
 value[unit]={k:output(['systemctl','show',unit,'-p',k,'--value']) for k in ['ActiveState','SubState','MainPID','NRestarts','Result','ExecMainStatus','ExecMainStartTimestamp','WorkingDirectory']}
 raw=output(['journalctl','-u',unit,'--since','5 minutes ago','--no-pager','-o','cat'])
 value[unit]['errors']=[s[:400] for s in raw.splitlines() if any(token in s for token in ['Traceback','Error:','Exception:','AssertionError','Failed to','failed with result','Scheduled restart','Main process exited','Starting AURA','Started AURA','Stopped AURA'])][-25:]
value['zocl_refcnt']=output(['cat','/sys/module/zocl/refcnt'])
print(json.dumps(value),flush=True)
