from common import *
from collections import defaultdict
MAP=load(B/'visual_artifact_fix_20261102/release/fresh_expected_after.json')
want=MAP['component_sha256'].copy()
startup='_startup/config.json'
want[startup]=MAP['startup_sha256']
assert len(want)==381
sw=ROOT/'src/software'
lookup=defaultdict(set)
for n,h in want.items():lookup[h].add(n)
found={}
def collect(p,h=None):
    if h and h not in lookup:return
    if not p.is_file():return
    h=sha(p)
    if h not in lookup:return
    for name in list(lookup.pop(h)):
        dest=ROOT/'board/config/startup.snapshot.json' if name==startup else sw/name
        copy(p,dest)
        found[name]=str(p)
c=B/'other_components_20261102/live_enrollment_20261102/voice_conversation_address_20261102/candidate_runtime'
for n,h in want.items():
    for k in [c,P/'aura']:
        collect(k/n,h)
for f in (B/'cpu_optimization_20261102').rglob('*'):
    names={n.rsplit('/',1)[-1] for h in lookup.values() for n in h}
    if f.name.split('__')[-1] in names:collect(f)
inv=Path(r'E:\Ubuntu到E盘_单向补齐_20261102')
with (inv/'windows_common_sha256.jsonl').open(encoding='utf8') as fp:
    for l in fp:
        rec=json.loads(l)
        if rec.get('sha256') in lookup:collect(SH/rec['p'],rec['sha256'])
names={n.rsplit('/',1)[-1] for h in lookup.values() for n in h}
for d,dirs,files in os.walk(B):
    dirs[:]=[s for s in dirs if not s.startswith(('test_work','engineering_delivery')) and s not in ('__pycache__','.git')]
    for s in files:
        if s.split('__')[-1] in names or (startup not in found and 'startup' in s and s.endswith('.json')):collect(Path(d)/s)
for n in list(want):
    if n not in found and n!=startup and (sw/n).is_file() and sha(sw/n)==want[n]:found[n]='prior verified collection'
save(W/'source_locations.local.json',found)
save(ROOT/'data/reference/runtime_hashes.json',{'component_sha256':MAP['component_sha256'],'startup_sha256':want[startup]})
print(len(found), 'found. Missing:', [n for n in want if n not in found])
