"""Prepare the GUI-status-tolerant launcher; no hardware IO or actuation."""
import hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='3e1add36-b917-4289-91dc-699348528782'
old=Path('/home/root/aura-pan-follow-20261020/prepared-wide-visible-01/execute.py')
assert hashlib.sha256(old.read_bytes()).hexdigest()=='368705eb0c20947b64ccf4b28e7fb51ab1286905810594f9dbe5d349ccd71e36'
text=old.read_text()
before="gui=get(8783,'/api/state')"
after="try:\n gui=get(8783,'/api/state')\nexcept Exception as gui_exc:\n gui={'phase':'STATUS_UNAVAILABLE','playing':None,'automatic_conversation':{'state':'UNKNOWN'}}"
assert text.count(before)==1
raw=text.replace(before,after).encode()
assert hashlib.sha256(raw).hexdigest()=='c00674778ad1ebd4fb3c3cd4f08aeaa60bb396344eb1942eca50b7db2bf5db57'
compile(raw,'wide-visible-execute2.py','exec')
d=Path('/home/root/aura-pan-follow-20261020/prepared-wide-visible-02')
d.mkdir(parents=True,exist_ok=False)
with (d/'execute.py').open('xb') as stream:stream.write(raw)
print(json.dumps({'status':'PREPARED_NO_ACTUATION','sha256':'c00674778ad1ebd4fb3c3cd4f08aeaa60bb396344eb1942eca50b7db2bf5db57','only_change':'GUI HTTP status read tolerates unavailability; motion payload and identity sampling gate unchanged'}),flush=True)
