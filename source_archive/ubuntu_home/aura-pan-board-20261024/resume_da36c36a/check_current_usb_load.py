import json,os,subprocess,time,urllib.request
from pathlib import Path
start=time.monotonic();boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
def cpu():
 line=Path('/proc/stat').read_text().splitlines()[0].split()[1:];return [int(x) for x in line]
before=cpu();time.sleep(3);end=time.monotonic();after=cpu()
r=subprocess.run(['journalctl','-k','-b','-n','300','-o','json','--no-pager'],capture_output=True,text=True,timeout=3)
rows=[json.loads(x) for x in r.stdout.splitlines()] if r.returncode==0 else []
stamp=lambda x:int(x.get('__MONOTONIC_TIMESTAMP','0'))/1000000
fresh=[x for x in rows if x.get('_BOOT_ID')==boot.replace('-','') and start<=stamp(x)<=end]
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
delta=[b-a for a,b in zip(before,after)];total=sum(delta[:8])
print(json.dumps({'boot_id':boot,'window_s':end-start,'journal_returncode':r.returncode,
 'retained_lines':len(rows),'tail_covers_window':bool(rows) and min(map(stamp,rows))<=start,
 'new_xhci_warnings':sum("couldn't access mem fast enough" in x.get('MESSAGE','') for x in fresh),
 'latest_kernel_event_mono_s':max(map(stamp,rows)) if rows else None,'latest_retained_xhci_event_mono_s':max([stamp(x) for x in rows if "couldn't access mem fast enough" in x.get('MESSAGE','')],default=None),
 'cpu_busy_fraction_all_cores':1-(delta[3]+delta[4])/total if total else None,'loadavg':os.getloadavg(),
 'camera_pid':h['pid'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()},'owner_fenced':h['dpu_schedule']['owner_fenced'],
 'motor_commands':0,'MMIO_opened':False,'services_restarted':False}))
