"""One bounded phase observation of an existing SFace thread; no inference owner."""
import fcntl,hashlib,importlib.util,json,os,re,subprocess,sys,time
from pathlib import Path

SOURCE=Path(__file__).resolve()
TOKEN=hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT=Path('/home/root/aura-native-wait-20261023/vart-phase')/TOKEN
SUPPORT=Path('/home/root/aura-post-power-20261022/helpers/9c8f8702f68a4d24/source.py')
assert hashlib.sha256(SUPPORT.read_bytes()).hexdigest()=='9c8f8702f68a4d24c76be06e1c1ad575d0c53a77e353a78b8bb89b15e1e658e4'
spec=importlib.util.spec_from_file_location('_phase_trace_support',SUPPORT)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.SOURCE=SOURCE;h.TOKEN=TOKEN;h.ROOT=ROOT;h.GROUP='aura_vart_'+TOKEN
h.INSTANCE=h.TRACE/'instances'/h.GROUP;h.GUARD='aura-vart-phase-cleanup-'+TOKEN
GUI_ROOT=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce')
assert h.sha(GUI_ROOT/'gui_trial.py')=='1b782de0126abbbe6550050e41bfb2db22137449daf0c779285279e8cfee12b3'
sys.dont_write_bytecode=True;sys.path.insert(0,str(GUI_ROOT));import gui_trial as g
LIBRARY=Path('/usr/lib/python3.9/site-packages/vart.so')
LIB_SHA='dc6bff9be31b8dc349a72489e06237f8503175805d042025558694823f61de34'
# Non-branch neighbour points: native call includes three argument instructions;
# RestoreThread interval includes one argument move. All times include probes.
POINTS={'native_enter':(0x10a04,0xaa1403e0),'native_return':(0x10a10,0xaa0003f6),
        'restore_enter':(0x10a1c,0xaa1303e0),'restore_return':(0x10a24,0xa94ad7f3)}

def birth(pid,tid=None):
    p=Path('/proc')/str(pid)
    if tid is not None:p=p/'task'/str(tid)
    return int((p/'stat').read_text().rsplit(')',1)[1].split()[19])
def validate(pid,tid,pborn,tborn):
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==h.BOOT
    assert int(g.prop(g.CAMERA,'MainPID'))==pid==588727
    assert birth(pid)==pborn and birth(pid,tid)==tborn
    assert h.sha(g.UNIT)==g.UNIT_SHA and h.sha(LIBRARY)==LIB_SHA
    inode=str(LIBRARY.stat().st_ino)
    assert any(len(fields)>=6 and fields[-1]==str(LIBRARY) and fields[4]==inode
        for fields in (line.split() for line in (Path('/proc')/str(pid)/'maps').read_text().splitlines()))

def parse_trace(raw,tid):
    pattern=re.compile(r'-(\d+)\s+\[\d+\].*?\s(\d+)\.(\d+):\s+(?:'+h.GROUP+r':)?('+('|'.join(h.NAMES))+r'):')
    events=[];digits=set()
    for line in raw.splitlines():
        match=pattern.search(line)
        if not match:continue
        found,sec,frac,name=match.groups();assert int(found)==tid and len(frac)<=9
        digits.add(len(frac));events.append([int(sec)*1000000000+int(frac.ljust(9,'0')),name])
    cycles=[];incomplete=0;current=[]
    for stamp,name in events:
        if name=='native_enter':
            if current:incomplete+=1
            current=[[stamp,name]]
        elif current and name==h.NAMES[len(current)]:current.append([stamp,name])
        else:
            incomplete+=1;current=[];continue
        if len(current)==4:
            times=[p[0] for p in current];assert times==sorted(times)
            cycles.append({'native_start_ns':times[0],'native_return_ns':times[1],
                'restore_start_ns':times[2],'restore_return_ns':times[3],
                'native_interval_ms':(times[1]-times[0])/1e6,
                'native_return_to_restore_ms':(times[2]-times[1])/1e6,
                'restore_interval_ms':(times[3]-times[2])/1e6})
            current=[]
    return events,cycles,incomplete+bool(current),sorted(digits)

