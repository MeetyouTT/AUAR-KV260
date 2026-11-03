"""Stage and invoke the reviewed post-consumption pin helper only."""
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

HELPER_SHA='e42df5b355b627ac4a6df21086e8cf07a43b722ffc6b5c5bdd5b93f96b3b8124'
ROOT='/home/root/aura-board-owner-candidate-20261030/pin-helper-'+HELPER_SHA[:16]
OUTPUT='/home/root/aura-board-owner-candidate-20261030/private-pin-8100a7fd-restored260102-20261030'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    gate=json.loads((HERE.parent/'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    if gate['performance_window'].get('state')!='BUSINESS_ACCEPTANCE_EXCLUSIVE':raise RuntimeError('Root window required')
    review=json.loads((HERE/'resume_camera_pin/actual_complete_journal_review.json').read_text(encoding='utf-8'))
    assert review['phase']=='COMPLETE' and review['restored_pid']==260102 and review['dropin_removed']
    source=HERE/'resume_camera_pin/rebuild_same_boot_readback.py';raw=source.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HELPER_SHA
    from resume_camera_pin.rebuild_same_boot_readback import AUTHORITY
    argv=['/usr/bin/python3','-B',ROOT+'/rebuild_same_boot_readback.py','--executor-path',AUTHORITY['executor_path'],
        '--expected-executor-sha256',AUTHORITY['executor_sha256'],'--journal',AUTHORITY['journal_path'],
        '--expected-journal-sha256',review['sha256'],'--baseline-config',AUTHORITY['baseline_path'],
        '--expected-baseline-sha256',AUTHORITY['baseline_sha256']]
    if args.write:
        dry=json.loads((HERE/'resume_camera_pin/actual_sameboot_dryrun.json').read_text(encoding='utf-8'))['result']
        assert dry['ready'] and dry['journal_sha256']==review['sha256'] and not dry['written']
        argv+=['--write','--private-root',OUTPUT,'--output',OUTPUT+'/face_gallery_readback.local.json',
            '--proof-output',OUTPUT+'/source_proof.json','--expected-observation-sha256',dry['observation_sha256']]
    script='''import base64,hashlib,json,os,subprocess\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\nr=Path(ROOT);assert r.parent==Path('/home/root/aura-board-owner-candidate-20261030') and not r.is_symlink()\nr.mkdir(mode=0o700,exist_ok=True);assert r.stat().st_mode&0o077==0\nb=base64.b64decode(DATA,validate=True);assert hashlib.sha256(b).hexdigest()==SHA\np=r/'rebuild_same_boot_readback.py';assert not p.is_symlink()\nif p.exists():assert p.read_bytes()==b\nelse:\n fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n with os.fdopen(fd,'wb') as out:out.write(b);out.flush();os.fsync(out.fileno())\nif WRITE:\n q=Path(OUTPUT);assert q.parent==r.parent and not q.exists() and not q.is_symlink();q.mkdir(mode=0o700)\nv=subprocess.run(ARGV,capture_output=True,text=True,timeout=40)\nprint(json.dumps(dict(returncode=v.returncode,stdout=v.stdout,stderr=v.stderr)))'''
    values=dict(BOOT=review['boot'],ROOT=ROOT,DATA=base64.b64encode(raw).decode(),SHA=HELPER_SHA,WRITE=args.write,OUTPUT=OUTPUT,ARGV=argv)
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    now=datetime.datetime.now(datetime.timezone.utc)
    result=json.loads(ssh('python3 -B -',prefix+script,timeout=50))
    report=dict(checked_utc=now.isoformat(),helper_sha256=HELPER_SHA,argv=argv,**result)
    report['result']=json.loads(result['stdout'])
    name='actual_sameboot_written.json' if args.write else 'actual_sameboot_dryrun.json'
    write_json(HERE/'resume_camera_pin'/name,report)
    print(json.dumps(dict(output=str(HERE/'resume_camera_pin'/name),result=report['result']),ensure_ascii=True))
    raise SystemExit(0 if report['result'].get('ready') and result['returncode']==0 else 1)


if __name__=='__main__':main()
