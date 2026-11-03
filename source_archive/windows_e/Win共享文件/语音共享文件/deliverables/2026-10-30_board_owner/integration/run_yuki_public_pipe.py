"""One root-pinned public-pipe inspection or bounded execution."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
from resume_baseline import write_json

SHA='b9bf2135c2f63e1b5b58226039e0f5ae893eeffe9860884ad1f8d3b535171684'
ROOT='/home/root/aura-board-owner-candidate-20261030/ui-round2-4750fc97e43a75bd'
CONTROL='/home/root/aura-board-owner-candidate-20261030/ui-capacity-control-20261030-r2'
SCRIPT=r'''
import base64,hashlib,json,os,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
raw=base64.b64decode(SOURCE,validate=True);assert hashlib.sha256(raw).hexdigest()==SHA
p=Path(CONTROL)/('public-pipe-'+SHA[:16]+'.py');assert not p.is_symlink()
if p.exists():assert p.read_bytes()==raw
else:
 fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
live=json.loads((Path(CONTROL)/'candidate_owner.json').read_bytes())['owner']
assert all(live[k]==OWNER[k] for k in ('pid','birth','cmdline_sha256'))
argv=['/usr/bin/python3','-B',str(p),ACTION,'--probe-file','/home/root/aura-board-owner-candidate-20261030/perf-fa0bc04a6f8c15a9/probe.py',
 '--control-file',ROOT+'/control_round2.py','--policy',ROOT+'/policy.json',
 '--candidate-pid',str(OWNER['pid']),'--candidate-birth',OWNER['birth'],'--candidate-cmdline-sha256',OWNER['cmdline_sha256']]
done=subprocess.run(argv,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=170)
try:value=json.loads(done.stdout)
except ValueError:value=dict(status='INVALID_RESULT',stderr=done.stderr[-1000:])
print(json.dumps(dict(returncode=done.returncode,result=value)))
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('inspect','run'),default='inspect',nargs='?');parser.add_argument('--repeat',action='store_true');args=parser.parse_args()
    raw=(HERE/'resume_yuki_pipe_capacity/public_pipe_capacity_v2.py').read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    owner=json.loads((HERE/'resume_ui_trial_round2/actual_launch.json').read_text(encoding='utf-8'))['result']['owner']
    values=dict(SHA=SHA,ROOT=ROOT,CONTROL=CONTROL,SOURCE=base64.b64encode(raw).decode(),ACTION=args.action,OWNER=owner)
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    result=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=185))
    path=HERE/'resume_yuki_pipe_capacity'/('actual_round2_'+args.action+('_repeat' if args.repeat else '')+'.json')
    write_json(path,dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**result))
    value=result['result'];probe=value.get('probe_result',{})
    print(json.dumps(dict(output=str(path),returncode=result['returncode'],status=value.get('status'),error=value.get('error_code'),failure=value.get('failure_type'),probe_status=probe.get('status'),input_queue=probe.get('input_queue'),runs=probe.get('runs'),frontend=probe.get('frontend_processing_ms')),ensure_ascii=True))

if __name__=='__main__':main()
