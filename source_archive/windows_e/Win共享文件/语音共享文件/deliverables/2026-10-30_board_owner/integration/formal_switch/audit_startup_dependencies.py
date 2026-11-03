"""Offline added-import closure against original286 and formal26; no imports."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'resume_runtime/fresh_source/aura'
pins=json.loads((HERE.parent/'resume_ui_trial_round2/policy.json').read_bytes())['pins']
manifest=json.loads((HERE/'manifest.json').read_bytes())
modules={name[:-3].replace('/','.') for name in pins if name.endswith('.py')}
modules.update(name[5:-3].replace('/','.') for name in manifest['files'] if name.startswith('aura/') and name.endswith('.py'))
prefixes={'board','common','tools','host','workflows'}

def imports(raw,owner):
    result=set()
    for node in ast.walk(ast.parse(raw)):
        if isinstance(node,ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom):
            name=node.module or ''
            if node.level:
                package=owner.split('.')[:-node.level]
                name='.'.join(package+([name] if name else []))
            if name.split('.')[0] not in prefixes:continue
            if name in modules:result.add(name)
            else:
                for alias in node.names:
                    child=name+'.'+alias.name
                    if child in modules:result.add(child)
                    elif any(value.startswith(name+'.') for value in modules):
                        # A package attribute may be a class, not a submodule.
                        result.add(name)
                    else:result.add(name)
    return {name for name in result if name.split('.')[0] in prefixes}

rows=[]
missing={}
for relative in manifest['files']:
    if not relative.startswith('aura/') or not relative.endswith('.py'):continue
    name=relative[5:]
    owner=name[:-3].replace('/','.')
    raw=(HERE/'overlay'/relative).read_bytes()
    added=imports(raw,owner)
    if name in pins:
        before=BASE/name
        assert before.is_file() and hashlib.sha256(before.read_bytes()).hexdigest()==pins[name]
        added-=imports(before.read_bytes(),owner)
    for dependency in sorted(added):
        exists=dependency in modules or any(value.startswith(dependency+'.') for value in modules)
        rows.append(dict(source=name,added_import=dependency,in_original_or_overlay=exists))
        if not exists:missing.setdefault(dependency,[]).append(name)
device=HERE.parents[3]/'aura/common/device_policy.py'
device_raw=device.read_bytes()
assert not any(isinstance(node,(ast.Import,ast.ImportFrom)) for node in ast.walk(ast.parse(device_raw)))
result=dict(status='ONE_MISSING_PURE_CONSTANT_DEPENDENCY',original_pins=len(pins),
    overlay_files=len(manifest['files']),added_project_imports=rows,missing=missing,
    required_addition=dict(path='aura/common/device_policy.py',bytes=len(device_raw),sha256=hashlib.sha256(device_raw).hexdigest(),
        import_count=0),device_or_model_or_service_or_database_calls=False)
(HERE/'startup_dependency_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=True))
