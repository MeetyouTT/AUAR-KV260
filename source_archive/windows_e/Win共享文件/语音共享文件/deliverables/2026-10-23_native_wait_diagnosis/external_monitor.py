"""Read-only external scheduler sampling; never enters a production lease."""
import bisect,json,math,os,resource,statistics,time,urllib.request
from pathlib import Path

DURATION=60.;HZ=100;EXPECTED_PID=499773
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
    with op.open('http://127.0.0.1:8790/health',timeout=4) as response:h=json.load(response)
    s=h['dpu_schedule'];d=s['optional_diagnostics'];f=h['identity']['face_targets']
    return {'pid':h['pid'],'yolo_hz':h['detection_hz'],'optional':s['optional'],
        'owner_fenced':s['owner_fenced'],'gaps':f['freshness_metrics']['counters']['observed_gap_intervals'],
        'maximum_normal_trace':d['maximum_normal_trace'],'fault_events':d['fault_events']}
def start_ticks(path):return int(path.read_text().rsplit(') ',1)[1].split()[19])
def summary(values):
    s=sorted(values);n=len(s)
    if not n:return {'count':0}
    return {'count':n,'mean':statistics.mean(s),'p50':s[math.ceil(n*.5)-1],
        'p95':s[math.ceil(n*.95)-1],'p99':s[math.ceil(n*.99)-1],'max':s[-1]}
def parse(raw):
    if len(raw)>256:raise ValueError('Oversized target schedstat')
    fields=raw.split()
    if len(fields)!=3 or not all(f.isdigit() for f in fields):raise ValueError('Invalid target schedstat')
    values=tuple(int(f) for f in fields)
    if any(v>=2**64 for v in values):raise ValueError('Target counter overflow')
    return values
def align_trace(trace,targets,window_start,window_end):
    tid=trace.get('calling_thread_native_id');entry=next((v for v in targets.values() if v['tid']==tid),None)
    a,b=trace.get('execute_start_mono_ns',0),trace.get('execute_return_mono_ns',0)
    out={'event_sequence':trace.get('event_sequence'),'task_code':trace.get('task_code'),'tid':tid,
         'execute_marks_start_ns':a,'execute_marks_end_ns':b,'covered':False}
    if not entry or not a or not b or a<window_start or b>window_end:return out
    rows=entry['samples'];ends=[r[1] for r in rows];begins=[r[0] for r in rows]
    left=bisect.bisect_right(ends,a)-1;right=bisect.bisect_left(begins,b)
    if left<0 or right>=len(rows):return out
    x,y=rows[left],rows[right]
    out.update(covered=True,expanded_bracket_start_ns=x[0],expanded_bracket_end_ns=y[1],
        expanded_runqueue_counter_delta_ns=y[3]-x[3],expanded_runtime_counter_delta_ns=y[2]-x[2],
        before_edge_uncertainty_ns=a-x[0],after_edge_uncertainty_ns=y[1]-b,
        scope='expanded external counter interval; deferred kernel accounting and non-atomic reads; not exact VART/GIL attribution')
    return out

result={'complete':False,'passed':False,'scope':'EXTERNAL_TARGET_THREAD_COUNTERS_NO_PRODUCTION_PATCH_OR_DPU_JOB',
    'production_changes':False,'dpu_jobs_submitted':0,'requested_hz':HZ,'requested_seconds':DURATION,
    'cpu_gate_one_core_percent':2.0,'minimum_effective_hz':90.0,
    'target_runtime_scope':'schedstat sum_exec_runtime can lag; not CLOCK_THREAD_CPUTIME_ID',
    'observer_scope':'os.pread may release this monitor GIL; it does not run inside the camera interpreter or DPU lease',
    'timing_scope':'each ordered read is bracketed, not atomic; large queue steps can include deferred accounting'}
