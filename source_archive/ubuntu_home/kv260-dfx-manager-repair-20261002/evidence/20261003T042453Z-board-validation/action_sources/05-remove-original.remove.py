import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2052fe46637f6a7c5f5a67ecdc46439e849057b4a75aad4d1ccbf2ed74d38b37'
exec(compile(s,str(p),'exec'))
gate('0991D1B457855C8987936E6','kv260-benchmark-b4096');manager_guard(False)
snapshot('BEFORE')
subprocess.run(['dfx-mgr-client','-remove'],check=True)
gate('0991D1B457855C8987936E6',None)
assert not Path('/sys/bus/platform/devices/axi:zyxclmm_drm').exists()
snapshot('AFTER')
