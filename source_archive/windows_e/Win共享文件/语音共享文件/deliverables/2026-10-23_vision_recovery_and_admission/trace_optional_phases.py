"""Bounded native/GIL phases of existing optional calls, never submit a job."""
import fcntl,hashlib,importlib.util,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path

SOURCE=Path(__file__).resolve();TOKEN=hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT=Path('/home/root/aura-sface-recovery-20261023/phase')/TOKEN
SUPPORT=Path('/home/root/aura-post-power-20261022/helpers/9c8f8702f68a4d24/source.py')
assert hashlib.sha256(SUPPORT.read_bytes()).hexdigest()=='9c8f8702f68a4d24c76be06e1c1ad575d0c53a77e353a78b8bb89b15e1e658e4'
spec=importlib.util.spec_from_file_location('_optional_trace_support',SUPPORT)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.SOURCE=SOURCE;h.ROOT=ROOT;h.GROUP='aura_optional_'+TOKEN;h.INSTANCE=h.TRACE/'instances'/h.GROUP
h.BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
h.GUARD='aura-optional-phase-cleanup-'+TOKEN
PROMOTION=Path('/home/root/aura-sface-recovery-20261023/promotion/4bcbe0999c62a348/report.json')
DURATION=600
LIB=Path('/usr/lib/python3.9/site-packages/vart.so')
LIB_SHA='dc6bff9be31b8dc349a72489e06237f8503175805d042025558694823f61de34'
POINTS={'native_enter':(0x10a04,0xaa1403e0),'native_return':(0x10a10,0xaa0003f6),
        'restore_enter':(0x10a1c,0xaa1303e0),'restore_return':(0x10a24,0xa94ad7f3)}
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
    with OP.open('http://127.0.0.1:8790/health',timeout=4) as stream:value=json.load(stream)
    return {'pid':value['pid'],'detected_frames':value['detected_frames'],'detection_hz':value['detection_hz'],
        'schedule':value['dpu_schedule'],'feature':value['identity']['feature_inference'],
        'gap':value['identity']['face_targets']['freshness_metrics']['counters']['observed_gap_intervals']}