def run():
    run_wall_started=time.monotonic_ns();run_cpu_started=time.process_time_ns()
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    assert not (ROOT/'report.json').exists() and not h.INSTANCE.exists() and not h.owned_definitions()
    assert h.sha(LIBRARY)==LIB_SHA
    rawlib=LIBRARY.read_bytes()
    for offset,opcode in POINTS.values():assert int.from_bytes(rawlib[offset:offset+4],'little')==opcode
    meta=json.loads((GUI_ROOT/'session.json').read_text());g.verify(GUI_ROOT,meta)
    before=g.camera();assert before['pid']==588727 and not before['owner_fenced']
    assert before['feature_inference']['ready'] and before['worker_alive']
    full=g.get(8790,'/health');normal=full['dpu_schedule']['optional_diagnostics']['maximum_normal_trace']
    assert normal['task_code']==2,'No independently identified SFace TID'
    pid=before['pid'];tid=normal['calling_thread_native_id'];pborn=birth(pid);tborn=birth(pid,tid)
    validate(pid,tid,pborn,tborn);g.retained().single_owner(pid)
    before_global=h.global_state()
    targets={name:str(LIBRARY)+':0x'+format(pair[0],'x') for name,pair in POINTS.items()}
    h.save(ROOT/'ownership.json',{'source_sha256':h.sha(SOURCE),'group':h.GROUP,'boot':h.BOOT,'event_targets':targets})
    report={'complete':False,'passed':False,'scope':'EXISTING_SFACE_THREAD_PHASE_OBSERVATION',
        'production_source_changes':False,'additional_dpu_jobs_submitted':0,'source_sha256':h.sha(SOURCE),
        'library_sha256':LIB_SHA,'pid':pid,'tid':tid,'process_birth_ticks':pborn,'thread_birth_ticks':tborn,
        'points':POINTS,'before':before,'before_gui_pid':g.prop(g.GUI,'MainPID'),
        'predeclared_gate':{'whole_monitor_one_core_percent':2.,'minimum_complete_cycles':1,'seconds':60},
        'scope_limits':['probe overhead remains in original 30ms/5ms accounting',
            'common_pid filters recorded events; other threads using the same ELF can still incur trap overhead',
            'phase intervals include off-CPU and probe work, not hardware busy time',
            'no captured fault does not prove rare-tail root cause resolved']}
    h.save(ROOT/'report.json',report);armed=False
    try:
        h.command(['systemd-run','--unit='+h.GUARD,'--on-active=75s','--property=RuntimeMaxSec=30',
            '/usr/bin/python3','-B',str(SOURCE),'--cleanup'])
        assert g.prop(h.GUARD+'.timer','ActiveState')=='active';armed=True
        h.INSTANCE.mkdir();h.write(h.INSTANCE/'tracing_on','0');h.write(h.INSTANCE/'current_tracer','nop')
        h.write(h.INSTANCE/'buffer_size_kb','256');h.write(h.INSTANCE/'trace_clock','mono')
        for name,target in targets.items():
            h.write(h.TRACE/'uprobe_events','p:'+h.GROUP+'/'+name+' '+target,True)
            event=h.INSTANCE/'events'/h.GROUP/name
            h.write(event/'filter','common_pid == '+str(tid));h.write(event/'enable','1')
        validate(pid,tid,pborn,tborn)
        h.write(h.INSTANCE/'trace','');cpu_start=time.process_time_ns();start=time.monotonic_ns()
        h.write(h.INSTANCE/'tracing_on','1');until=time.monotonic()+60
        while time.monotonic()<until:
            time.sleep(min(1.,max(0.,until-time.monotonic())))
            assert birth(pid)==pborn and birth(pid,tid)==tborn
        h.write(h.INSTANCE/'tracing_on','0');end=time.monotonic_ns()
        events,cycles,incomplete,digits=parse_trace((h.INSTANCE/'trace').read_text(),tid)
        loss={}
        for path in (h.INSTANCE/'per_cpu').glob('cpu*/stats'):
            text=path.read_text();loss[path.parent.name]={key:int(re.search(r'^'+re.escape(key)+r':\s*(\d+)',text,re.M).group(1))
                for key in ('overrun','commit overrun','dropped events')}
        assert loss
        validate(pid,tid,pborn,tborn);after=g.camera();g.verify(GUI_ROOT,meta)
        cpu=time.process_time_ns()-cpu_start;duration=(time.monotonic_ns()-start)/1e9
        faults={name:after['optional'][name]['overruns']-before['optional'][name]['overruns'] for name in ('yunet','sface')}
        report.update(start_mono_ns=start,end_mono_ns=end,monitor_accounting_seconds=duration,
            monitor_cpu_one_core_percent=cpu/1e9/duration*100.,numeric_events=events,cycles=cycles,
            incomplete_phase_sequences=incomplete,displayed_fraction_digits=digits,lost_events=loss,
            after=after,after_gui_pid=g.prop(g.GUI,'MainPID'),fault_deltas=faults,
            observed_sface_completions=after['feature_inference']['completed']-before['feature_inference']['completed'])
        report['primary_overrun_delta']=after['primary_overruns']-before['primary_overruns']
        report['measurement_passed']=bool(cycles) and not any(n for row in loss.values() for n in row.values())
        report['business_fault_free_window']=(not any(faults.values()) and after['gaps']==before['gaps']
            and not report['primary_overrun_delta'] and not after['owner_fenced']
            and after['worker_faults']==before['worker_faults'] and after['diagnostic_failures']==before['diagnostic_failures'])
    except Exception as error:report['error']=type(error).__name__+': '+str(error)
    finally:
        report['cleanup']=h.cleanup();report['global_state_unchanged']=h.global_state()==before_global
        if armed and report['cleanup']['passed']:h.command(['systemctl','stop',h.GUARD+'.timer'])
        report['guard_timer_state']=g.prop(h.GUARD+'.timer','ActiveState')
        whole_seconds=(time.monotonic_ns()-run_wall_started)/1e9
        report['whole_monitor_cpu_one_core_percent']=(time.process_time_ns()-run_cpu_started)/1e9/whole_seconds*100.
        report['whole_monitor_accounting_seconds']=whole_seconds
        report['monitor_accounting_scope']='Controller CPU through setup, reads, aggregation and cleanup; excludes child systemctl CPU and final JSON serialization; target trap cost checked separately on fixture'
        report['cost_gate_passed']=report['whole_monitor_cpu_one_core_percent']<=2.
        report['complete']=True;report['root_cause_resolved']=False
        report['passed']=(report.get('measurement_passed',False) and report.get('cost_gate_passed',False)
            and report['cleanup']['passed'] and report['global_state_unchanged'] and report['guard_timer_state']=='inactive')
        h.save(ROOT/'report.json',report)
    return report

if __name__=='__main__':
    if sys.argv[1:]==['--cleanup']:print(json.dumps(h.cleanup()))
    elif sys.argv[1:]==['--run']:
        ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
        with (ROOT/'controller.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run()
    else:
        assert not sys.argv[1:] and not (ROOT/'report.json').exists()
        unit='aura-vart-phase-'+TOKEN
        h.command(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=90',
            '/usr/bin/python3','-B',str(SOURCE),'--run'])
        print(json.dumps({'started':True,'unit':unit,'report':str(ROOT/'report.json'),'source_sha256':h.sha(SOURCE)}))
