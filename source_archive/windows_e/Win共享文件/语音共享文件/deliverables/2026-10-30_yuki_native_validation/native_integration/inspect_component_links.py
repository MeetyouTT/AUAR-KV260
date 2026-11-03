from pathlib import Path
import json
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration')
basis=json.loads((phase/'board_source/manifest.json').read_text());runtime=Path(basis['runtime']);outside=[]
for name in basis['component_pins']:
    path=runtime/'aura'/name;resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(runtime):outside.append(dict(name=name,target=str(resolved),symlink=path.is_symlink()))
(phase/'results/current-component-link-targets.json').write_text(json.dumps(outside,indent=2))
print(json.dumps(dict(count=len(outside),examples=outside[:12],target_roots=sorted({str(Path(row['target']).parents[3]) for row in outside}))))