targets={};before=health();assert before['pid']==EXPECTED_PID
result['before']=before;process_path=Path('/proc')/str(EXPECTED_PID);process_birth=start_ticks(process_path/'stat')
traces=before['fault_events']+[before['maximum_normal_trace'] or {}]
for trace in traces:
    kind=trace.get('task_code');tid=trace.get('calling_thread_native_id')
    if kind not in (1,2) or type(tid) is not int or tid<=0:continue
    task=process_path/'task'/str(tid);birth=start_ticks(task/'stat')
    path=task/'schedstat';fd=os.open(str(path),os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    info=os.fstat(fd)
    if start_ticks(task/'stat')!=birth or path.stat().st_ino!=info.st_ino:
        os.close(fd);raise RuntimeError('Target native thread changed during open')
    if kind in targets:os.close(targets[kind]['fd'])
    targets[kind]={'tid':tid,'fd':fd,'birth_ticks':birth,'inode':info.st_ino,'device':info.st_dev,
        'nice':os.getpriority(os.PRIO_PROCESS,tid),'policy':os.sched_getscheduler(tid),
        'affinity':sorted(os.sched_getaffinity(tid)),'samples':[]}
assert set(targets)=={1,2},'Both actual optional calling thread IDs are required'
result['monitor_nice']=os.getpriority(os.PRIO_PROCESS,0)
start=time.monotonic_ns();cpu_start=time.process_time_ns();next_tick=start;period=int(1e9/HZ);skipped=0
try:
    while time.monotonic_ns()-start<int(DURATION*1e9):
        now=time.monotonic_ns()
        if now<next_tick:time.sleep((next_tick-now)/1e9)
        if time.monotonic_ns()-start>=int(DURATION*1e9):break
        for kind,entry in targets.items():
            a=time.monotonic_ns();values=parse(os.pread(entry['fd'],257,0));b=time.monotonic_ns()
            row=[a,b,*values]
            if entry['samples'] and any(values[i]<entry['samples'][-1][i+2] for i in range(3)):
                raise RuntimeError('Target counters decreased; no attribution across changed identities')
            entry['samples'].append(row)
            assert len(entry['samples'])<=int(DURATION*HZ)+8
        next_tick+=period;now=time.monotonic_ns()
        if now>next_tick:
            missed=(now-next_tick)//period+1;skipped+=missed;next_tick+=missed*period
    end=time.monotonic_ns();loop_cpu=time.process_time_ns()-cpu_start
    assert start_ticks(process_path/'stat')==process_birth
    for entry in targets.values():
        assert start_ticks(process_path/'task'/str(entry['tid'])/'stat')==entry['birth_ticks']
    after=health();assert after['pid']==EXPECTED_PID;result['after']=after
    result.update(window_start_mono_ns=start,window_end_mono_ns=end,actual_seconds=(end-start)/1e9,
        skipped_cadence_ticks=skipped,loop_cpu_one_core_percent=100*loop_cpu/(end-start),targets={})
    for kind,entry in targets.items():
        rows=entry['samples'];first,last=rows[0],rows[-1]
        steps=[rows[i][3]-rows[i-1][3] for i in range(1,len(rows))]
        result['targets'][str(kind)]={k:v for k,v in entry.items() if k not in ('fd','samples')}
        result['targets'][str(kind)].update(samples=len(rows),effective_hz=(len(rows)-1)/((last[0]-first[0])/1e9),
            read_duration_ns=summary([r[1]-r[0] for r in rows]),late_reads_over_2ms=sum(r[1]-r[0]>2_000_000 for r in rows),
            total_runqueue_counter_delta_ns=last[3]-first[3],total_runtime_counter_delta_ns=last[2]-first[2],
            runqueue_step_ns=summary(steps),nonzero_schedstat=any(last[2:]))
    events={}
    for trace in before['fault_events']+after['fault_events']+[before['maximum_normal_trace'] or {},after['maximum_normal_trace'] or {}]:
        if trace.get('event_sequence'):events[trace['event_sequence']]=trace
    result['event_brackets']=[align_trace(t,targets,start,end) for t in events.values()]
    result['covered_trace_events']=sum(t['covered'] for t in result['event_brackets'])
    raw={'scope':'numeric external scheduler snapshots only','pid':EXPECTED_PID,'birth_ticks':process_birth,
         'sample_fields':['before_mono_ns','after_mono_ns','runtime_ns','runqueue_ns','timeslices'],
         'targets':{str(k):{'tid':v['tid'],'samples':v['samples']} for k,v in targets.items()}}
    (ROOT/'numeric-samples.json').write_text(json.dumps(raw,separators=(',',':')))
    usage=resource.getrusage(resource.RUSAGE_SELF)
    result['whole_process_cpu_seconds_to_serialization']=usage.ru_utime+usage.ru_stime
    result['whole_process_cpu_one_core_percent']=100*(usage.ru_utime+usage.ru_stime)/((time.monotonic_ns()-start)/1e9)
    result['passed']=(result['whole_process_cpu_one_core_percent']<=2.0 and
        all(t['effective_hz']>=90.0 and t['nonzero_schedstat'] for t in result['targets'].values()))
except Exception as error:
    result['error']=type(error).__name__+': '+str(error)
finally:
    for entry in targets.values():os.close(entry['fd'])
    result['complete']=True
    temp=ROOT/'report.tmp';temp.write_text(json.dumps(result,indent=2)+'\n');os.replace(temp,ROOT/'report.json')
print(json.dumps(result))
