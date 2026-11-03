from pathlib import Path
import hashlib,json,subprocess,zipfile
base=Path('/home/root/aura-yuki-validation-20261030');phase=base/'native_integration'
allowed=[]
for p in (phase/'results').rglob('*'):
    if p.is_file() and p.suffix in ('.json','.png','.log','.so','.cpp','.hpp'):allowed.append(p)
for name in ('host-build-result.json','host-test-result.json','egl-gtk-probe.json','glarea-probe.json','egl-configs.json'):
    if (phase/name).exists():allowed.append(phase/name)
for name in ('libaura_yuki.so','yuki_frame_export','yuki_runtime_audit','yuki_tile_uv_test'):
    if (phase/'build_host'/name).exists():allowed.append(phase/'build_host'/name)
record={'production_ui':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True),
 'source_hashes':{p.relative_to(phase).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (phase/'host').glob('*') if p.is_file()},
 'production_deployed':False,'files':{p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in allowed}}
archive=base/'phase-native-evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as out:
    for p in allowed:out.write(p,p.relative_to(base).as_posix())
    out.writestr('native_integration/collection-manifest.json',json.dumps(record,indent=2))
print(json.dumps({'files':len(allowed),'bytes':archive.stat().st_size,'archive':archive.name}))
