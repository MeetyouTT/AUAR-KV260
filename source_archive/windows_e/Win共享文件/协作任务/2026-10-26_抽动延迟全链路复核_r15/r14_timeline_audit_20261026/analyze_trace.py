"""Read one private numeric trial; reject stale GUI samples from the prior run."""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def analyze(path):
    raw=path.read_bytes();data=json.loads(raw);report=data['final_report'];result=report['result']
    start=result['heartbeat_mono_ms']-round(result['elapsed_s']*1000)
    events=report['result']['events']
    assert len(events)==2*result['segments']
    assert min(e['mono_ms'] for e in events)>=start
    commands={};stale=0;recent=[]
    for row in data['timeline']+[{'result':result}]:
        value=row.get('result') or {}
        if value.get('heartbeat_mono_ms',0)<start:
            stale+=1;continue
        recent.append(value)
        for command in value.get('command_trace',[]):
            if command['mono_ms']>=start:
                commands[(command['mono_ms'],command['source_frame_id'],command['target_us'])]=command
    command_rows=sorted(commands.values(),key=lambda c:c['mono_ms'])
    arms=[e['mono_ms'] for e in events if e['reason'].startswith('FACE_CONFIRMED_')]
    segments=[]
    for i,stamp in enumerate(arms):
        end=arms[i+1] if i+1<len(arms) else result['heartbeat_mono_ms']+1
        rows=[c for c in command_rows if stamp<=c['mono_ms']<end]
        stops=[e for e in events if stamp<=e['mono_ms']<end and not e['reason'].startswith('FACE_CONFIRMED_')]
        segments.append(dict(arm_mono_ms=stamp,reconstructed_commands=len(rows),
            first_command=rows[:1],last_command=rows[-1:],stop_events=stops))
    return dict(source_sha256=hashlib.sha256(raw).hexdigest(),trial_start_estimate_mono_ms=start,
        trial_end_mono_ms=result['heartbeat_mono_ms'],excluded_stale_or_empty_snapshots=stale,
        event_counts=dict(collections.Counter(e['reason'] for e in events)),
        accepted_total=result['commands_accepted'],reconstructed_accepted_commands=len(command_rows),
        accepted_not_retained_in_bounded_snapshots=result['commands_accepted']-len(command_rows),
        target_changes_total=result['motion_target_changes'],range_us=result['range_us'],
        telemetry=report['telemetry'],submission_timing=report['submission_timing'],reader_queue=report['reader_queue'],
        segments=segments,physical_motion_quality='user reports twitch and delayed response',
        last_guard_alarm_excess_ms=round((report['submission_timing']['last_delayed_submission']['observed_mono_s']
            +report['submission_timing']['last_delayed_submission']['accepted_readback']['lease_left_ms']/1000.
            -report['submission_timing']['last_delayed_submission']['original_deadline_mono_s'])*1000.,6),
        scope='numeric trial analysis; cached ACK false rejection is software-reproduced but this alarm lacks an exact readback timestamp')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);a=p.parse_args()
    print(json.dumps(analyze(a.trace),indent=2))
