import hashlib,json,subprocess
from pathlib import Path
source=Path('/home/root/aura-post-power-20261022/helpers/15d8d8f6a596610a/source.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='15d8d8f6a596610a77f26c555f92877f3dad11a4535881cf63b914b7c99c618d'
p=subprocess.run(['/usr/bin/python3','-B',str(source),'--remove'],capture_output=True,text=True,timeout=10)
assert p.returncode==0,p.stderr
root=Path('/home/root/aura-display-sequence-20261024/deferred/15d8d8f6a596610a')
plan=json.loads((root/'plan.json').read_text())
print(json.dumps({'removal':json.loads(p.stdout),'plan':plan,'no_display_or_camera_restart':True,
 'current_boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
