"""Check GPU IRQ activity and driver initialization without changing counters."""
import json,subprocess,time,urllib.request
from pathlib import Path
def irq():
    return [l.strip() for l in Path('/proc/interrupts').read_text().splitlines() if 'mali' in l.lower()]
def display():
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
    d=u.get('avatar_display',{})
    return {k:d.get(k) for k in ('frames','sequence','kind','target_fps','visible','age_ms')}
p=subprocess.run(['dmesg'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5)
logs=[l for l in p.stdout.splitlines() if 'mali' in l.lower() and any(s in l.lower() for s in ('utilization','driver','gpu','profiling'))]
a=irq();d0=display();start=time.monotonic();time.sleep(2);b=irq();d1=display()
print(json.dumps({'irq_before':a,'irq_after':b,'display_before':d0,'display_after':d1,'duration_s':time.monotonic()-start,'driver_boot_metadata':logs[-20:],'dmesg_exit':p.returncode}))
