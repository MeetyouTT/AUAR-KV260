from common import *
import ast,base64,re,shlex
meta=load(ROOT/'board/config/public_board_resources.json')
units=meta['systemd_order']
eff={}
for name,overrides in units.items():
    config={k:[] for k in ['ExecStartPre','ExecCondition','ExecStart','ExecStartPost','ExecStop','ExecStopPost']}
    for dest in ['/etc/systemd/system/'+name]+overrides:
        for line in (ROOT/meta['files'][dest]['source']).read_text(encoding='utf8').splitlines():
            k,_,v=line.strip().partition('=')
            if k in config:
                if v:config[k].append(v)
                else:config[k].clear()
    eff[name]=config
save(W/'public_unit_effective.json',eff)
wanted={}; active=eff['aura-camera-ui.service']['ExecStartPre']
for raw in active:
    av=shlex.split(raw)
    if '-c' not in av:print('pre directly executed',av[:2]);continue
    code=av[av.index('-c')+1]
    strings=tuple(x.value for x in ast.walk(ast.parse(code)) if isinstance(x,ast.Constant) and isinstance(x.value,str))
    paths=[s for s in strings if s.startswith('/home/root/') and s.endswith('deployment-manifest.json')]
    digests=[s for s in strings if re.fullmatch(r'[0-9a-f]{64}',s)]
    if len(paths)==len(digests)==1:wanted[paths[0]]=digests[0]
    else:print('other pre arg (paths only)',[s for s in strings if s.startswith('/')][:3])
print('effective prestart',len(active),'release manifests',len(wanted))
def read_board(spec):
    remote="""import os,stat,sys,json,base64,hashlib
from pathlib import Path
out={}
for n,h in SPEC.items():
    p=Path(n)
    if p.resolve(strict=True)!=p:raise ValueError(p.name+' symlink')
    with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOATIME|os.O_NOFOLLOW|os.O_NONBLOCK),'rb')as f:
        st=os.fstat(f.fileno());assert stat.S_ISREG(st.st_mode) and st.st_size<=2000000
        b=f.read(2000001);assert len(b)==st.st_size
    assert hashlib.sha256(b).hexdigest()==h,n
    out[n]=base64.b64encode(b).decode()
print(json.dumps(out))
""".replace('SPEC',repr(spec))
    cmd=['ssh','-b','192.168.50.1','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=8','aura-kv260','python3 -I -B -']
    p=subprocess.run(cmd,input=remote.encode(),capture_output=True,timeout=60)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[:500])
    blobs=json.loads(p.stdout);assert set(blobs)==set(spec)
    result={}
    for n,s in blobs.items():
        b=base64.b64decode(s,validate=True);h=spec[n]
        assert hashlib.sha256(b).hexdigest()==h
        (W/'public_kv260_copy'/h).write_bytes(b);result[n]=b
    return result
pins={}
for n,b in read_board(wanted).items():
    j=json.loads(b);rows=j['pins']
    for path,h in rows.items():
        if path in pins and pins[path]!=h:raise RuntimeError('inconsistent preflight '+path)
        pins[path]=h
    print('preflight',n.split('/')[-2],len(rows), list(j.keys())[:8])
save(W/'public_camera_preflight.json',{'manifests':wanted,'pins':pins})
if sys.argv[1:]!=['inspect']:raise ValueError('inspect first')
print('unique pins',len(pins))
for n in pins:print(n)
