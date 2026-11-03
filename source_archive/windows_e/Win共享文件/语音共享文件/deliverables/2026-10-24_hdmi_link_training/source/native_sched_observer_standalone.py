"""Numeric scheduler-event intervals, with explicit unknown coverage."""
import re


def parse_scheduler_events(text):
    header=re.compile(r'-(\d+)\s+\[(\d+)\]\s+\S+\s+(\d+)\.(\d+):\s+(sched_switch|sched_wakeup):\s+(.*)$')
    result=[]
    for line in text.splitlines():
        match=header.search(line)
        if not match:continue
        actor,cpu,seconds,fraction,kind,body=match.groups()
        row=dict(mono_ns=int(seconds)*10**9+int(fraction.ljust(9,'0')[:9]),cpu=int(cpu),kind=kind)
        if kind=='sched_switch':
            value=re.search(r'prev_pid=(\d+).*prev_state=(\S+).*next_pid=(\d+)',body)
            if not value:continue
            row.update(prev_tid=int(value[1]),prev_state=value[2],next_tid=int(value[3]))
        else:
            value=re.search(r'(?:^|\s)pid=(\d+)(?:\s|$)',body)
            if not value:continue
            row['tid']=int(value[1])
        result.append(row)
    return sorted(result,key=lambda row:row['mono_ns'])


def scheduler_window(events,tid,start_ns,end_ns,pauses=()):
    if type(tid) is not int or tid<=0 or end_ns<=start_ns:
        raise ValueError('Positive TID and increasing native interval required')
    durations=dict(RUNNING=0,RUNNABLE=0,BLOCKED=0,UNKNOWN=0)
    intervals=[];state='UNKNOWN';point=start_ns
    def advance(current,event):
        if event['kind']=='sched_switch':
            if event['next_tid']==tid:return 'RUNNING'
            if event['prev_tid']==tid:
                return 'RUNNABLE' if event['prev_state'].startswith('R') else 'BLOCKED'
        elif event['tid']==tid and current!='RUNNING':return 'RUNNABLE'
        return current
    for event in events:
        timestamp=event['mono_ns']
        if timestamp<=start_ns:
            state=advance(state,event);continue
        if timestamp>=end_ns:break
        next_state=advance(state,event)
        if next_state!=state:
            durations[state]+=timestamp-point
            intervals.append(dict(start_ns=point,end_ns=timestamp,state=state))
            point=timestamp;state=next_state
    durations[state]+=end_ns-point
    intervals.append(dict(start_ns=point,end_ns=end_ns,state=state))
    overlaps=any(begin<end_ns and finish>start_ns for begin,finish in pauses)
    known=durations['UNKNOWN']==0 and not overlaps
    classification='INCOMPLETE_TRACE'
    wall=end_ns-start_ns
    if known:
        if durations['RUNNABLE']>=wall*.7:classification='RUNQUEUE_DOMINATED'
        elif durations['BLOCKED']>=wall*.7:classification='BLOCKING_DOMINATED'
        else:classification='MIXED_OR_RUNNING'
    assert sum(durations.values())==wall
    return dict(wall_ms=wall/1e6,state_ms={key:value/1e6 for key,value in durations.items()},
        classification=classification,coverage_complete=known,pause_overlaps=overlaps,intervals=intervals,
        running_scope='scheduled-on-CPU upper bound; hard IRQ/soft IRQ time is not subtracted',
        blocked_scope='sleeping/off-CPU; cannot distinguish driver locks from other waits')


