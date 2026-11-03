import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
s=json.loads((root/'state.json').read_text());folder=Path(s['benchmark_result']).parent.parent if s.get('benchmark_result') else root/('benchmark-'+Path('/proc/sys/kernel/random/boot_id').read_text().strip())
value={'state':s,'uptime':Path('/proc/uptime').read_text().split()[0]}
for name in ['result.json','checkpoint.json']:
 p=folder/'result'/name
 if p.exists():value[name]=json.loads(p.read_text())
value['controller_status']=subprocess.check_output(['systemctl','show','aura-native-equivalence-be72669aa53de735.service','-p','ActiveState','-p','SubState','-p','MainPID'],text=True)
if s.get('benchmark_pid'):
 p=Path('/proc')/str(s['benchmark_pid'])/'status'
 value['process_alive']=p.exists()
 if p.exists():value['process_state']=[line for line in p.read_text().splitlines() if line.startswith(('State:','Threads:'))]
log=folder/'benchmark.log'
if log.exists():value['log_tail']=log.read_text(errors='replace')[-2000:]
print(json.dumps(value))
