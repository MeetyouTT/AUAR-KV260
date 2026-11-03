from common import *
src=ROOT/'board/config/original_camera_inputs.json'
d=load(src);dest_rows=load(ROOT/'board/config/deployment_files.json')
startup=load(ROOT/'board/config/startup.snapshot.json')
look=dict(d['unresolved_from_offline_archives'])
look[startup['touch_module']]=startup['touch_module_sha256']
nativ='/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/libaura_native_operator.so'
look[nativ]='704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224'
spec=json.dumps(look)
script=r"""
import os,sys,hashlib,tarfile,io,json
from pathlib import Path
home=Path.home(); want=json.loads(SPEC)
names={n.rsplit('/',1)[-1] for n in want}; hs=set(want.values()); found={}
for base in sorted(home.glob('aura-*')):
    if not base.is_dir(): continue
    for root,dirs,files in os.walk(str(base)):
        dirs[:]=[k for k in dirs if k not in ('private-data','.git','__pycache__','build','site-packages','.cache','venv','host-env','node_modules','private')]
        for n in files:
            if n not in names and ('native' not in n or not n.endswith('.so')):continue
            p=Path(root)/n
            try:
                if p.stat().st_size>5000000:continue
                b=p.read_bytes();h=hashlib.sha256(b).hexdigest()
                if h in hs:found[h]=b
            except OSError:pass
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as tar:
    for n,h in want.items():
        if h in found:
            b=found[h];i=tarfile.TarInfo('board/linked/'+h[:12]+'/'+Path(n).name);i.size=len(b);tar.addfile(i,io.BytesIO(b))
""".replace('SPEC',repr(spec))
remote_collect(script,ROOT)
new=0
for n,h in look.items():
    s='board/linked/'+h[:12]+'/'+n.rsplit('/',1)[-1];f=ROOT/s
    if f.is_file() and sha(f)==h:
        if not any(row['destination']==n for row in dest_rows):dest_rows.append(dict(source=s,destination=n))
        d['unresolved_from_offline_archives'].pop(n,None);new+=1
save(src,d);save(ROOT/'board/config/deployment_files.json',dest_rows)
print('Found',new,'other exact inputs. Remaining prior camera pins:',len(d['unresolved_from_offline_archives']))
