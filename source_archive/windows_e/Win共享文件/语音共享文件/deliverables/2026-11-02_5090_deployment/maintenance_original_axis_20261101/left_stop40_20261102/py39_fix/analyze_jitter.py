import collections
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
e=json.loads((HERE/'JITTER_NUMERIC_EVIDENCE.json').read_text(encoding='utf-8'))
reports=[]
stops={'SOURCE_UNCONFIRMED','SOURCE_EXPIRED','SOURCE_HORIZON_ENDED','SOURCE_LEASE_EXPIRED',
       'SOURCE_SUBMISSION_EXPIRED','CONTROL_TICK_LATE','VISUAL_CENTER_COMPLETE','MEASUREMENT_JUMP_PENDING'}
for report in e['reports']:
    result=report['result'];commands=result.get('command_trace',[]);events=result.get('events',[])
    segments=[];current=None
    for event in events:
        reason=event['reason'];stamp=event['mono_ms']
        if reason.startswith('FACE_CONFIRMED_'):
            if current:segments.append(dict(current,stop='NEXT_ARM_WITHOUT_RETAINED_STOP',end_ms=stamp))
            current=dict(start_ms=stamp,arm_reason=reason)
        elif reason in stops and current:
            segments.append(dict(current,stop=reason,end_ms=stamp));current=None
    if current:segments.append(dict(current,stop='LAST',end_ms=result['heartbeat_mono_ms']))
    summary={}
    for s in segments:
        cs=[c for c in commands if s['start_ms']<=c['mono_ms']<=s['end_ms']]
        endpoints=sorted(set(c['target_us'] for c in cs))
        side='PWM_INCREASE' if endpoints==[2500] else 'PWM_DECREASE' if endpoints==[500] else 'NO_RETAINED_COMMAND' if not endpoints else 'MIXED'
        gaps=[b['mono_ms']-a['mono_ms'] for a,b in zip(cs,cs[1:])]
        s.update(direction=side,endpoints=endpoints,retained_commands=len(cs),duration_ms=s['end_ms']-s['start_ms'],
            max_commit_gap_ms=max(gaps,default=None),min_lease_ms=min((c['lease_ms'] for c in cs),default=None),
            max_source_age_ms=max((c['source_age_ms'] for c in cs),default=None),
            max_detection_age_at_commit_ms=max((c['mono_ms']-c['face_anchor_mono_ms'] for c in cs if c.get('face_anchor_mono_ms') is not None),default=None))
        group=summary.setdefault(side,dict(segments=0,stop_counts=collections.Counter(),retained_commands=0))
        group['segments']+=1;group['stop_counts'][s['stop']]+=1;group['retained_commands']+=len(cs)
    interruptions=[]
    for previous,current in zip(segments,segments[1:]):
        if previous['stop']!='VISUAL_CENTER_COMPLETE' and previous['direction']==current['direction']:
            interruptions.append(dict(direction=current['direction'],stop=previous['stop'],stop_ms=previous['end_ms'],
                next_arm_ms=current['start_ms'],rearm_gap_ms=current['start_ms']-previous['end_ms']))
    obs=report.get('observation_trace') or []
    reports.append(dict(path=report['path'],elapsed_s=result.get('elapsed_s'),commands_total=result.get('commands_accepted'),
        commands_retained=len(commands),visual_center_completions=result.get('visual_center_completions'),
        segments_counter=result.get('segments'),segments=segments,direction_summary=summary,interruptions=interruptions,
        packet_summary=report.get('input_summary'),timing=report.get('telemetry'),reader_queue=report.get('reader_queue'),
        unconfirmed_tracking_reasons=dict(collections.Counter(o.get('tracking_reason') for o in obs if o.get('state')=='UNCONFIRMED')),
        max_source_age_ms=max((o['source_age_ms'] for o in obs if o.get('source_age_ms') is not None),default=None),
        max_detection_age_ms=max((o['detection_age_ms'] for o in obs if o.get('detection_age_ms') is not None),default=None)))
live=json.loads((HERE/'UI_STARTED.json').read_text(encoding='utf-8'))
last_report=live['snapshots'][-1]['report'];widths={}
for s in live['snapshots']:
    if s.get('report')!=last_report:continue
    for w in (s.get('report_result') or {}).get('hardware_width_trace') or []:
        widths[(w['mono_ms'],w['target_us'])]=w
groups={}
for side,endpoint in (('PWM_INCREASE',2500),('PWM_DECREASE',500)):
    ws=sorted((w for w in widths.values() if w['target_us']==endpoint),key=lambda w:w['mono_ms'])
    comparisons=[(a,b) for a,b in zip(ws,ws[1:]) if 0<b['mono_ms']-a['mono_ms']<=100]
    unexpected=[dict(a=a,b=b) for a,b in comparisons if (b['width_us']-a['width_us'])*(1 if endpoint==2500 else -1)<0]
    groups[side]=dict(samples=len(ws),adjacent_pairs_within_100ms=len(comparisons),opposite_steps=len(unexpected),
        unexpected_steps=unexpected,first=ws[0] if ws else None,last=ws[-1] if ws else None)
out=dict(schema='aura-axis-jitter-readonly-analysis-1',evidence_utc=e['utc'],runtime_faults=e['runtime_faults'],reports=reports,
    sampled_hardware_width_comparison=dict(report=last_report,groups=groups,
        scope='sparse register readbacks; no shaft/pin waveform measurement; no global monotonic claim across episodes'),
    field_direction_mapping='User-view right has not been equated with a PWM sign',
    conclusion='Repeated stop/rearm is evidenced. Mechanical load cannot be separated without field correlation. No PWM reversal within retained segment endpoints.')
(HERE/'JITTER_ANALYSIS.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='reports'},indent=2))
for r in reports:print(json.dumps({k:v for k,v in r.items() if k not in ('packet_summary','segments')},indent=2));print(json.dumps(r['segments'],indent=2))
