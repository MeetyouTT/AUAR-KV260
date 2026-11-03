import json,subprocess
from pathlib import Path
out={'status':'READ_ONLY_REBOOT_EVIDENCE','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
     'uptime_seconds':Path('/proc/uptime').read_text().split()[0], 'pstore':{}}
for p in Path('/sys/fs/pstore').glob('*'):
 if not p.is_file():continue
 lines=p.read_bytes()[:131072].decode(errors='replace').splitlines()
 out['pstore'][p.name]=[line for line in lines if any(x in line.lower() for x in ('panic','watchdog','call trace','out of memory','oom-kill','reboot','segfault','fatal','error'))][-20:]
for name,args in [('boots',['journalctl','--list-boots','--no-pager']),('previous_kernel',['journalctl','-b','-1','-k','-p','err','-n','15','--no-pager','-o','cat'])]:
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
 out[name]={'returncode':p.returncode,'output':p.stdout[-3000:]}
out['kernel_panic_timeout']=Path('/proc/sys/kernel/panic').read_text().strip()
print(json.dumps(out),flush=True)
