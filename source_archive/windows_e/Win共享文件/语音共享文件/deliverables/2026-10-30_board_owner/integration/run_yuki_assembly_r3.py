"""Root-owned transport for the frozen revision2 synthetic runtime assembly."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import KEY,ssh
from resume_baseline import write_json

SHA='15da79abf924632e492092a098144787acebcd3d1d31223e1001231224b33456'
POLICY='ffa2f3b1c063c3af51006c622d81684fdeb37cf19d8c7b0ac063325d0581f9ea'
ARCHIVE='2c25b6a91a635a9bb70eef00cdc180829c503cdba3382135f8366c72e3242334'
ROOT='/home/root/aura-board-owner-candidate-20261030/yuki-assembly-'+ARCHIVE[:12]+'-'+SHA[:12]
TARGET='/home/root/aura-board-owner-candidate-20261030/yuki-gui-capacity-20261030-r3'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',action='store_true');args=parser.parse_args()
    folder=HERE/'resume_yuki_run_assembly';source=HERE/'resume_yuki_business_candidate_v2/yuki_business.source_candidate.zip'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==ARCHIVE
    files={'assemble.py':(folder/'assemble_v2.py',SHA),'policy.json':(folder/'assembly_policy.v2.final.json',POLICY)}
    for p,h in files.values():assert hashlib.sha256(p.read_bytes()).hexdigest()==h
    gate=json.loads((HERE.parent/'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    assert gate['performance_window']['state']=='BUSINESS_ACCEPTANCE_EXCLUSIVE'
    prepare='''import base64,hashlib,os\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\nr=Path(ROOT);assert r.parent==Path('/home/root/aura-board-owner-candidate-20261030') and not r.is_symlink()\nr.mkdir(mode=0o700,exist_ok=True);assert r.stat().st_mode&0o077==0\nfor name,payload in FILES.items():\n b=base64.b64decode(payload[0],validate=True);assert hashlib.sha256(b).hexdigest()==payload[1]\n p=r/name;assert not p.is_symlink()\n if p.exists():assert p.read_bytes()==b\n else:\n  fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n  with os.fdopen(fd,'wb') as out:out.write(b);out.flush();os.fsync(out.fileno())\n'''
    values=dict(BOOT=gate['performance_window']['board_boot'],ROOT=ROOT,
        FILES={n:(base64.b64encode(p.read_bytes()).decode(),h) for n,(p,h) in files.items()})
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    ssh('python3 -B -',prefix+prepare)
    exists=ssh('python3 -B -',"from pathlib import Path\nprint(Path("+repr(ROOT+'/source.zip')+").exists())\n").strip()=='True'
    if not exists:
        result=subprocess.run(['C:/Windows/System32/OpenSSH/scp.exe','-O','-q','-i',str(KEY),
            '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',source.name,
            'root@192.168.50.2:'+ROOT+'/source.zip'],cwd=str(source.parent),capture_output=True,text=True,timeout=35)
        if result.returncode:raise RuntimeError(result.stderr[-1500:])
    settings=folder/'actual_request_r3.json'
    if settings.exists():request=json.loads(settings.read_text(encoding='utf-8'))
    else:
        now=datetime.datetime.now(datetime.timezone.utc).timestamp()
        request=dict(utc_start=now-86400,utc_end=now+86400,target=TARGET)
        write_json(settings,request)
    assert request['target']==TARGET
    argv=['/usr/bin/python3','-B',ROOT+'/assemble.py']+(['stage'] if args.stage else [])
    argv+=['--policy',ROOT+'/policy.json','--policy-sha256',POLICY,'--archive',ROOT+'/source.zip',
        '--target',TARGET,'--utc-start',str(request['utc_start']),'--utc-end',str(request['utc_end'])]
    if args.stage:
        checked=json.loads((folder/'actual_inspect_r3.json').read_text(encoding='utf-8'))['result']
        argv+=['--expected-inspection-sha256',checked['inspection_sha256']]
    wrapper='''import hashlib,json,subprocess\nfrom pathlib import Path\np=Path(ROOT)/'source.zip';assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==ARCHIVE\np.chmod(0o600)\nr=subprocess.run(ARGV,capture_output=True,text=True,timeout=90)\nprint(json.dumps(dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)))'''
    prefix='\n'.join(k+'='+repr(v) for k,v in dict(ROOT=ROOT,ARCHIVE=ARCHIVE,ARGV=argv).items())+'\n'
    result=json.loads(ssh('python3 -B -',prefix+wrapper,timeout=100))
    try:result['result']=json.loads(result['stdout'])
    except ValueError:result['result']=dict(status='INVALID_OR_MISSING_RESULT')
    output=folder/('actual_staged_r3.json' if args.stage else 'actual_inspect_r3.json')
    write_json(output,dict(argv=argv,**result))
    value=result['result']
    print(json.dumps(dict(output=str(output),returncode=result['returncode'],result={k:v for k,v in value.items()
        if k not in ('source_snapshot','snapshot','file_hashes','files','resources','dependency_snapshots')}),ensure_ascii=True))


if __name__=='__main__':main()
