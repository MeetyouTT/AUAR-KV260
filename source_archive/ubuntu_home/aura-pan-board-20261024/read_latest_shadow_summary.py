"""Read only the filtered summary for the most recent shadow attempt."""
import json
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-follow-shadow-live/runs')
runs=sorted((p for p in root.glob('live-*') if p.is_dir()),key=lambda p:p.name)
assert runs
p=runs[-1]/'shadow.jsonl.summary.json';d=json.loads(p.read_text())
print(json.dumps({'run_dir':runs[-1].name,'summary':d},sort_keys=True))
