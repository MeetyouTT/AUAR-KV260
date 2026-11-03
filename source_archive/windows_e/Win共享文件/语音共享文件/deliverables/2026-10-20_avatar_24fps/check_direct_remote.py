import subprocess,json
print(json.dumps({'processes':subprocess.getoutput("ps -eo pid,etime,args | grep direct-display | head -8"),'service':subprocess.getoutput('systemctl is-active aura-avatar-ui.service')}))
