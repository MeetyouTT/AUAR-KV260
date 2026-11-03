import hashlib,json
from pathlib import Path
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='c006a771-c3e4-4d4f-97d7-ade3dd774619'
p=ops/('native-run-'+boot+'-1333/config.json');raw=p.read_bytes();c=json.loads(raw)
d={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'native_execution':c['native_execution']}
f=ops/'native_entry_pan_face_v5.py';d['entry_source']=f.read_text()
print(json.dumps(d))
