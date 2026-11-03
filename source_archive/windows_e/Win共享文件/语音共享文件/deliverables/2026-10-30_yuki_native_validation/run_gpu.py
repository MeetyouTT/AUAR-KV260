from pathlib import Path
import hashlib
import json
import subprocess
import time
root = Path('/home/root/aura-yuki-validation-20261030')
before = subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True)
argv = ['nice','-n','15','python3',str(root/'probe_build/gles2_capture.py'),
        str(root/'candidate-frames.json'),str(root/'candidate-captures')]
started=time.monotonic()
with (root/'gpu-render-r2.log').open('w') as log:
    p = subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=60)
after = subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True)
result={'argv':argv,'returncode':p.returncode,'elapsed_seconds':time.monotonic()-started,
        'ui_unchanged':before==after,'script_sha256':hashlib.sha256((root/'probe_build/gles2_capture.py').read_bytes()).hexdigest(),
        'performance_certified':False,'production_accepted':False}
(root/'gpu-render-r2-result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
print((root/'gpu-render-r2.log').read_text()[-3500:])
