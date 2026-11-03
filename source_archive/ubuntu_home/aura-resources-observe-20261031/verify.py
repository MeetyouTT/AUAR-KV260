"""12-second service CPU/RSS breakdown plus GPU and XRT memory metadata."""
import json,os,subprocess,time
from pathlib import Path
def read(p):
    try:return Path(p).read_text().strip()
    except OSError as e:return {'error':type(e).__name__}
def snapshot():
    rows={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            t=(p/'stat').read_text();v=t.rsplit(') ',1)[1].split()
            rows[int(p.name)]={'ppid':int(v[1]),'ticks':int(v[11])+int(v[12]),'birth':int(v[19]),'rss_kib':int(v[21])*os.sysconf('SC_PAGE_SIZE')//1024,'comm':t[t.index('(')+1:t.rindex(')')]}
        except (OSError,IndexError,ValueError):pass
    return rows
def group(rows,leader):
    members={leader}
    while True:
        more=members|{p for p,v in rows.items() if v['ppid'] in members}
        if more==members:return sorted(members & rows.keys())
        members=more
leaders={}
for n in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service'):
    leaders[n]=int(subprocess.check_output(['systemctl','show',n,'-p','MainPID','--value'],text=True,timeout=4).strip())
a=snapshot();start=time.monotonic();time.sleep(12);b=snapshot();duration=time.monotonic()-start;hz=os.sysconf('SC_CLK_TCK');groups={}
for n,leader in leaders.items():
    ga=group(a,leader);gb=group(b,leader);common=[p for p in ga if p in gb and a[p]['birth']==b[p]['birth']]
    ticks=sum(b[p]['ticks']-a[p]['ticks'] for p in common)
    members=[]
    for p in gb:
        v=dict(b[p]);v['pid']=p
        v['board_cpu_percent']=100*(v['ticks']-a[p]['ticks'])/hz/duration/os.cpu_count() if p in common else None
        args=read('/proc/'+str(p)+'/cmdline');v['scripts']=[Path(s).name for s in args.split('\0') if s.endswith('.py')] if isinstance(args,str) else []
        rollup=read('/proc/'+str(p)+'/smaps_rollup')
        v['pss_kib']=next((int(l.split()[1]) for l in rollup.splitlines() if l.startswith('Pss:')),None) if isinstance(rollup,str) else None
        members.append(v)
    groups[n]={'board_cpu_percent':100*ticks/hz/duration/os.cpu_count(),'rss_sum_kib':sum(b[p]['rss_kib'] for p in gb),'pss_sum_kib':sum(v['pss_kib'] or 0 for v in members),'same_members':ga==gb,'members':members}
xrt=Path('/sys/devices/platform/axi/axi:zyxclmm_drm')
gpu=Path('/sys/kernel/debug/mali')
print(json.dumps({'duration_s':duration,'cpu_count':os.cpu_count(),'groups':groups,'xrt_memory':{n:read(xrt/n) for n in ('memstat','memstat_raw')},'xrt_memory_nodes':[p.name for p in xrt.iterdir() if any(k in p.name for k in ('mem','stat'))],'gpu_driver_profile_config':{str(p):read(p) for p in Path('/sys/module/mali/parameters').glob('*')},'gpu':{n:read(gpu/n) for n in ('version','utilization_pp','utilization_gp','utilization_gp_pp','gpu_memory')},'cu_stat':read(xrt/'CU.3.auto/stat')}))
