import json,subprocess
r={}
for name in ('aura-avatar-ui.service','aura-camera-ui.service'):
 r[name]=subprocess.check_output(['systemctl','show',name,'-p','ActiveState','-p','SubState','-p','ExecMainStatus','-p','Result','-p','MainPID','-p','TimeoutStartUSec'],text=True)
log=subprocess.check_output(['journalctl','-u','aura-avatar-ui.service','-n','50','--no-pager','-o','cat'],text=True)
keys=('error','failed','traceback','exception','timeout','starting','started','preflight','ready')
r['startup_lines']=[line[:350] for line in log.splitlines() if any(k in line.lower() for k in keys)]
print(json.dumps(r))
