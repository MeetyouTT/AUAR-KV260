"""Numeric scheduler-event intervals, with explicit unknown coverage."""
import re


def matching_fault_report(report,lower_ns,upper_ns,task=1):
    """A newer health counter must not be attributed to a stale normal report."""
    if report.get('abi_version')!=2 or report.get('task')!=task:return False
    start=report.get('start_ns',0);native=report.get('native_return_ns',0)
    end=report.get('release_decision_ns',0);unlock=report.get('after_unlock_ns',0)
    if not (0<start<=native<=end<=unlock<=upper_ns and end>=lower_ns):return False
    return bool(report.get('hardcap') or report.get('guard') or
        (report.get('native_status',0)!=0 and (report.get('submitted') or report.get('completed'))))


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
