import hashlib,json,subprocess
from pathlib import Path
p=Path('/usr/lib/libvart-dpu-runner.so.3.0.0')
symbols=subprocess.check_output(['nm','-D','-C','--defined-only',str(p)],text=True)
rows=[line for line in symbols.splitlines() if ('DpuRunnerDdr::execute_async' in line or 'DpuRunnerDdr::wait(' in line or 'DpuRunnerBaseImp::start_dpu2' in line)]
code={}
for row in rows:
 address=int(row.split()[0],16);count=16 if '::wait(' in row else 320
 code[row]=subprocess.check_output(['objdump','-d','-C','--start-address='+hex(address),'--stop-address='+hex(address+count),str(p)],text=True)
print(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,
 'symbols':rows,'disassembly':code,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
