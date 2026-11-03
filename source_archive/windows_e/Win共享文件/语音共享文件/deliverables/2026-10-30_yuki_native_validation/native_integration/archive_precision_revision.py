from pathlib import Path
import hashlib,json,shutil
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');out=root/'results'
dest=out/'revision-r6-per-icon-before-state-cache'
assert not dest.exists();dest.mkdir()
for name in ('precision-validation-result.json','precision-images.json','continuous.json','continuous-samples.json','gtk-clock.json','gtk-clock-samples.json','gtk-final.png'):
    if (out/name).exists():shutil.copyfile(out/name,dest/name)
for name in ('gles2_renderer.cpp','gles2_renderer.hpp','tile_uv.hpp','yuki_host.cpp'):
    shutil.copyfile(root/'host'/name,dest/name)
shutil.copyfile(root/'build_host/libaura_yuki.so',dest/'libaura_yuki.so')
record=dict(reason='GTK P99 62.9944ms exceeds unchanged62.5ms gate; image and clock/control checks PASS',
  files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir() if p.is_file()})
(dest/'manifest.json').write_text(json.dumps(record,indent=2));print(json.dumps(dict(archived=str(dest),files=len(record['files']))))
