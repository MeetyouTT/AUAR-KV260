import json
from pathlib import Path
t=Path('/sys/kernel/tracing')
r={name:(t/name).read_text().strip() if (t/name).exists() else None for name in ('trace_clock','available_tracers','options/nsecs')}
p=t/'error_log'
r['own_error_lines']=[line for line in p.read_text().splitlines() if 'aura_iso_6781bbb12d73edb2' in line or 'fixture.so' in line][-12:] if p.exists() else []
r['owned_events']=[line for line in (t/'uprobe_events').read_text().splitlines() if 'aura_iso_' in line]
r['own_instance_exists']=(t/'instances/aura_iso_6781bbb12d73edb2').exists()
print(json.dumps(r))
