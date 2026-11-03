from pathlib import Path
import json
root = Path('/home/root/aura-yuki-validation-20261030')
for name in ['build-result.json', 'build-exception.json', 'resume-result.json', 'cpu-run-result.json', 'cpu-audit.json']:
    path = root / name
    if path.exists():
        value = json.loads(path.read_text())
        if name == 'cpu-audit.json':
            value = {k: value.get(k) for k in ['structural_import_ok', 'compiled', 'ok',
                      'visual_certified', 'import_errors', 'import_warnings',
                      'unsupported_fields', 'compile_errors', 'geometry_diagnostics',
                      'initial_pose', 'timelines']}
        print(name, json.dumps(value, ensure_ascii=False))
for name in ['build.log', 'resume-build.log', 'resume-launcher.log', 'cpu-run.log', 'audit-launcher.log']:
    log = root / name
    if log.exists():
        print(name, '\n'.join(log.read_text(errors='replace').splitlines()[-8:]))
