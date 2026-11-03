import json,subprocess
r={}
unit='aura-vart-phase-0b69843e8b7c38fa'
for key,args in [('state',['systemctl','show',unit,'-p','ActiveState','-p','ExecMainStatus','-p','Result']),
 ('own_journal',['journalctl','-u',unit,'-n','18','--no-pager','-o','cat'])]:
 r[key]=subprocess.check_output(args,stderr=subprocess.STDOUT,text=True)
print(json.dumps(r))
