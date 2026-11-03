"""Read active camera/UI launchers and identity prerequisites; no mutations."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

remote = r'''
import hashlib,json,subprocess,urllib.request
from pathlib import Path
def run(args):return subprocess.check_output(args,text=True,timeout=10).strip()
def get(port,path):
 try:return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=5))
 except Exception as e:return {'unavailable':str(e)}
health=get(8790,'/health');ui=get(8783,'/api/state');camera=get(8790,'/v1/ui/status')
pid=health.get('pid')
command=Path('/proc/%d/cmdline'%pid).read_bytes().replace(b'\0',b' ').decode() if pid else None
cwd=str(Path('/proc/%d/cwd'%pid).resolve()) if pid else None
units=run(['systemctl','list-units','--type=service','--all','--plain','--no-legend'])
names=[line.split()[0] for line in units.splitlines() if any(s in line.lower() for s in ('camera','vision','avatar-ui'))]
result={'health':health,'camera_command':command,'camera_cwd':cwd,
 'camera_status':{k:v for k,v in camera.items() if k!='preview'},
 'ui':{k:ui.get(k) for k in ('phase','automatic_conversation','local_recording','local_transcription')},
 'units':{n:{'unit':run(['systemctl','cat',n]),'properties':run(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,Result,ExecMainStatus'])} for n in names},'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
print(json.dumps(result))
'''
result=json.loads(ssh('python3 -',remote,timeout=40))
(HERE/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
