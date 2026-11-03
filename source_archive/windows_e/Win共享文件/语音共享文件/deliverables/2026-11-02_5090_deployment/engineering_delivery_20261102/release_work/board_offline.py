from common import *
import re
deploy=load(ROOT/'board/config/deployment_files.json')
srcmap={r['destination']:r['source'] for r in deploy}
def reg(p,dest):
    k=p.relative_to(ROOT).as_posix()
    if dest in srcmap and srcmap[dest]!=k and sha(p)!=sha(ROOT/srcmap[dest]):raise ValueError((dest,k))
    srcmap[dest]=k
R=ROOT/'src/camera'
oldmeta=load(B/'cpu_optimization_20261102/camera/SOURCE_DISCOVERY.json')['board_result']['meta']
saved=load(ROOT/'src/software/config/face_gallery_readback.local.json')['source_sha256']
assert sha(ROOT/'src/software/tests/fixtures/vision/person_bus.jpg')=='975917d943c3dd367a27c37c4a9b0cdaf28c73ce671c881f6489a18bda20b46f'
# Resolve fixed input hashes against saved sources, and avoid provisioning per-boot state.
index={}
for p in ROOT.rglob('*'):
    if p.is_file() and p.stat().st_size<3000000:index.setdefault(sha(p),p)
inv=Path(r'E:\Ubuntu到E盘_单向补齐_20261102\windows_common_sha256.jsonl')
ext='/home/root/aura-native-live-20261024/ops/be72669aa53de735/'
want={**{ext+name:h for name,h in oldmeta['source_pins'].items()},**{p:h for p,h in saved.items() if '/native-run-' not in p}}
want.update(oldmeta['protected'])
hashset=set(want.values())
with inv.open(encoding='utf8')as f:
    for l in f:
        a=json.loads(l);h=a.get('sha256')
        if h in hashset and h not in index:
            p=SH/a['p']
            if p.is_file() and sha(p)==h:index[h]=p
variants=[
   lambda d: (json.dumps(d,sort_keys=True,indent=2)+'\n').encode(),
   lambda d: (json.dumps(d,indent=2)+'\n').encode(),
   lambda d: (json.dumps(d,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode(),
]
for d in [oldmeta,load(B/'cpu_optimization_20261102/camera/SOURCE_DISCOVERY.json')['board_result']['config']]:
    for make in variants:
        blob=make(d);h=hashlib.sha256(blob).hexdigest()
        if h in hashset:
            fn=ROOT/'board/linked'/h[:12]/('meta.json' if 'protected' in d else 'config.json')
            fn.parent.mkdir(parents=True,exist_ok=True);fn.write_bytes(blob);index[h]=fn
missing={}
for n,h in want.items():
    if h not in index:missing[n]=h;continue
    f=index[h]
    if not f.resolve().is_relative_to(ROOT.resolve()):
        dest=ROOT/'board/linked'/h[:12]/n.rsplit('/',1)[-1];copy(f,dest);f=dest
    reg(f,n)
ip='/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217/board_identity.sface_int8.json'
j=load(ROOT/srcmap[ip])
def recurse(v):
    if isinstance(v,dict):
        for n in v.values():recurse(n)
    elif isinstance(v,list):
        for n in v:recurse(n)
    elif isinstance(v,str) and v.endswith('.xmodel') and v.startswith('/'):
        p=ROOT/'models/dpu'/v.rsplit('/',1)[-1]
        if p.is_file():reg(p,v)
recurse(j)
# Mirror fixed deployment-input paths only; user/session DBs and old process identities are never seeded.
save(ROOT/'board/config/deployment_files.json',[{'source':p,'destination':n} for n,p in sorted(srcmap.items())])
save(ROOT/'board/config/original_camera_inputs.json',dict(meta_sha256=saved.get(ext+'meta.json'),historical_external_pins=len(want),unresolved_from_offline_archives=missing,source='camera metadata and baseline proof; actual new boot requires fresh binding'))
print('Public path mapping',len(srcmap),'remaining historical pins',len(missing))
for k in list(missing)[:16]:print(k)
