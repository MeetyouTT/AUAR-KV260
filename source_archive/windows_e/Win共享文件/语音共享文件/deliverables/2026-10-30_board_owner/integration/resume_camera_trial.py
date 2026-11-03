"""One explicit root-owned camera trial action, always journaled separately."""
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

BOOT='8100a7fd-0c6a-46c4-82b8-f874988a1521'
MANIFEST='b697628ac2588881628e809e207a8bbc5e88f9d0ab40a433749e1d875aa38ccd'
EXECUTOR='08348d996517ea78a438332b965839e886d6da5531ea5d13941eb46ccec711d2'
READBACK='/home/root/aura-board-owner-candidate-20261030/private-pin-8100a7fd-20261030/face_gallery_readback.local.json'
READBACK_SHA='8daeef57e5871abeb21a73d7daca5b0e1a02ae0824ccc481c62e7977fa365167'
ROOT='/home/root/aura-board-owner-candidate-20261030/camera-budget-'+MANIFEST[:16]+'-'+EXECUTOR[:12]


def gate():
    state=json.loads((HERE.parent/'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    if state['performance_window'].get('state')!='BUSINESS_ACCEPTANCE_EXCLUSIVE':
        raise RuntimeError('Root does not own the hardware window')


def stage():
    gate()
    local=HERE/'resume_camera_budget'
    sources={'candidate/'+n:local/'candidate'/n for n in ('entry.py','face_budget.py','candidate-manifest.json')}
    sources['serial_trial.py']=local/'serial_trial.py'
    pins={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in sources.items()}
    if pins['serial_trial.py']!=EXECUTOR or pins['candidate/candidate-manifest.json']!=MANIFEST:
        raise ValueError('Trial source has changed since review')
    for n,p in sources.items():
        if n.endswith('.py'):compile(p.read_text(encoding='utf-8'),str(p),'exec')
    script='''import base64,hashlib,json,os,subprocess\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\nr=Path(ROOT);assert r.parent==Path('/home/root/aura-board-owner-candidate-20261030')\nassert r.parent.is_dir() and not r.parent.is_symlink() and not r.is_symlink()\nr.mkdir(mode=0o700,exist_ok=True)\nassert r.stat().st_mode&0o077==0\nfor name,encoded in SOURCES.items():\n p=r/name;assert not p.is_symlink() and r in p.resolve().parents\n p.parent.mkdir(mode=0o700,exist_ok=True)\n b=base64.b64decode(encoded,validate=True);assert hashlib.sha256(b).hexdigest()==PINS[name]\n if p.exists():assert p.read_bytes()==b\n else:\n  fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n  with os.fdopen(fd,'wb') as out:out.write(b);out.flush();os.fsync(out.fileno())\nj=r/'journal';assert not j.is_symlink();j.mkdir(mode=0o700,exist_ok=True)\nassert j.stat().st_mode&0o077==0\np=Path(READBACK);assert hashlib.sha256(p.read_bytes()).hexdigest()==READBACK_SHA\nv=json.loads(p.read_bytes())\npid=int(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True))\nassert pid==v['camera_pid'] and v['board_boot_id']==BOOT\nbirth=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]\nassert str(v['camera_start_ticks'])==birth\ncheck=subprocess.run(['/usr/bin/python3','-B',str(r/'candidate/entry.py'),'--manifest-sha256',MANIFEST,'--verify-only'],capture_output=True,text=True,timeout=25)\nassert check.returncode==0,check.stderr\nprint(json.dumps(dict(status='STAGED_STATICALLY_VERIFIED_NO_OWNER_STARTED',root=str(r),candidate_dir=str(r/'candidate'),journal=str(j/'state.json'),pins=PINS,pid=pid,birth=birth,boot=BOOT,verification=json.loads(check.stdout))))'''
    prefix='\n'.join(k+'='+repr(v) for k,v in dict(BOOT=BOOT,ROOT=ROOT,MANIFEST=MANIFEST,READBACK=READBACK,
        READBACK_SHA=READBACK_SHA,PINS=pins,SOURCES={n:base64.b64encode(p.read_bytes()).decode() for n,p in sources.items()}).items())+'\n'
    value=json.loads(ssh('python3 -B -',prefix+script,timeout=40))
    write_json(HERE/'resume_camera_budget/actual_staged.json',value)
    print(json.dumps(value,ensure_ascii=True))


def action(name):
    gate()
    staged=json.loads((HERE/'resume_camera_budget/actual_staged.json').read_text(encoding='utf-8'))
    if staged['root']!=ROOT or staged['boot']!=BOOT:raise ValueError('Trial root or boot differs')
    executor=staged.get('active_executor','serial_trial.py')
    if executor not in staged['pins'] or '/' in executor:raise ValueError('Unpinned trial executor')
    argv=['/usr/bin/python3','-B',ROOT+'/'+executor,name,'--journal',staged['journal'],'--wait-seconds','20']
    if name=='prepare':
        argv+=['--candidate-dir',staged['candidate_dir'],'--manifest-sha256',MANIFEST,
            '--readback',READBACK,'--readback-sha256',READBACK_SHA,'--expected-boot',BOOT,
            '--expected-pid',str(staged['pid']),'--expected-birth',staged['birth']]
    script='''import hashlib,json,subprocess\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\nfor name,expected in PINS.items():assert hashlib.sha256((Path(ROOT)/name).read_bytes()).hexdigest()==expected\nr=subprocess.run(ARGV,capture_output=True,text=True,timeout=90)\nprint(json.dumps(dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)))'''
    prefix='\n'.join(k+'='+repr(v) for k,v in dict(BOOT=BOOT,ROOT=ROOT,PINS=staged['pins'],ARGV=argv).items())+'\n'
    now=datetime.datetime.now(datetime.timezone.utc)
    record=dict(action=name,began_utc=now.isoformat(),root=ROOT,argv=argv)
    try:
        result=json.loads(ssh('python3 -B -',prefix+script,timeout=100));record.update(result)
        record['result']=json.loads(result['stdout'])
    except Exception as error:record.update(error_type=type(error).__name__,error=str(error)[-3000:])
    output=HERE/'resume_camera_budget'/(now.strftime('%Y%m%dT%H%M%S')+'-'+name+'.json')
    write_json(output,record)
    print(json.dumps(dict(output=str(output),**record),ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('stage','prepare','stop-baseline',
        'start-candidate','stop-candidate','restore','finalize','status','stop-restored'))
    args=parser.parse_args()
    if args.action=='stage':stage()
    else:action(args.action)
