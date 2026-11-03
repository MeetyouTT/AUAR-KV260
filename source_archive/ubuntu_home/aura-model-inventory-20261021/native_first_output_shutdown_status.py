import json,time
from pathlib import Path
root=Path('/home/root/aura-native-coldboot-20261024/376e4921416108f4')
p=root/'shutdown.json'
until=time.monotonic()+10
while not p.exists() and time.monotonic()<until:time.sleep(.1)
print(json.dumps({'report_exists':p.exists(),'report':json.loads(p.read_text()) if p.exists() else None}))
