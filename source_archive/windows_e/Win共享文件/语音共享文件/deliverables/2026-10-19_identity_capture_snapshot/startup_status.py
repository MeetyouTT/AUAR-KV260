"""Read-only systemd/launcher diagnostics during UI activation."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,subprocess
from pathlib import Path
def run(args):return subprocess.run(args,capture_output=True,text=True,timeout=10).stdout
out={'unit':run(['systemctl','show','aura-avatar-ui.service','-p','MainPID,ActiveState,SubState,ExecMainStatus,Type,TimeoutStartUSec']),
 'journal':run(['journalctl','-u','aura-avatar-ui.service','-n','22','--no-pager','-o','cat'])}
root=Path(RUNTIME)/'managed-runs'
logs=sorted(root.glob('*/stage.log'),key=lambda p:p.stat().st_mtime)
if logs:out['child_stage_log']=logs[-1].read_text(errors='replace')[-6500:]
print(json.dumps(out))
'''
remote=remote.replace('RUNTIME',repr(json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))['runtime']),1)
r=json.loads(ssh('python3 -B -',remote,timeout=25))
(HERE/'startup_status.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False))
