import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/shadow_live.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='5cf53a19fb59c14d2a59a0ae968159a173402f34dbd3dbcdabdc35439a4ca0c3'
code=p.read_text()
a="s['phase']=='CURRENT_BOOT_R3_PREPARED_OUTPUT_STOPPED'"
assert code.count(a)==1 and code.count('shadow-v10r3-live10.json')==1
code=code.replace(a,"s['phase']=='CURRENT_BOOT_R3_SHADOW_PASS_OUTPUT_STOPPED'").replace('shadow-v10r3-live10.json','shadow-v10r3-live10-face.json')
exec(compile(code,str(p)+'-face-window','exec'))
