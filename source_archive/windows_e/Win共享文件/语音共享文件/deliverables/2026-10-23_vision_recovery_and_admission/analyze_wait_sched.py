"""Join complete phase cycles with observed target scheduler intervals."""
import bisect,json,statistics,sys
from pathlib import Path

def overlap(lo,hi,intervals,ends):
    queue=sleep=unknown=0
    index=bisect.bisect_right(ends,lo)
    for start,end,state,wake in intervals[index:]:
        if start>=hi:break
        left=max(start,lo);right=min(end,hi)
        if right<=left:continue
        if state.startswith('R'):queue+=right-left
        elif wake is None:unknown+=right-left
        else:
            sleep+=max(0,min(right,wake)-left)
            queue+=max(0,right-max(left,wake))
    return {'runqueue_ms':queue/1e6,'sleep_ms':sleep/1e6,'unknown_off_cpu_ms':unknown/1e6,
        'unattributed_wall_ms':max(0.,(hi-lo-queue-sleep-unknown)/1e6)}

def analyze(report):
    intervals=report['off_cpu_intervals'];ends=[row[1] for row in intervals]
    phases={'total_critical':('start_ns','wait_cleanup_end_ns'),'native':('start_ns','native_return_ns'),'gil_reacquire':('restore_start_ns','restore_return_ns'),
        'wait_frontend':('wait_enter_ns','wait_native_enter_ns'),'wait_native':('wait_native_enter_ns','wait_native_return_ns'),
        'wait_cleanup':('wait_native_return_ns','wait_cleanup_end_ns')}
    joined=[]
    for row in report['cycles']:
        if row['tid']!=report['scheduler_target_tid']:continue
        value=dict(row,attribution={})
        for kind,(a,b) in phases.items():
            value['attribution'][kind]=dict(wall_ms=(row[b]-row[a])/1e6,**overlap(row[a],row[b],intervals,ends))
        joined.append(value)
    summary={}
    for kind in phases:
        values=[row['attribution'][kind] for row in joined]
        wall=sorted(row['wall_ms'] for row in values)
        queues=sorted(v['runqueue_ms'] for v in values)
        summary[kind]={'n':len(values),'wall_p50_ms':statistics.median(wall),'wall_p99_ms':wall[int(.99*len(wall))],
            'runqueue_p99_ms':queues[int(.99*len(queues))],'runqueue_max_ms':max(queues),
            'wall_max_ms':max(wall),'sum_wall_ms':sum(wall),
            **{key:sum(v[key] for v in values) for key in ('runqueue_ms','sleep_ms','unknown_off_cpu_ms','unattributed_wall_ms')}}
    faults=[]
    old_seq=max((e['event_sequence'] for e in report['before']['schedule']['optional_diagnostics']['fault_events']),default=0)
    for event in report['after']['schedule']['optional_diagnostics']['fault_events']:
        if event['event_sequence']<=old_seq:continue
        match=next((row for row in joined if event['execute_start_mono_ns']<=row['start_ns']<=event['execute_return_mono_ns']),None)
        entry={'event':event,'matched_cycle':match}
        if match:
            spans={'python_wait_start_to_wrapper_entry':(event['wait_start_mono_ns'],match['wait_enter_ns']),
                'cleanup_to_python_wait_end':(match['wait_cleanup_end_ns'],event['wait_end_mono_ns'])}
            entry['python_boundary_segments']={key:dict(wall_ms=(b-a)/1e6,**overlap(a,b,intervals,ends)) for key,(a,b) in spans.items() if b>=a}
        faults.append(entry)
    return {'scope':'Known scheduler overlap only; unattributed wall is not guaranteed CPU compute or hardware time',
        'complete_cycles':len(joined),'actual_seconds':report['actual_seconds'],'phases':summary,'faults':faults,
        'largest_wait_cycles':sorted(joined,key=lambda row:row['wait_frontend_ms']+row['wait_native_ms']+row['wait_cleanup_ms'],reverse=True)[:10],
        'largest_native_cycles':sorted(joined,key=lambda row:row['native_ms'],reverse=True)[:10],
        'largest_gil_cycles':sorted(joined,key=lambda row:row['restore_ms'],reverse=True)[:10]}

if __name__=='__main__':
    path=Path(sys.argv[1]);value=json.loads(path.read_text());report=value.get('report',value)
    result=analyze(report);out=path.with_name('wait-sched-analysis.json');out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not k.startswith('largest_')},indent=2))
