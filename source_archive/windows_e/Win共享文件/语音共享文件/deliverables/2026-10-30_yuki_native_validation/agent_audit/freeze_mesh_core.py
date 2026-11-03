from pathlib import Path
import hashlib
import json

root=Path(__file__).resolve().parent.parent
core=root/'native_integration/candidate_core'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files={}
for folder in ('src','include'):
    for p in (core/folder).rglob('*'):
        if p.is_file() and p.suffix in ('.cpp','.hpp','.h'):
            files[p.relative_to(core).as_posix()]=sha(p)
evidence=root/'evidence/native_integration/mesh_evidence'
tests=json.loads((evidence/'self-test.json').read_text(encoding='utf-8'))
real=json.loads((evidence/'real-grids.json').read_text(encoding='utf-8'))
audit=json.loads((evidence/'runtime-audit.json').read_text(encoding='utf-8'))
report={'phase':'mesh implementation production-TU freeze, before parent mask-boundary change',
    'production_frozen':True,'engine_sdk_parity':False,'core_root':str(core),
    'files':files,'changed_vs_frozen_upstream':[name for name,h in files.items()
        if not (root/'source'/name).exists() or sha(root/'source'/name)!=h],
    'evidence_sha256':{p.name:sha(p) for p in evidence.glob('*') if p.is_file()},
    'self_tests':{'ok':tests['ok'],'count':len(tests['tests']),
                  'benchmark':tests.get('geometry_benchmark')},
    'real_grids':{k:real.get(k) for k in ('ok','import_ok','combinators','controls','variable_count','changing_samples')},
    'runtime':{'ok':audit.get('ok'),'compiled':audit.get('compiled'),
               'initial_pose':audit.get('initial_pose'),
               'remaining_unsupported_fields':audit.get('unsupported_fields')},
    'no_production_deploy_or_restart':True}
out=Path(__file__).parent/'mesh_core_freeze.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'manifest':str(out),'geometry_sha':files['src/runtime/geometry_scene.cpp'],
    'self_tests':report['self_tests'],'real':report['real_grids'],'runtime':report['runtime']},
    ensure_ascii=True))
