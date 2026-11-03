import json,subprocess
from pathlib import Path
p=Path('/home/root/aura-native-wait-20261023/uprobe-isolated/e977c9df9c2d3bcb/fixture.so')
r={}
for key,args in [('fixture_disassembly',['objdump','-d','--start-address=0x7b0','--stop-address=0x840',str(p)]),('kernel',['dmesg'])]:
 c=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 r[key]=c.stdout if key!='kernel' else '\n'.join(line for line in c.stdout.splitlines()[-200:] if any(x in line.lower() for x in ('uprobe','fixture.so','aura_iso')))
 r[key+'_exit']=c.returncode
q=Path('/sys/kernel/tracing/error_log')
r['trace_errors']=q.read_text()[-4000:] if q.exists() else None
print(json.dumps(r))
