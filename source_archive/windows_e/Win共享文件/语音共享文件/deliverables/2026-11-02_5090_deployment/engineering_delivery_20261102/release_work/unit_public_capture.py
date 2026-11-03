from common import *
import base64,datetime,re
assert sys.argv[1] in ('inspect','capture')
src=r"""import os,hashlib,pathlib,stat,subprocess,re,shlex,base64,json
units=['aura-avatar-ui.service','aura-camera-ui.service']
rows=[]
for unit in units:
    raw=subprocess.check_output(['systemctl','show','--no-pager','--property=DropInPaths','--value',unit],text=True)
    for name in raw.strip().split():
        path=pathlib.Path(name); root=pathlib.Path('/etc/systemd/system')/(unit+'.d')
        if path.parent!=root or not re.fullmatch('[a-z0-9][a-z0-9_.-]*[.]conf',path.name) or path.resolve(strict=True)!=path:raise ValueError('unapproved config path')
        with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOATIME|os.O_NOFOLLOW|os.O_NONBLOCK),'rb')as f:
            m=os.fstat(f.fileno()); assert stat.S_ISREG(m.st_mode) and m.st_size<24576
            b=f.read(24577);assert len(b)==m.st_size
        s=b.decode('utf8')
        row=dict(unit=unit,destination=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),directives=[],env=[],commands=[])
        ok=True
        for line in s.splitlines():
            line=line.strip()
            if not line or line.startswith(('#',';')):continue
            if line in ('[Service]','[Unit]'):continue
            if '=' not in line:ok=False;row['directives'].append('unclassified');continue
            key,val=line.split('=',1);row['directives'].append(key)
            if key in ('ExecCondition','ExecStart','ExecStartPre','ExecStopPost','ExecStop','ExecStartPost'):
                if val:
                    args=shlex.split(val);row['commands'].append(args[0])
                    if not re.fullmatch(r'[-/]?[a-zA-Z0-9/._-]+',args[0]):ok=False
            elif key=='Environment':
                for item in shlex.split(val):
                    k,_,v=item.partition('=');row['env'].append(k)
                    if k not in ('MKL_NUM_THREADS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','PYTHONDONTWRITEBYTECODE','PYTHONNOUSERSITE','PYTHONPATH'):ok=False
                    if re.search(r'(?i)pass(word|wd)?|secret|token|cookie|credential|private|auth|key$',k):ok=False
            elif key not in ('RequiresMountsFor','SendSIGKILL','WorkingDirectory','Restart','RestartSec','TimeoutStopSec','TimeoutStartSec','StartLimitIntervalSec','StartLimitBurst','Nice','CPUWeight','OOMScoreAdjust','KillMode','Conflicts','After','Wants','Requires'):
                ok=False
        if re.search(r'(?i)-----BEGIN .*PRIVATE KEY|hf_[a-z0-9]{27,}|sk-[a-z0-9_-]{26,}|[a-z][a-z0-9]+://[^/ \n]+:[^/ \n]+@|(?:password|passwd|api[_-]?key|bearer|cookie|access[_-]?token|secret)\s*(?:=|:|\s)\s*[^ ;]+',s):ok=False
        row['eligible']=ok
        if MODE=='capture' and ok:row['data']=base64.b64encode(b).decode()
        rows.append(row)
print(json.dumps(rows))
""".replace('MODE',repr(sys.argv[1]))
cmd=['ssh','-b','192.168.50.1','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','RequestTTY=no','aura-kv260','python3 -I -B -']
proc=subprocess.run(cmd,input=src.encode(),capture_output=True,check=True,timeout=45)
rows=json.loads(proc.stdout)
print('fragments',len(rows),'directives',sorted(set(v for r in rows for v in r['directives'])))
print('env keys',sorted(set(v for r in rows for v in r['env'])))
print('command list',sorted(set(v for r in rows for v in r['commands'])))
print('excluded',[(r['unit'],Path(r['destination']).name,r['directives']) for r in rows if not r['eligible']])
if sys.argv[1]=='capture':
    baseline=load(W/'public_unit_metadata.json')
    assert [(x['destination'],x['sha256']) for x in baseline]==[(x['destination'],x['sha256']) for x in rows]
    for r in rows:
        txt=r.pop('data',None)
        if txt is not None:
            buf=base64.b64decode(txt,validate=True)
            assert hashlib.sha256(buf).hexdigest()==r['sha256']
            (W/'public_kv260_copy'/r['sha256']).write_bytes(buf)
    save(W/'public_unit_copy.json',rows)
else:save(W/'public_unit_metadata.json',rows)
