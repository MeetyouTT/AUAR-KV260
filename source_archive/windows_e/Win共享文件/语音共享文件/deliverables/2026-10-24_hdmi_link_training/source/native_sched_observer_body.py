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
PREDECESSOR=Path('/home/root/aura-display-sequence-20261024/scheduler-observer/84fb117db99251b9')


def predecessor():
    value=json.loads((PREDECESSOR/'result.json').read_text())
    assert value['boot']==BOOT and value['pid']==PID and value['target_tid']==TID
    assert value['phase']=='COMPLETE' and value['cleanup_passed']
    assert value['source_sha256'].startswith('84fb117db99251b9')
    return value,value['before']['mono_ns']+3600_000_000_000


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
    prior,deadline_ns=predecessor();assert prior['target_birth_ticks']==birth
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def health():
        assert int(task.read_text().rsplit(') ',1)[1].split()[19])==birth
        query_start_ns=time.monotonic_ns()
        with opener.open('http://127.0.0.1:8790/health',timeout=3) as stream:h=json.load(stream)
        assert h['pid']==PID and h['dpu_schedule'].get('native_critical') is True
        s=h['dpu_schedule'];job=s['optional']['yunet']
        return dict(query_start_ns=query_start_ns,mono_ns=time.monotonic_ns(),pid=h['pid'],frames=h['detected_frames'],
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
        duration_limit_seconds=max(0,(deadline_ns-time.monotonic_ns())/1e9),overall_deadline_mono_ns=deadline_ns,
        predecessor_root=str(PREDECESSOR),predecessor_elapsed_seconds=prior['elapsed_seconds'],
        handoff_gap_ns=before['query_start_ns']-prior.get('after',prior['before'])['mono_ns'],
        faults_observed_in_handoff_gap=before['optional']['yunet']['faults']-prior.get('after',prior['before'])['optional']['yunet']['faults'],
        health_query_interval_seconds=2,model_instances_created=0,
        uprobes_left_enabled=0,display_control_commands=0,native_fault_dumps=0,
        pause_intervals=[],before=before,trace_validation_passed=False,
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),captures=[],
        limitations=['Tracing is instrumentation; it may affect scheduling',
            'RUNNING includes hard/soft IRQ time; BLOCKED does not identify a specific lock',
            'Only the positively identified YuNet worker is traced, not SFace',
            'Health last-report sampling is not a lossless native fault ring'])
    created=False;began=time.monotonic();queries=0;failures=0;reason='DURATION_COMPLETE'
    def capture(label,state,lower_ns=None):
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
        exact=(label!='NEW_YUNET_FAULT' or
            lower_ns is not None and matching_fault_report(native,lower_ns,state['mono_ns']))
        item['exact_fault_report_available']=exact if label=='NEW_YUNET_FAULT' else None
        if label=='NEW_YUNET_FAULT':item['counter_change_observation_interval_ns']=[lower_ns,state['mono_ns']]
        start=native.get('start_ns',0);end=native.get('release_decision_ns',0)
        if exact and start and end>start:
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
        elif label=='NEW_YUNET_FAULT':
            item['failure_reason']='NO_MATCHING_NEW_FAULT_REPORT_DO_NOT_ATTRIBUTE_OLD_NORMAL_TIMING'
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
        while not STOP and time.monotonic_ns()<deadline_ns:
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
                # Counter snapshots can precede Python note_result publication.
                # Keep tracing and retry briefly, never label an old normal
                # report as the new fault just because its counter changed.
                lower_ns=previous['query_start_ns'];until=time.monotonic()+.5
                while not matching_fault_report(state['yunet_report'],lower_ns,state['mono_ns']) and time.monotonic()<until:
                    time.sleep(.05)
                    try:state=health();queries+=1
                    except Exception as exc:
                        report['fault_report_retry_error_type']=type(exc).__name__;break
                capture('NEW_YUNET_FAULT',state,lower_ns);report['native_fault_dumps']+=1
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
    prior,deadline_ns=predecessor()
    remaining=max(0,int((deadline_ns-time.monotonic_ns())/1e9))
    assert remaining>=30,'Original one-hour observation deadline has passed'
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    command(['systemd-run','--quiet','--unit=aura-sched-cleanup-'+TOKEN,'--on-active='+str(remaining+200)+'s',
        '/usr/bin/python3','-B',str(SOURCE),'--cleanup'])
    unit='aura-yunet-sched-'+TOKEN
    command(['systemd-run','--quiet','--no-block','--unit='+unit,'--property=Type=oneshot',
        '--property=RuntimeMaxSec='+str(remaining+100),'--property=TimeoutStopSec=10',
        '/usr/bin/python3','-B',str(SOURCE),'--observe'])
    until=time.monotonic()+6
    while time.monotonic()<until and not (ROOT/'progress.json').exists():time.sleep(.1)
    assert (ROOT/'progress.json').exists(),'Scheduler observer did not become ready'
    print(json.dumps(dict(unit=unit,root=str(ROOT),phase=json.loads((ROOT/'progress.json').read_text())['phase'],
        target_tid=TID,models_created=0,uprobe_probes_left=0)))


if __name__=='__main__':main()
