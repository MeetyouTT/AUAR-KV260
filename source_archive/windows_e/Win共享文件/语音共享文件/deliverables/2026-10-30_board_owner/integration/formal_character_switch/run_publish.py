"""Single-root transport for one explicit formal character publication step."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

CODE='c97bdb5e87268e2fb846b171b9b0bb97cac98baa2664e733173912e73071956b'
POLICY='b550e2a2307d97b52ba598a9e992f96ecacb53de05babf438d551a942de2996d'
ROOT='/home/root/aura-character-xuefei-20261030/tools-'+CODE[:16]
ARCHIVE='/home/root/aura-character-xuefei-20261030/incoming-f94fca2c94288acb/formal_yuki.overlay.zip'
SCRIPT=r'''
import base64,hashlib,json,os,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
r=Path(ROOT);assert not r.is_symlink() and r.parent==Path('/home/root/aura-character-xuefei-20261030')
r.mkdir(mode=0o700,exist_ok=True);assert r.resolve()==r and r.stat().st_mode&0o077==0
for name,(payload,pin) in FILES.items():
 raw=base64.b64decode(payload,validate=True);assert hashlib.sha256(raw).hexdigest()==pin
 p=r/name;assert not p.is_symlink()
 if p.exists():assert p.read_bytes()==raw
 else:
  fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
env=dict(os.environ);env.update(DISPLAY_ENV);env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
done=subprocess.run(['/usr/bin/python3','-B',str(r/'formal_publish.py')]+ARGV,env=env,capture_output=True,text=True,timeout=220)
try:value=json.loads(done.stdout)
except ValueError:value=dict(status='INVALID_HELPER_RESULT',stderr=done.stderr[-1000:])
print(json.dumps(dict(returncode=done.returncode,result=value)))
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('inspect','stage','startup-check','guard','window-inspect','normal-close','publish','ready','rollback-prepare','rollback-start','rollback-ready'));parser.add_argument('--appearance-records',action='store_true');args=parser.parse_args()
    evidence=HERE.parent/'appearance_patch' if args.appearance_records else HERE
    files={}
    for name,pin in (('formal_publish.py',CODE),('policy.json',POLICY)):
        raw=(HERE/'publish'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
        files[name]=(base64.b64encode(raw).decode(),pin)
    argv=[args.action,'--policy',ROOT+'/policy.json','--policy-sha256',POLICY]
    if args.action in ('inspect','stage'):argv+=['--overlay',ARCHIVE]
    if args.action=='normal-close':
        checked=json.loads((evidence/'actual_window-inspect.json').read_text(encoding='utf-8'))['result']
        assert checked['status']=='WINDOW_INSPECTED_NO_CLOSE'
        argv+=['--review-token',checked['review_token'],'--window-id',str(checked['window']['window_id'])]
    env=json.loads((HERE/'actual_baseline.json').read_text(encoding='utf-8'))['display_environment']
    values=dict(ROOT=ROOT,FILES=files,ARGV=argv,DISPLAY_ENV=env)
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    value=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=235))
    out=evidence/('actual_'+args.action+'.json');out.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    display={k:v for k,v in value['result'].items() if k not in ('output','files')}
    if 'files' in value['result']:display['files']=value['result']['files'] if isinstance(value['result']['files'],int) else len(value['result']['files'])
    print(json.dumps(dict(output=str(out),returncode=value['returncode'],result=display),ensure_ascii=True))

if __name__=='__main__':main()
