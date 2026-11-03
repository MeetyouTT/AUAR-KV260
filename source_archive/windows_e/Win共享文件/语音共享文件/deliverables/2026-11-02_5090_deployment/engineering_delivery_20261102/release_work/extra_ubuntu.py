from common import *
remote_collect(r"""
from pathlib import Path
import io,sys,hashlib,tarfile,subprocess,json
H=Path.home()
entries={}
def add(src,d):entries[d]=(src.read_bytes(),str(src.relative_to(H)))
core=H/'aura-pan-follow-shadow-20261024'
for sub, dst in [('ps_trajectory_v1','trajectory_src'),('mmio_batch_v1','mmio_src'),('native_operator_v1','native_operator')]:
    files=core/sub
    for p in sorted(files.rglob('*')):
        rel=p.relative_to(files); s=str(rel)
        if not p.is_file() or '__pycache__' in rel.parts:continue
        if rel.parts[0]=='ruckig' and not s.startswith(('ruckig/include/','ruckig/src/ruckig/')) and p.name!='LICENSE':continue
        if p.suffix in ['.cpp','.hpp','.h','.c','.py','.o'] or p.name in ['LICENSE','LICENSE.Ruckig','board-build-report.json','runtime-manifest.json','source-manifest.json','SOURCE_SHA256.json','README.md']:
            add(p, ('src/camera/' if sub=='native_operator_v1' else 'src/motion/')+dst+'/'+s)
for n,s in [('yunet','yunet_public_int8'),('sface','sface_public_int8')]:
    w=H/'aura-dpu-vision-20261021/work'
    add(w/(n+'-compiled')/(s+'.xmodel'),'models/dpu/'+s+'.xmodel')
    add(w/(n+'-hardware-vectors.npz'),'data/input/'+n+'_public_vectors.npz')
    for e in ['calibration-report.json','evaluation-report.json','quant_info.json']:
        add(w/(n+'-public-int8')/e,'models/quantization/'+n+'/'+e)
add(w/'arch.json','models/quantization/arch.json')
img=H/'kv260-sd-backup-20261003/offline-inspection/root.original.ext4'
name='/usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.xmodel'
b=subprocess.check_output(['/usr/sbin/debugfs','-R','cat '+name,str(img)],stderr=subprocess.DEVNULL)
if hashlib.sha256(b).hexdigest()!='def64abdeeccbd020cb651913ba907464c1a1786e30ba7d4aa077b601388950a':raise ValueError('image YOLO model digest')
entries['models/dpu/yolox_nano_person.xmodel']=(b,'kv260-sd-backup-20261003/offline-inspection/root.original.ext4#'+name)
rows=[dict(path=d,sha256=hashlib.sha256(v[0]).hexdigest(),source=v[1],bytes=len(v[0])) for d,v in entries.items()]
entries['data/reference/additional_ubuntu_inputs.json']=(json.dumps(rows,indent=1).encode(),'')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as t:
    for d,(b,_) in entries.items():
        i=tarfile.TarInfo(d);i.size=len(b);t.addfile(i,io.BytesIO(b))
""",ROOT)
for r in load(ROOT/'data/reference/additional_ubuntu_inputs.json'):
    if sha(ROOT/r['path'])!=r['sha256']:raise ValueError(r['path'])
print('Ubuntu model, vector and native-source transfer verified.')
