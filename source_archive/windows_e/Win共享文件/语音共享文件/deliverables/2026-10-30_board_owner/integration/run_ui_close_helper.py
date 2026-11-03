"""Root wrapper for reviewed source-only X11 inspection/normal-close helper."""
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

SHA='373c150f91867f00eddfe772cdecb065d51a449b822630542cf8287a3b6381ca'
PLAN='eab89f18a59e8f3bf63996ef3d213523d49544a54540c8e5789955108b190fa1'
ROOT='/home/root/aura-board-owner-candidate-20261030/ui-helper-'+SHA[:16]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--request-close',action='store_true');args=parser.parse_args()
    folder=HERE/'resume_ui_trial';baseline=json.loads((folder/'actual_ui_baseline.json').read_text(encoding='utf-8'))
    files={'x11_normal_close.py':(folder/'x11_normal_close_bin.py',SHA),
           'original_gui.plan.json':(folder/'original_gui.plan.json',PLAN)}
    for path,expected in files.values():assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    argv=['/usr/bin/python3','-B',ROOT+'/x11_normal_close.py','--plan',ROOT+'/original_gui.plan.json','--plan-sha256',PLAN]
    if args.request_close:
        previous=json.loads((folder/'actual_x11_inspect.json').read_text(encoding='utf-8'))['result']
        assert previous['close_guard_ready'] is True
        argv+=['--request-close','--review-token',previous['review_token'],'--window-id',str(previous['window']['window_id'])]
    script='''import base64,hashlib,json,os,subprocess\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\nr=Path(ROOT);assert not r.is_symlink() and r.parent==Path('/home/root/aura-board-owner-candidate-20261030')\nr.mkdir(mode=0o700,exist_ok=True);assert r.stat().st_mode&0o077==0\nfor name,payload in FILES.items():\n b=base64.b64decode(payload[0],validate=True);assert hashlib.sha256(b).hexdigest()==payload[1]\n q=r/name;assert not q.is_symlink()\n if q.exists():assert q.read_bytes()==b\n else:\n  fd=os.open(str(q),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n  with os.fdopen(fd,'wb') as out:out.write(b);out.flush();os.fsync(out.fileno())\nenv=dict(os.environ);env.update(ENV)\nv=subprocess.run(ARGV,env=env,capture_output=True,text=True,timeout=35)\nprint(json.dumps(dict(returncode=v.returncode,stdout=v.stdout,stderr=v.stderr)))'''
    values=dict(BOOT='8100a7fd-0c6a-46c4-82b8-f874988a1521',ROOT=ROOT,ARGV=argv,
        ENV=baseline['display_environment'],FILES={n:(base64.b64encode(p.read_bytes()).decode(),h) for n,(p,h) in files.items()})
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    result=json.loads(ssh('python3 -B -',prefix+script,timeout=45))
    result['result']=json.loads(result['stdout'])
    name='actual_x11_close.json' if args.request_close else 'actual_x11_inspect.json'
    write_json(folder/name,result)
    print(json.dumps(dict(output=str(folder/name),returncode=result['returncode'],result=result['result']),ensure_ascii=True))


if __name__=='__main__':main()
