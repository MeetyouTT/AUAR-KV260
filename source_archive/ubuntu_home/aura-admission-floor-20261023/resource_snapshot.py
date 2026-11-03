"""One bounded driver CU/CPU snapshot, no runner creation or synthetic input."""
import fcntl,hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
SOURCE=Path(__file__).resolve();TOKEN=hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT=Path('/home/root/aura-admission-floor-20261023/resource')/TOKEN
BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
CU=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto')
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def cmd(args):return subprocess.check_output(args,stderr=subprocess.PIPE,text=True,timeout=10).strip()
def prop(unit,name):return cmd(['systemctl','show',unit,'-p',name,'--value'])
def atomic(p,v):
    q=p.with_name(p.name+'.tmp-'+str(os.getpid()))
    with q.open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(q,p)
def camera():
    with OP.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
    s=h['dpu_schedule']
    return {'pid':h['pid'],'detected_frames':h['detected_frames'],'yolo_hz':h['detection_hz'],
        'face_processed':h['identity']['face_targets']['processed'],
        'optional_calls':{k:v['calls'] for k,v in s['optional'].items()},
        'optional_overruns':{k:v['overruns'] for k,v in s['optional'].items()},
        'sface_completed':h['identity']['feature_inference']['completed'],
        'primary_overruns':s['primary_period_overruns'],'admission_floor_ms':s.get('admission_floor_ms')}
def cpu():
    fields=[int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    processes={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            f=(p/'stat').read_text().rsplit(') ',1)[1].split()
            processes[int(p.name)]=(int(f[1]),int(f[11])+int(f[12]),int(f[19]))
        except (OSError,ValueError,IndexError):pass
    return {'mono':time.monotonic(),'total':sum(fields),'idle':fields[3]+fields[4],'processes':processes}
def group(sample,leader):
    members={leader};rows=sample['processes']
    while True:
        new=members|{pid for pid,(parent,_,_) in rows.items() if parent in members}
        if new==members:return {p:rows[p] for p in members if p in rows}
        members=new
def stats():
    raw=[int(n) for n in (CU/'stat').read_text().split()];assert len(raw)==8
    return {'mono':time.monotonic(),'raw':raw}
def off():
    if not (ROOT/'ownership.json').exists():return
    meta=json.loads((ROOT/'ownership.json').read_text())
    if meta.get('active') and meta['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip():
        (CU/'stats_end').read_text();meta['active']=False;atomic(ROOT/'ownership.json',meta)
def run():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert (CU/'base_paddr').read_text().strip()=='0xa0010000' and 'DPUCZDX8G' in (CU/'cu_info').read_text()
    assert stats()['raw'][0]==0,'Another statistics collector may be active'
    leaders={unit:int(prop(unit,'MainPID')) for unit in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
    before=camera();assert before['pid']==leaders['aura-camera-ui.service'] and before['admission_floor_ms']==30.
    guard='aura-resource-off-'+TOKEN
    atomic(ROOT/'ownership.json',{'boot':BOOT,'active':True})
    cmd(['systemd-run','--unit='+guard,'--on-active=30s','--property=RuntimeMaxSec=15',
        '/usr/bin/python3','-B',str(SOURCE),'--off'])
    assert prop(guard+'.timer','ActiveState')=='active'
    report={'scope':'15_SECONDS_UNPAIRED_CURRENT_WORKLOAD_NOT_OPTIMIZATION_GAIN',
        'boot':BOOT,'before':before,'dpu_jobs_submitted':0,'synthetic_input_used':False,
        'cu_stat_field_order':['completed','completed_delta','in_flight','average_submitted_queue',
            'max_submitted_queue','max_running','iops','idle_percent'],'samples':[]}
    try:
        (CU/'stats_begin').read_text();time.sleep(1.1)
        start=stats();first=cpu();previous=start
        for i in range(1,16):
            time.sleep(max(0.,first['mono']+i-time.monotonic()))
            s=stats();assert 0<=s['raw'][7]<=100
            s['duration']=s['mono']-previous['mono'];s['busy_percent']=100-s['raw'][7]
            report['samples'].append(s);previous=s
        last=cpu();after=camera();assert after['pid']==before['pid']
        duration=last['mono']-first['mono'];total=last['total']-first['total']
        groups={}
        for unit,leader in leaders.items():
            assert int(prop(unit,'MainPID'))==leader
            a=group(first,leader);b=group(last,leader)
            assert a.keys()==b.keys() and all(a[p][2]==b[p][2] for p in a)
            one=100*sum(b[p][1]-a[p][1] for p in a)/os.sysconf('SC_CLK_TCK')/duration
            groups[unit]={'pids':sorted(a),'one_core_percent':one,'board_percent':one/os.cpu_count()}
        report.update(after=after,duration_seconds=duration,
            board_cpu_busy_percent=100*(total-last['idle']+first['idle'])/total,process_groups=groups,
            dpu_task_busy_percent=sum(s['busy_percent']*s['duration'] for s in report['samples'])/sum(s['duration'] for s in report['samples']),
            completed_driver_commands=previous['raw'][0]-start['raw'][0],
            dpu_scope='Driver CU task busy includes driver-defined execution; not FPGA LUT/DSP occupancy or model-only speedup; integer percent samples')
    finally:
        off();cmd(['systemctl','stop',guard+'.timer'])
        a=stats();time.sleep(.25);b=stats()
        report['statistics_counter_stopped']=a['raw'][0]==b['raw'][0]
        report['guard_state']=prop(guard+'.timer','ActiveState')
        atomic(ROOT/'report.json',report)
    return report
if __name__=='__main__':
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    if sys.argv[1:]==['--off']:off()
    else:
        assert not sys.argv[1:]
        with (ROOT/'probe.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            assert not (ROOT/'report.json').exists();print(json.dumps(run()))
