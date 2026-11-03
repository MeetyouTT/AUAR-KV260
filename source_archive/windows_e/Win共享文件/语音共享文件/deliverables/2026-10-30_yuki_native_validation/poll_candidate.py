from pathlib import Path
import json
root = Path('/home/root/aura-yuki-validation-20261030')
for name in ['candidate-result.json', 'candidate-cpu-audit.json', 'capture-result.json', 'candidate-captures/render-report.json']:
    path = root / name
    if not path.exists(): continue
    data = json.loads(path.read_text())
    if name != 'candidate-cpu-audit.json':
        print(name, json.dumps({k:v for k,v in data.items() if k not in ('before_ui','after_ui')}, ensure_ascii=False))
    else:
        failures = [t for t in data.get('timelines',[]) if not t.get('ok')]
        print(name, json.dumps({'compiled': data['compiled'], 'ok': data['ok'],
              'initial_pose': data.get('initial_pose'), 'timeline_count': len(data.get('timelines',[])),
              'timeline_pass': len(data.get('timelines',[]))-len(failures),
              'first_failure': failures[:1]},ensure_ascii=False))
for name in ['candidate.log', 'candidate-exception.log', 'capture.log', 'capture-exception.log']:
    path = root / name
    if path.exists():print(name, '\n'.join(path.read_text(errors='replace').splitlines()[-10:]))
