import hashlib
from pathlib import Path
p=Path('/home/root/kv260-zocl-repair-20261003T005805Z/baseline/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='99c1fc5c842a026c05531eb637080717e44aaa199220d8ab942fbfe430814a6e'
exec(compile(s,str(p),'exec'))
WORK=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
guard('0991D1B457855C8987936E6','kv260-benchmark-b4096')
import shutil
WORK.mkdir(exist_ok=False);b=WORK/'baseline';b.mkdir()
paths=['/usr/bin/dfx-mgrd','/usr/bin/dfx-mgr-client','/lib/systemd/system/dfx-mgr.service','/etc/dfx-mgrd/daemon.conf','/etc/dfx-mgrd/default_firmware','/etc/vart.conf','/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko']
for p in paths:shutil.copy2(p,str(b/Path(p).name))
ko=Path('/home/root/kv260-m3-boardtest-20261003T021012Z/repaired-zocl.ko')
assert digest(ko)=='5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412'
shutil.copy2(str(ko),str(WORK/'repaired-zocl.ko'))
(b/'state.json').write_text(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'parameters':PARAMS,'active':active_packages()}))
hashes={p:digest(p) for p in paths}
(b/'file-hashes.json').write_text(json.dumps(hashes,indent=2))
print('BACKUP '+json.dumps({'directory':str(b),'files':hashes}),flush=True)
snapshot('AFTER')
