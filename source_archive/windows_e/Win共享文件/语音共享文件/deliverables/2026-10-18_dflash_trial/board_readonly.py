"""Find the current vision process rather than trusting a historical PID."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
script='''import json,pathlib,urllib.request,subprocess
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
out={'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'state':{k:v for k,v in s.items() if any(t in k.lower() for t in ('camera','vision','health','source'))}}
try:out['camera_health']=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
except Exception as e:out['camera_health_error']=str(e)
out['units']=subprocess.check_output(['systemctl','list-units','--type=service','--all','--no-pager','--plain'],text=True)
out['units']='\\n'.join(line for line in out['units'].splitlines() if any(k in line.lower() for k in ('aura','camera','vision','dpu')))
print(json.dumps(out))
'''
value=json.loads(ssh('python3 -',script))
(Path(__file__).resolve().parent/'board_current.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value,ensure_ascii=True))
