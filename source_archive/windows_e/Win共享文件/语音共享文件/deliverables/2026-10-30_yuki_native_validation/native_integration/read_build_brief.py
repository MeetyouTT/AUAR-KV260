from pathlib import Path
import json
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
state=json.loads((root/'host-build-state.json').read_text());p=Path('/proc',str(state['pid']),'cmdline')
print('build_worker_active',p.exists() and b'host_build_worker.py' in p.read_bytes())
print((root/'host-build.log').read_text()[-1000:])
print((root/'host-build-result.json').read_text())
path=root/'results/optimized-test-result.json'
if path.exists():print(path.read_text())
path=root/'results/complete-parameter-render.json'
if path.exists():print(path.read_text())
