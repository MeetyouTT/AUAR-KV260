import json
from pathlib import Path
p=Path('/home/root/aura-boundary-nav-20261029/state.json')
s=json.loads(p.read_text())
assert s['phase']=='VERIFIED' and s['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
s['board_wall_clock_utc']=s.pop('verified_utc',s.get('board_wall_clock_utc'))
s['verified_host_utc']='2026-10-29T06:15:22Z'
s['time_source_note']='Host UTC is evidence time; board wall clock is unsynchronized.'
p.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(s))
