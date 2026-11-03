from pathlib import Path
import json
root=Path('/home/root/aura-yuki-validation-20261030/native_integration/results')
for name in ('optimized-test-result.json','bp-diagnostic-result.json','bp-diagnostic-render.json','gtk-clock.json'):
    p=root/name
    if p.exists():print(name,p.read_text()[:8000])
