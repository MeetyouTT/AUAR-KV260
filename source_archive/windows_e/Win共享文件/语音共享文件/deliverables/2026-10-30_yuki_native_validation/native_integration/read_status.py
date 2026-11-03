from pathlib import Path
import json
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
for result in ('host-build-result.json','host-test-result.json','results/mask-comparison.json','results/continuous.json','results/gtk-clock.json'):
    path=root/result
    if path.exists():print(result,path.read_text()[:6500])
log=root/'host-build.log'
if not (root/'host-test-result.json').exists() and log.exists():print('BUILD_LOG_TAIL',log.read_text()[-2800:])
log=root/'host-test.log'
if log.exists():print('TEST_LOG_TAIL',log.read_text()[-6000:])
