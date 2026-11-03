"""Prepare task-owned Yuki files; no production paths are written."""
from pathlib import Path
import hashlib,json,shutil
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');root=phase/'paired_ab/yuki_runtime/aura'
root.mkdir(parents=True,exist_ok=True);assert root.resolve().is_relative_to(phase)
for relative in ('tools/native_yuki.py','tools/egl_window.py'):
    target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((phase/'host'/target.name).read_bytes())
target=root/'tools/libaura_yuki.so';shutil.copyfile(phase/'build_host/libaura_yuki.so',target)
for source in (phase/'runtime_assets').rglob('*'):
    if source.is_file():
        target=root/'assets/yuki'/source.relative_to(phase/'runtime_assets');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
config=dict(enabled=True,fps=16,library='tools/libaura_yuki.so',model='assets/yuki/model.runtime.json',resx='assets/yuki/yuk_0.ems.resx.json',resource_root='assets/yuki',seed=1)
files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
(phase/'paired_ab/yuki-root.json').write_text(json.dumps(dict(root=str(root),config=config,files=files),indent=2))
print(json.dumps(dict(root=str(root),files=len(files),production_written=False)))
