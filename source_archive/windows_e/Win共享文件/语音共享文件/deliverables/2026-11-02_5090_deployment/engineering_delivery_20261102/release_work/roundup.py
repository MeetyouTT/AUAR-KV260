from common import *
import re
d=load(ROOT/'board/config/original_camera_inputs.json')
wanted=dict(d['unresolved_from_offline_archives'])
report=load(ROOT/'data/reference/public_feedback.json')
for r in report['assets']:wanted[r['path']]=r['sha256']
wanted[report['manifest']]=report['manifest_sha256']
script=r"""
import sys,json,hashlib,base64,gzip,ast,os,io,tarfile,zipfile
from pathlib import Path
H=Path.home();desired=json.loads(SPEC);hs=set(desired.values());names={Path(k).name for k in desired};blobs={}
def maybe(b):
    h=hashlib.sha256(b).hexdigest()
    if h in hs:blobs[h]=b
def literals(p):
    result={}
    for node in ast.parse(p.read_bytes()).body:
        if not isinstance(node,ast.Assign) or not isinstance(node.targets[0],ast.Name):continue
        try:result[node.targets[0].id]=ast.literal_eval(node.value)
        except (ValueError,TypeError,SyntaxError):pass
    return result
live=H/'aura-native-live-20261024'
bl=literals(live/'board_prepare.py')['PAYLOAD']
meta=json.loads(gzip.decompress(base64.b64decode(bl)))
for n,b in meta['files'].items():maybe(base64.b64decode(b))
for v in ['r3','r4']:
    fs=json.loads((live/v/'files.json').read_text())
    maybe((json.dumps({'schema':'aura-native-python-source-2','files':{n:p for n,p in fs.items() if n.endswith('.py')}},indent=2,sort_keys=True)+'\n').encode())
    items=literals(live/v/'board_prepare_fix.py')
    for k in ('PAYLOAD','CHANGES'):
        if isinstance(items.get(k),dict):
            for n,b in items[k].items():
                if isinstance(b,str):maybe(base64.b64decode(b))
a=H/'aura-dpu-vision-20261021/work'
archives=[p for p in a.glob('*.tar.gz') if 'private' not in p.name and p.stat().st_size<16000000]
dirs=[H/'aura-native-live-20261024',H/'aura-vision-reliability-20261023',H/'aura-board-tracking-20261011',H/'aura-board-yolo-20261011',H/'aura-native-critical-20261024',H/'aura-board-ui-autostart-20261009',H/'aura-dpu-vision-20261021/live-source']
for root in dirs:
    archives += [p for p in root.rglob('*.zip') if 'private' not in p.name and p.stat().st_size<16000000]
def eligible(n,size):
    return Path(n).name in names and size<5000000
for p in archives:
    try:
        if p.suffix=='.zip':
            with zipfile.ZipFile(p) as z:
                for f in z.infolist():
                    if eligible(f.filename,f.file_size):maybe(z.read(f))
        else:
            with tarfile.open(p,'r:gz') as t:
                for f in t:
                    if f.isfile() and eligible(f.name,f.size):maybe(t.extractfile(f).read())
    except (tarfile.TarError,zipfile.BadZipFile,OSError):continue
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as tar:
    emitted=set()
    for n,h in desired.items():
        path='board/linked/'+h[:12]+'/'+Path(n).name
        if h not in blobs or path in emitted:continue
        emitted.add(path);b=blobs[h];f=tarfile.TarInfo(path);f.size=len(b);tar.addfile(f,io.BytesIO(b))
""".replace('SPEC',repr(json.dumps(wanted)))
remote_collect(script,ROOT)
srcs=load(ROOT/'board/config/deployment_files.json')
for n,h in wanted.items():
    p='board/linked/'+h[:12]+'/'+n.rsplit('/',1)[-1]
    if not (ROOT/p).is_file():continue
    assert sha(ROOT/p)==h
    if not any(k['destination']==n for k in srcs):srcs.append(dict(source=p,destination=n))
    d['unresolved_from_offline_archives'].pop(n,None);print(n)
save(ROOT/'board/config/deployment_files.json',srcs)
save(ROOT/'board/config/original_camera_inputs.json',d)
print('remaining',len(d['unresolved_from_offline_archives']))
