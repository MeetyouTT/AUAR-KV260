import subprocess,json
from pathlib import Path
print(json.dumps({'unit':subprocess.getoutput('systemctl status aura-avatar-ui.service --no-pager'), 'journal':subprocess.getoutput('journalctl -u aura-avatar-ui.service -n 45 --no-pager'),'processes':subprocess.getoutput("ps -eo pid,ppid,pcpu,etime,args | grep -E 'board_avatar|launcher.py|camera_motion' | head -15")}))
