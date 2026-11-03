import json,time
from pathlib import Path
root=Path('/home/root/aura-display-sequence-20261024/a878bbd5303bf1a3')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='25b3d8ed-84e5-4a81-a2d6-6c8de1733a5f'
if not (root/'result.json').exists():
 p=root/'finish'
 if not p.exists():
  with p.open('x') as out:json.dump({'requested_mono_ns':time.monotonic_ns(),'user_result':'bad_before_replug_normal_after_replug_same_boot'},out)
until=time.monotonic()+22
while time.monotonic()<until and not (root/'result.json').exists():time.sleep(.2)
p=root/'result.json'
print(json.dumps({'ready':p.exists(),'report':json.loads(p.read_text()) if p.exists() else None,
 'state':json.loads((root/'state.json').read_text()),
 'own_trace_instance_exists':Path('/sys/kernel/tracing/instances/aura_hdmi_a878bbd5303bf1a3').exists()}))
