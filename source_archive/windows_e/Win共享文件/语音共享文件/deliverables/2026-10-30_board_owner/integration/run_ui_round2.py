"""Root transport; performs exactly one explicitly named round2 step."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
from resume_baseline import write_json

MANIFEST='4750fc97e43a75bd31b20db5b8764fb6df3595545d2a78f92978531988ea9460'
ROOT='/home/root/aura-board-owner-candidate-20261030/ui-round2-'+MANIFEST[:16]
SCRIPT=r'''
import base64,hashlib,json,os,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
r=Path(ROOT);assert r.parent==Path('/home/root/aura-board-owner-candidate-20261030') and not r.is_symlink()
r.mkdir(mode=0o700,exist_ok=True);assert r.resolve()==r and r.stat().st_mode&0o077==0
for name,(payload,pin) in FILES.items():
 raw=base64.b64decode(payload,validate=True);assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
 p=r/name;assert p.parent==r and not p.is_symlink()
 if p.exists():assert p.read_bytes()==raw
 else:
  fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
env=dict(os.environ);env.update(DISPLAY_ENV)
done=subprocess.run(['/usr/bin/python3','-B',str(r/'trial.py')]+ARGV,env=env,capture_output=True,text=True,timeout=115)
try:value=json.loads(done.stdout)
except ValueError:value=dict(status='INVALID_RESULT',error=done.stderr[-1500:])
print(json.dumps(dict(returncode=done.returncode,result=value)))
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('step',choices=('guard-inspect','guard-install','guard-cancel','original-inspect','original-close','launch-inspect','launch','candidate-inspect','candidate-close','restore-inspect','restore'))
    parser.add_argument('--natural-exit',action='store_true');args=parser.parse_args()
    folder=HERE/'resume_ui_trial_round2';raw=(folder/'manifest.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==MANIFEST
    manifest=json.loads(raw);assert set(manifest['files'])=={'trial.py','control_round2.py','launch_round2.py','port_wait.py','x11_close.py','policy.json','original_gui.plan.json'}
    files={}
    for name,pin in manifest['files'].items():
        raw=(folder/name).read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
        files[name]=(base64.b64encode(raw).decode(),pin)
    argv=[args.step,'--policy-sha256',manifest['policy_sha256']]
    if args.step=='guard-install':
        checked=json.loads((folder/'actual_guard-inspect.json').read_text(encoding='utf-8'))['result']
        assert checked['status']=='GUARD_INSPECTED_NO_MUTATION'
        argv+=['--inspection-sha256',checked['inspection_sha256']]
    if args.step in ('original-close','candidate-close'):
        checked=json.loads((folder/('actual_'+args.step.replace('-close','-inspect')+'.json')).read_text(encoding='utf-8'))['result']
        assert checked['status']=='INSPECTED' and checked['close_guard_ready'] is True
        argv+=['--review-token',checked['review_token'],'--window-id',str(checked['window']['window_id'])]
    if args.natural_exit:argv+=['--candidate-exited-naturally']
    env=json.loads((HERE/'resume_ui_trial/actual_ui_baseline.json').read_text(encoding='utf-8'))['display_environment']
    values=dict(ROOT=ROOT,FILES=files,DISPLAY_ENV=env,ARGV=argv)
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    value=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=130))
    target=folder/('actual_'+args.step+('_natural' if args.natural_exit else '')+'.json')
    write_json(target,value);print(json.dumps(dict(output=str(target),**value),ensure_ascii=True))

if __name__=='__main__':main()
