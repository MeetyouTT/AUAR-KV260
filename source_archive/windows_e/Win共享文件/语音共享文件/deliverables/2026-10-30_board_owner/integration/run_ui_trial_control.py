"""Root transport for the reviewed serial synthetic GUI lifecycle."""
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

PINS={'restore_v2.py':'1d4b0a2e86f4a681e3953cd467c19b1ac83f4f990f278047c5c8fec5307a132c',
      'launch_v2.py':'d87375185bfb5c5f2956a0b4400966ec1c2c2717c1c64dc2f83312e7575c3a71',
      'ui_trial_policy.v2.json':'77fd6821d70ff4200e2becbe9832b94606f936bd2f69e7fe460046114e1ccf83'}
ROOT='/home/root/aura-board-owner-candidate-20261030/ui-controls-'+PINS['restore_v2.py'][:16]
CONTROL='/home/root/aura-board-owner-candidate-20261030/ui-capacity-control-20261030'
X11='/home/root/aura-board-owner-candidate-20261030/ui-helper-373c150f91867f00/x11_normal_close.py'
X11SHA='373c150f91867f00eddfe772cdecb065d51a449b822630542cf8287a3b6381ca'
SCRIPT=r'''
import base64,hashlib,json,os,subprocess,sys
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
r=Path(ROOT);assert not r.is_symlink() and r.parent==Path('/home/root/aura-board-owner-candidate-20261030')
r.mkdir(mode=0o700,exist_ok=True);assert r.stat().st_mode&0o077==0
def put(path,data):
 p=Path(path);assert not p.is_symlink() and p.parent.resolve()==p.parent
 if p.exists():assert p.read_bytes()==data
 else:
  fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
for name,(payload,expected) in FILES.items():
 data=base64.b64decode(payload,validate=True);assert hashlib.sha256(data).hexdigest()==expected;put(r/name,data)
sys.path.insert(0,str(r));import restore_v2 as c
policy=c.read_policy(str(r/'ui_trial_policy.v2.json'),PINS['ui_trial_policy.v2.json'])
env=dict(os.environ);env.update(DISPLAY_ENV)
if MODE=='prepare':
 journal,unit=c.proof(policy)
 print(json.dumps(dict(status='REVIEWED_CONTROL_READY_NO_UI_CHANGED',unit_pid=unit['MainPID'],pins=286,guard=journal['guard'])))
 raise SystemExit(0)
if MODE in ('inspect-close','close'):
 owner=c.load(CONTROL+'/candidate_owner.json')['owner'];c.need(c.same_owner(c.process(owner['pid']),owner),'candidate_owner_changed')
 c.proof(policy)
 plan=ORIGINAL_PLAN;plan['owner']={k:v for k,v in owner.items() if k!='parent_pid'}
 manifest=c.load(c.TARGET+'/assembly_manifest.json')
 for relative in ('tools/board_avatar_pan.py','tools/board_avatar_gtk.py','tools/yuki_business_candidate.py','tools/libaura_yuki.so'):
  key='runtime/aura/'+relative;plan['sources'][c.TARGET+'/'+key]=manifest['candidate_files'][key]['sha256']
 raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode();plan_sha=hashlib.sha256(raw).hexdigest()
 path=CONTROL+'/candidate_close_plan.json';put(path,raw)
 c.need(hashlib.sha256(Path(X11).read_bytes()).hexdigest()==X11SHA,'x11_source_changed')
 argv=['/usr/bin/python3','-B',X11,'--plan',path,'--plan-sha256',plan_sha]
 if MODE=='close':
  previous=c.load(CONTROL+'/candidate_close_inspect.json')
  c.need(previous['close_guard_ready'] is True,'candidate_close_guard_not_ready')
  argv+=['--request-close','--review-token',previous['review_token'],'--window-id',str(previous['window']['window_id'])]
 done=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=35)
 value=json.loads(done.stdout)
 if done.returncode==0:
  put(CONTROL+('/candidate_close_inspect.json' if MODE=='inspect-close' else '/candidate_normal_close.json'),done.stdout.encode())
 print(json.dumps(dict(returncode=done.returncode,result=value)))
 raise SystemExit(0)
if MODE.startswith('launch'):
 raw=base64.b64decode(RECEIPT,validate=True);receipt=CONTROL+'/original_normal_close.json';put(receipt,raw)
 argv=['/usr/bin/python3','-B',str(r/'launch_v2.py'),'--policy',str(r/'ui_trial_policy.v2.json'),
       '--policy-sha256',PINS['ui_trial_policy.v2.json'],'--original-close-receipt',receipt,'--receipt-sha256',hashlib.sha256(raw).hexdigest()]
 if MODE=='launch':argv+=['--launch']
elif MODE.startswith('restore'):
 argv=['/usr/bin/python3','-B',str(r/'restore_v2.py'),'--policy',str(r/'ui_trial_policy.v2.json'),
       '--policy-sha256',PINS['ui_trial_policy.v2.json']]
 if MODE=='restore':argv+=['--restore']
 if NATURAL:argv+=['--candidate-exited-naturally']
 elif Path(CONTROL+'/candidate_owner.json').exists():
  receipt=CONTROL+'/candidate_normal_close.json'
  argv+=['--candidate-close-receipt',receipt,'--receipt-sha256',hashlib.sha256(Path(receipt).read_bytes()).hexdigest()]
else:raise ValueError('mode')
done=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=110)
try:value=json.loads(done.stdout)
except ValueError:value=dict(status='INVALID_RESULT',stderr=done.stderr[-1000:])
print(json.dumps(dict(returncode=done.returncode,result=value)))
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','launch-inspect','launch','inspect-close','close','restore-inspect','restore'))
    parser.add_argument('--natural-exit',action='store_true');args=parser.parse_args()
    folder=HERE/'resume_ui_trial'
    files={}
    for name,expected in PINS.items():
        raw=(folder/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
        files[name]=(base64.b64encode(raw).decode(),expected)
    baseline=json.loads((folder/'actual_ui_baseline.json').read_text(encoding='utf-8'))
    original=json.loads((folder/'original_gui.plan.json').read_text(encoding='utf-8'))
    receipt=''
    if args.mode.startswith('launch'):
        value=json.loads((folder/'actual_x11_close.json').read_text(encoding='utf-8'))['result']
        assert value.get('owner_exited') is True and value.get('forced_action') is False
        receipt=base64.b64encode(json.dumps(value,sort_keys=True).encode()).decode()
    values=dict(ROOT=ROOT,CONTROL=CONTROL,PINS=PINS,FILES=files,MODE=args.mode,NATURAL=args.natural_exit,
        DISPLAY_ENV=baseline['display_environment'],ORIGINAL_PLAN=original,RECEIPT=receipt,X11=X11,X11SHA=X11SHA)
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    result=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=120))
    path=folder/('actual_control_'+args.mode+('_natural' if args.natural_exit else '')+'.json')
    write_json(path,result);print(json.dumps(dict(output=str(path),**result),ensure_ascii=True))

if __name__=='__main__':main()