def birth(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
def parse(raw,allowed):
    regex=re.compile(r'-(\d+)\s+\[\d+\].*?\s(\d+)\.(\d+):\s+(?:'+h.GROUP+r':)?('+('|'.join(h.NAMES))+r'):')
    events=[];cycles=[];pending={};partial=0;digits=set()
    for line in raw.splitlines():
        found=regex.search(line)
        if not found:continue
        tid,sec,frac,name=found.groups();tid=int(tid)
        assert tid in allowed and len(frac)<=9
        stamp=int(sec)*1000000000+int(frac.ljust(9,'0'));digits.add(len(frac));events.append([tid,stamp,name])
        current=pending.get(tid,[])
        if name==h.NAMES[0]:
            if current:partial+=1
            current=[stamp]
        elif current and name==h.NAMES[len(current)]:current.append(stamp)
        else:partial+=1;pending.pop(tid,None);continue
        if len(current)==4:
            assert current==sorted(current)
            cycles.append({'tid':tid,'start_ns':current[0],'native_return_ns':current[1],
                'restore_start_ns':current[2],'restore_return_ns':current[3],
                'native_ms':(current[1]-current[0])/1e6,'between_ms':(current[2]-current[1])/1e6,
                'restore_ms':(current[3]-current[2])/1e6})
            pending.pop(tid,None)
        else:pending[tid]=current
    return {'events':events,'cycles':cycles,'partial_sequences':partial+len(pending),'fraction_digits':sorted(digits)}

def run():
    cpu_start=time.process_time_ns();wall_start=time.monotonic_ns()
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==h.BOOT
    root_report=json.loads(PROMOTION.read_text());assert root_report['accepted'] and root_report['passed']
    before=health();pid=before['pid'];born=birth(pid)
    assert pid==root_report['candidate_camera_pid'] and not before['schedule']['owner_fenced']
    assert h.sha(LIB)==LIB_SHA
    rawlib=LIB.read_bytes()
    for off,op in POINTS.values():assert int.from_bytes(rawlib[off:off+4],'little')==op
    allowed={int(p.name) for p in (Path('/proc')/str(pid)/'task').iterdir()}
    assert 1<=len(allowed)<=32
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    assert not (ROOT/'report.json').exists() and not h.INSTANCE.exists() and not h.owned_definitions()
    targets={name:str(LIB)+':0x'+format(v[0],'x') for name,v in POINTS.items()}
    h.save(ROOT/'ownership.json',{'source_sha256':h.sha(SOURCE),'group':h.GROUP,'boot':h.BOOT,'event_targets':targets})
    global_before=h.global_state();armed=False
    report={'complete':False,'passed':False,'boot':h.BOOT,'pid':pid,'birth_ticks':born,'before':before,
        'source_sha256':h.sha(SOURCE),'library_sha256':LIB_SHA,'record_tids':sorted(allowed),
        'dpu_jobs_submitted':0,'production_source_changed':False,'requested_seconds':DURATION,
        'scope':'Wall intervals with trace overhead; record filter does not remove other threads trap cost; not hardware busy time'}
    h.save(ROOT/'report.json',report)
    try:
        h.command(['systemd-run','--unit='+h.GUARD,'--on-active='+str(DURATION+30)+'s','--property=RuntimeMaxSec=30',
            '/usr/bin/python3','-B',str(SOURCE),'--cleanup'])
        assert h.command(['systemctl','show',h.GUARD+'.timer','-p','ActiveState','--value'])=='active';armed=True
        h.INSTANCE.mkdir();h.write(h.INSTANCE/'tracing_on','0');h.write(h.INSTANCE/'current_tracer','nop')
        h.write(h.INSTANCE/'buffer_size_kb','512');h.write(h.INSTANCE/'trace_clock','mono')
        filt=' || '.join('common_pid == '+str(tid) for tid in sorted(allowed))
        for name,target in targets.items():
            h.write(h.TRACE/'uprobe_events','p:'+h.GROUP+'/'+name+' '+target,True)
            event=h.INSTANCE/'events'/h.GROUP/name;h.write(event/'filter',filt);h.write(event/'enable','1')
        h.write(h.INSTANCE/'trace','');start=time.monotonic_ns();h.write(h.INSTANCE/'tracing_on','1')
        deadline=time.monotonic()+DURATION;after=before;observations=[]
        while time.monotonic()<deadline:
            time.sleep(min(5.,max(0.,deadline-time.monotonic())))
            assert birth(pid)==born
            after=health();assert after['pid']==pid
            observations.append({'mono_ns':time.monotonic_ns(),'faults':{k:v['overruns'] for k,v in after['schedule']['optional'].items()},'primary_overruns':after['schedule']['primary_period_overruns']})
            if after['schedule']['owner_fenced'] or any(after['schedule']['optional'][k]['overruns']>before['schedule']['optional'][k]['overruns'] for k in ('yunet','sface')):break
        h.write(h.INSTANCE/'tracing_on','0');end=time.monotonic_ns()
        report.update(parse((h.INSTANCE/'trace').read_text(),allowed))
        loss={}
        for p in (h.INSTANCE/'per_cpu').glob('cpu*/stats'):
            text=p.read_text();loss[p.parent.name]={key:int(re.search(r'^'+re.escape(key)+r':\s*(\d+)',text,re.M).group(1)) for key in ('overrun','commit overrun','dropped events')}
        assert loss
        report.update(after=after,observations=observations,lost_events=loss,start_ns=start,end_ns=end,actual_seconds=(end-start)/1e9)
        report['measurement_passed']=bool(report['cycles']) and not any(n for row in loss.values() for n in row.values())
    except Exception as error:report['error']=type(error).__name__+': '+str(error)
    finally:
        report['cleanup']=h.cleanup();report['global_state_unchanged']=h.global_state()==global_before
        if armed and report['cleanup']['passed']:h.command(['systemctl','stop',h.GUARD+'.timer'])
        report['guard_state']=h.command(['systemctl','show',h.GUARD+'.timer','-p','ActiveState','--value'])
        seconds=(time.monotonic_ns()-wall_start)/1e9
        report['controller_cpu_one_core_percent']=(time.process_time_ns()-cpu_start)/1e9/seconds*100.
        report['controller_cost_scope']='Controller through setup/cleanup; child systemctl and final serialization excluded; target traps separately costed on fixture'
        report['complete']=True;report['root_cause_fixed']=False
        report['passed']=(report.get('measurement_passed',False) and report['cleanup']['passed']
            and report['global_state_unchanged'] and report['guard_state']=='inactive'
            and report['controller_cpu_one_core_percent']<=2.)
        h.save(ROOT/'report.json',report)
    return report

if __name__=='__main__':
    if sys.argv[1:]==['--cleanup']:print(json.dumps(h.cleanup()))
    elif sys.argv[1:]==['--run']:
        ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
        with (ROOT/'controller.lock').open('a+') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run()
    else:
        assert not sys.argv[1:] and not (ROOT/'report.json').exists()
        unit='aura-optional-phase-'+TOKEN
        h.command(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec='+str(DURATION+60),
            '/usr/bin/python3','-B',str(SOURCE),'--run'])
        print(json.dumps({'started':True,'unit':unit,'report':str(ROOT/'report.json'),'source_sha256':h.sha(SOURCE)}))
