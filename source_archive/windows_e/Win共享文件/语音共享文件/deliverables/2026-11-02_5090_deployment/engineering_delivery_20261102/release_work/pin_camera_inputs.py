from common import *
import ast,base64,re,shlex
prefix='/home/root/aura-native-live-20261024/ops/be72669aa53de735/'
pfr=load(W/'public_camera_preflight.json')
eff=load(W/'public_unit_effective.json')['aura-camera-ui.service']
wanted={};groups=[]
def add_pairs(ps):
    for n,h in ps.items():
        assert n.startswith(prefix) and '..' not in PurePosixPath(n).parts and re.fullmatch(r'[a-zA-Z0-9_./-]+',n),n
        leaf=PurePosixPath(n)
        assert leaf.suffix=='.py' or leaf.name in ('config.json','source-manifest.json','runtime-manifest.json','deployment-manifest.json','settings.json','libaura_native_operator.so'),n
        assert re.fullmatch('[a-f0-9]{64}',h) and (n not in wanted or wanted[n]==h),n
        wanted[n]=h
for raw in eff['ExecStartPre']:
    av=shlex.split(raw);code=av[av.index('-c')+1];tree=ast.parse(code)
    pairs={};mode='inline'
    assignments=[a for a in tree.body if isinstance(a,ast.Assign) and isinstance(a.targets[0],ast.Name) and a.targets[0].id=='checks']
    if assignments:
        for n,h in ast.literal_eval(assignments[0].value):
            if n in pairs:assert pairs[n]==h
            pairs[n]=h
    else:
        strings=[x.value for x in ast.walk(tree) if isinstance(x,ast.Constant) and isinstance(x.value,str)]
        paths=[s for s in strings if s.startswith(prefix) and (s.endswith('deployment-manifest.json') or s.endswith('runtime-manifest.json'))]
        hashes=[s for s in strings if re.fullmatch('[0-9a-f]{64}',s)]
        assert len(paths)==len(hashes)==1;src=paths[0];h=hashes[0];pairs[src]=h
        if src in pfr['manifests']:
            assert pfr['manifests'][src]==h
            rows=load(W/'public_kv260_copy'/h)['pins']
        else:
            assert src.endswith('/native-operator-v1/runtime-manifest.json')
            ref=ROOT/'src/camera/native_operator/runtime-manifest.json';assert sha(ref)==h
            rows=load(ref)['files']
        pairs.update(rows);mode='manifest'
    add_pairs(pairs);groups.append(dict(kind=mode,count=len(pairs),paths=sorted(pairs)))
# Re-use the positive-only reader without importing or running historical scripts.
helper=ast.parse((W/'active_camera_sources.py').read_text(encoding='utf-8-sig'))
fun=next(n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name=='read_board')
code=compile(ast.Module(body=[fun],type_ignores=[]),'read_board_function','exec');exec(code,globals())
read_board(wanted)
meta=load(ROOT/'board/config/public_board_resources.json');plan=load(ROOT/'board/config/deployment_files.json');indexed={r['destination']:r['source'] for r in plan}
chain={n:r['path'] for n,r in load(ROOT/'src/camera/entry_chain/source_paths.json').items()}
files=meta['files'];from_known={}
for row in (ROOT/'checksums.sha256').read_text(encoding='utf8').splitlines():
    h,n=row.split('  ',1)
    if n.startswith(('src/camera/','src/motion/','src/software/','board/linked/')):from_known.setdefault(h,n)
for r in files.values():from_known[r['sha256']]=r['source']
added=0
for n,h in wanted.items():
    blob=W/'public_kv260_copy'/h;assert sha(blob)==h
    src=indexed.get(n) or chain.get(n) or from_known.get(h)
    if src:
        assert sha(ROOT/src)==h,n
    else:
        src='src/camera/preflight/'+n[len(prefix):]
        copy(blob,ROOT/src);from_known[h]=src;added+=1
    if n not in indexed:
        plan.append(dict(source=src,destination=n));indexed[n]=src
    if n not in files:
        files[n]={'source':src,'sha256':h,'bytes':blob.stat().st_size,'kind':'camera_preflight_input','hash_basis':'effective_camera_ExecStartPre'}
    else: assert files[n]['source']==src and files[n]['sha256']==h
meta.update({'source':'Named public files read over SSH using the trusted board key. No board write or service action.','camera_prestart':groups,'camera_prestart_unique_paths':len(wanted)})
save(ROOT/'board/config/public_board_resources.json',meta)
save(ROOT/'board/config/deployment_files.json',plan)
qa=load(QA/'board_public_copy.json')
qa.update({'current_camera_prestart_rules':len(groups),'camera_prestart_files_matched_on_board':len(wanted),'unique_public_file_destinations':len(files)})
save(QA/'board_public_copy.json',qa)
print('20 runtime checks:',len(groups),'distinct files checked on board',len(wanted),'new source bytes at',added,'paths; total destinations',len(files))