"""One-hour bounded target-thread scheduler trace; no uprobe stays enabled."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

BOOT='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
PID=1291
TID=1335
SOURCE=Path(__file__).resolve()
TOKEN=hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT=Path('/home/root/aura-display-sequence-20261024/scheduler-observer')/TOKEN
TRACE=Path('/sys/kernel/tracing/instances')/('aura_sched_'+TOKEN)
STOP=False


def atomic(path,value):
    path=Path(path);temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,indent=2)+'\n');os.replace(temp,path)


def command(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=5)
    if p.returncode:raise RuntimeError('Observer service command failed')
    return p.stdout


def cleanup():
    if not (ROOT/'ownership.json').exists():return
    meta=json.loads((ROOT/'ownership.json').read_text())
    assert meta['boot']==BOOT and meta['trace']==str(TRACE)
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    if TRACE.exists():
        (TRACE/'tracing_on').write_text('0')
        (TRACE/'events/enable').write_text('0')
        TRACE.rmdir()


def observe():
    global STOP
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert not TRACE.exists()
    task=Path('/proc')/str(PID)/'task'/str(TID)/'stat'
    birth=int(task.read_text().rsplit(') ',1)[1].split()[19])
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def health():
        assert int(task.read_text().rsplit(') ',1)[1].split()[19])==birth
        with opener.open('http://127.0.0.1:8790/health',timeout=3) as stream:h=json.load(stream)
        assert h['pid']==PID and h['dpu_schedule'].get('native_critical') is True
        s=h['dpu_schedule'];job=s['optional']['yunet']
        return dict(mono_ns=time.monotonic_ns(),pid=h['pid'],frames=h['detected_frames'],
            primary_overruns=s['primary_period_overruns'],fenced=s['owner_fenced'],
            worker_alive=h['identity']['face_targets']['worker_alive'],
            optional={kind:dict(overruns=j['overruns'],native_completed=j['native_completed'],
                phase=j['recovery']['phase'],faults=j['recovery']['faults'],recoveries=j['recovery']['recoveries'])
                for kind,j in s['optional'].items()},
            yunet_report=job.get('last_native_report') or {})
    def stopping(*args):
        global STOP
        STOP=True
    signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
    before=previous=health();assert not before['fenced'] and before['worker_alive']
    report=dict(scope='INSTRUMENTED_ONE_HOUR_YUNET_SCHEDULER_TRACE_NO_MODEL_OR_POLICY_CHANGE',
        boot=BOOT,pid=PID,target_tid=TID,target_birth_ticks=birth,phase='STARTING',
        duration_limit_seconds=3600,health_query_interval_seconds=2,model_instances_created=0,
        uprobes_left_enabled=0,display_control_commands=0,native_fault_dumps=0,
        pause_intervals=[],before=before,trace_validation_passed=False,
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),captures=[],
        limitations=['Tracing is instrumentation; it may affect scheduling',
            'RUNNING includes hard/soft IRQ time; BLOCKED does not identify a specific lock',
            'Only the positively identified YuNet worker is traced, not SFace',
            'Health last-report sampling is not a lossless native fault ring'])
    created=False;began=time.monotonic();queries=0;failures=0;reason='DURATION_COMPLETE'
    def capture(label,state):
        pause_start=time.monotonic_ns()
        (TRACE/'tracing_on').write_text('0')
        raw=(TRACE/'trace').read_text()
        stats={p.parent.name:p.read_text() for p in (TRACE/'per_cpu').glob('cpu*/stats')}
        (TRACE/'tracing_on').write_text('1')
        pause_end=time.monotonic_ns();report['pause_intervals'].append([pause_start,pause_end])
        number=len(report['captures']);(ROOT/('trace-'+str(number)+'.private.txt')).write_text(raw)
        events=parse_scheduler_events(raw);native=state['yunet_report']
        item=dict(label=label,observed_mono_ns=state['mono_ns'],state=state,
            scheduler_event_count=len(events),buffer_stats=stats,native_report_available=False)
        start=native.get('start_ns',0);end=native.get('release_decision_ns',0)
        if start and end>start:
            item['native_report_available']=True
            item['lease']=scheduler_window(events,TID,start,end,report['pause_intervals'])
            native_end=native.get('native_return_ns',0)
            if start<native_end<end:
                item['native_body']=scheduler_window(events,TID,start,native_end,report['pause_intervals'])
                item['release_bookkeeping']=scheduler_window(events,TID,native_end,end,report['pause_intervals'])
            item['numeric_window_events']=[event for event in events if start-50_000_000<=event['mono_ns']<=end+50_000_000]
            # Per-CPU overwrite is harmless only if the retained events on
            # that CPU extend earlier than this particular native interval.
            clipped=[]
            for cpu,text in stats.items():
                match=re.search(r'^overrun:\s*(\d+)',text,re.M)
                rows=[event for event in events if event['cpu']==int(cpu[3:])]
                if match and int(match[1]) and rows and rows[0]['mono_ns']>start:
                    clipped.append(cpu)
            item['clipped_cpus']=clipped
            if clipped:
                item['lease'].update(coverage_complete=False,classification='INCOMPLETE_TRACE')
        atomic(ROOT/('capture-'+str(number)+'.json'),item)
        report['captures'].append(item)
        return bool(item.get('lease',{}).get('coverage_complete'))
    try:
        TRACE.mkdir();created=True
        atomic(ROOT/'ownership.json',dict(boot=BOOT,trace=str(TRACE),source_sha256=report['source_sha256']))
        (TRACE/'tracing_on').write_text('0');(TRACE/'buffer_size_kb').write_text('256')
        (TRACE/'trace_clock').write_text('mono')
        filters=dict(sched_switch='prev_pid == '+str(TID)+' || next_pid == '+str(TID),
                     sched_wakeup='pid == '+str(TID))
        for name,text in filters.items():
            event=TRACE/'events/sched'/name
            (event/'filter').write_text(text);(event/'enable').write_text('1')
        report['filters']=filters
        (TRACE/'tracing_on').write_text('1')
        report['phase']='OBSERVING';atomic(ROOT/'progress.json',report)
        while not STOP and time.monotonic()-began<3600:
            time.sleep(2)
            try:
                state=health();queries+=1;failures=0
                assert state['frames']>=previous['frames']
                assert state['optional']['yunet']['overruns']>=previous['optional']['yunet']['overruns']
            except Exception as exc:
                failures+=1;report['last_query_failure_type']=type(exc).__name__
                if failures>=5:reason='QUERY_OR_COUNTER_FAILURE';break
                continue
            report['after']=state;report['elapsed_seconds']=time.monotonic()-began
            old=previous['optional']['yunet'];new=state['optional']['yunet']
            if new['faults']>old['faults'] or new['overruns']>old['overruns']:
                capture('NEW_YUNET_FAULT',state);report['native_fault_dumps']+=1
            elif (not report['trace_validation_passed'] and report['elapsed_seconds']>=15
                  and state['yunet_report'].get('start_ns') and len(report['captures'])<4):
                report['trace_validation_passed']=capture('NORMAL_WINDOW_TRACE_VALIDATION',state)
            previous=state
            if queries%15==0:atomic(ROOT/'progress.json',report)
            if state['fenced'] or not state['worker_alive']:
                reason='BUSINESS_UNAVAILABLE';break
            if report['native_fault_dumps']>=2:
                reason='TWO_NATIVE_FAULTS_RETAINED';break
    except BaseException as exc:
        reason='OBSERVER_ERROR';report['failure_type']=type(exc).__name__
        report['failure']=str(exc)
    finally:
        if created:cleanup()
        report.update(phase='COMPLETE',finish_reason='STOP_REQUESTED' if STOP else reason,
            cleanup_passed=not TRACE.exists(),observer_cpu_seconds=time.process_time(),
            elapsed_seconds=time.monotonic()-began,health_queries=queries)
        try:command(['systemctl','stop','aura-sched-cleanup-'+TOKEN+'.timer'])
        except Exception:pass
        atomic(ROOT/'result.json',report);atomic(ROOT/'progress.json',report)


def main():
    import sys
    if sys.argv[1:]==['--cleanup']:cleanup();return
    if sys.argv[1:]==['--observe']:observe();return
    assert not sys.argv[1:]
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    command(['systemd-run','--quiet','--unit=aura-sched-cleanup-'+TOKEN,'--on-active=3800s',
        '/usr/bin/python3','-B',str(SOURCE),'--cleanup'])
    unit='aura-yunet-sched-'+TOKEN
    command(['systemd-run','--quiet','--no-block','--unit='+unit,'--property=Type=oneshot',
        '--property=RuntimeMaxSec=3700','--property=TimeoutStopSec=10',
        '/usr/bin/python3','-B',str(SOURCE),'--observe'])
    until=time.monotonic()+6
    while time.monotonic()<until and not (ROOT/'progress.json').exists():time.sleep(.1)
    assert (ROOT/'progress.json').exists(),'Scheduler observer did not become ready'
    print(json.dumps(dict(unit=unit,root=str(ROOT),phase=json.loads((ROOT/'progress.json').read_text())['phase'],
        target_tid=TID,models_created=0,uprobe_probes_left=0)))


if __name__=='__main__':main()
