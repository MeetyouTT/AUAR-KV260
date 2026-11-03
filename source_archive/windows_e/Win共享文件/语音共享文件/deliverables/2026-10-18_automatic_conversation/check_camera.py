"""Audit a changed camera PID; never restart or configure vision services."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,subprocess,urllib.request
from pathlib import Path
camera=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
def run(args):return subprocess.run(args,capture_output=True,text=True,timeout=12).stdout
units=[line.split()[0] for line in run(['systemctl','list-units','--type=service','--all','--plain','--no-legend']).splitlines() if any(word in line.lower() for word in ('camera','yolox','vision'))]
result={'health':camera,'process_command':Path('/proc/%d/cmdline'%camera['pid']).read_bytes().replace(b'\0',b' ').decode(),
        'units':{unit:{'properties':run(['systemctl','show',unit,'--property=MainPID,NRestarts,ActiveEnterTimestampMonotonic,ExecMainStartTimestampMonotonic,Result']),
                       'journal':run(['journalctl','-b','-u',unit,'--no-pager','-n','45','-o','short-monotonic'])} for unit in units}}
print(json.dumps(result))
'''
result=json.loads(ssh('python3 -',remote,timeout=45))
(HERE/'camera_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pid':result['health']['pid'],'units':result['units']},ensure_ascii=True))
