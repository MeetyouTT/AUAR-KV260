from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).parent;source=root/'precision_candidate';dest=root/'host'
freeze=json.loads((source/'freeze.json').read_text(encoding='utf8'))
backup=root/'host_before_precision';backup.mkdir(exist_ok=True)
for name in freeze['required_renderer_files']:
    data=(source/name).read_bytes();assert hashlib.sha256(data).hexdigest()==freeze['hashes'][name]
    if (dest/name).exists() and not (backup/name).exists():shutil.copyfile(dest/name,backup/name)
    (dest/name).write_bytes(data)
for name,old,new in (
 ('yuki_host.cpp','std::make_unique<aura_yuki::Renderer>(scene,root)','std::make_unique<aura_yuki::Renderer>(scene,imported.asset,root)'),
 ('diagnostic_api.cpp','std::make_unique<aura_yuki::Renderer>(*scene,root)','std::make_unique<aura_yuki::Renderer>(*scene,input.asset,root)')):
    path=dest/name;data=path.read_text(encoding='utf8')
    assert data.count(old)==1;path.write_text(data.replace(old,new),encoding='utf8')
path=dest/'yuki_host.cpp';data=path.read_text(encoding='utf8')
old='instance->transition(arm,float(pose),initial?0:6)';assert data.count(old)==1
path.write_text(data.replace(old,'instance->transition(arm,float(pose),0)'),encoding='utf8')
(root/'precision-merge.json').write_text(json.dumps({'frozen_files':{name:freeze['hashes'][name] for name in freeze['required_renderer_files']},
 'pose_selector':'instant discrete selection, matching the original driver','production_deployed':False},indent=2),encoding='utf8')
print('PRECISION_RENDERER_MERGED; CPP_GPU_VALIDATION_PENDING')
