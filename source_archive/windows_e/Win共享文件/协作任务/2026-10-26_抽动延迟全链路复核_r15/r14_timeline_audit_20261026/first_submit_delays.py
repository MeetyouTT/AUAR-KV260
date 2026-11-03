"""First different-target submission only when a same-epoch ACK prefix survives.

command_trace.mono_ms is sampled BEFORE submit(), not an ACK timestamp or a
mechanical motion timestamp. These delays are lower bounds on accepted output.
"""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path


def analyze(path):
    raw=path.read_bytes();d=json.loads(raw);r=d['final_report'];end=r['result']
    start=end['heartbeat_mono_ms']-round(end['elapsed_s']*1000)
    arms=[x for x in end['events'] if x['reason'].startswith('FACE_CONFIRMED_')]
    snapshots=[]
    for sample in d['timeline']+[{'result':end}]:
        value=sample.get('result') or {}
        if value.get('heartbeat_mono_ms',0)>=start:snapshots.append(value)
    rows=[];all_commands={}
    for value in snapshots:
        for c in value.get('command_trace',[]):
            if c['mono_ms']>=start:all_commands[(c['mono_ms'],c['source_frame_id'],c['target_us'])]=c
    for i,arm in enumerate(arms):
        a=arm['mono_ms'];b=arms[i+1]['mono_ms'] if i+1<len(arms) else end['heartbeat_mono_ms']+1
        epoch=r['before']['epoch']+i+1
        witnesses=[]
        for value in snapshots:
            h=value['heartbeat_mono_ms'];rb=value['readback']
            if not a<=h<b or rb['epoch']!=epoch:continue
            prefix=[c for c in value['command_trace'] if a<=c['mono_ms']<=h]
            # Exact matching hardware ACK count proves the prefix begins at
            # the first accepted command, without guessing across missing rows.
            if len(prefix)>0 and len(prefix)==rb['ack_seq']:
                witnesses.append(dict(snapshot_mono_ms=h,epoch=epoch,ack_seq=rb['ack_seq'],
                    reference_us=rb['reference_us'],first=prefix[0]))
        row=dict(segment=i+1,epoch=epoch,arm_mono_ms=a,arm_reason=arm['reason'],
                 first_submission_proven=bool(witnesses))
        if witnesses:
            w=min(witnesses,key=lambda x:x['snapshot_mono_ms']);c=w['first']
            assert c['delta_us']!=0 and c['target_us']!=w['reference_us']
            row.update(witness=w,arm_to_submit_lower_bound_ms=c['mono_ms']-a,
                       source_age_at_submit_ms=c['source_age_ms'])
        else:
            retained=[c for c in all_commands.values() if a<=c['mono_ms']<b]
            row.update(retained_commands_in_segment=len(retained),
                exclusion='no same-epoch snapshot proving complete first-ACK prefix')
        rows.append(row)
    delays=[x['arm_to_submit_lower_bound_ms'] for x in rows if x['first_submission_proven']]
    commands=list(all_commands.values());speeds=[abs(c['velocity_us_s']) for c in commands]
    changed=[abs(c['velocity_us_s']) for c in commands if c['delta_us']]
    j=r['control_parameters']['maximum_jerk_us_s3'];a=r['control_parameters']['maximum_acceleration_us_s2']
    t=a/j;position=j*t**3/6.;velocity=j*t*t/2.
    kinematic=t+(-velocity+math.sqrt(velocity*velocity+2*a*(.5-position)))/a
    first_observation=r['observation_trace'][0]
    first=rows[0]['witness']['first'] if rows[0]['first_submission_proven'] else None
    return dict(trace_sha256=hashlib.sha256(raw).hexdigest(),segments_total=len(arms),proven_first_submissions=len(delays),
        arm_to_submit_lower_bound_ms=dict(minimum=min(delays),median=statistics.median(delays),maximum=max(delays)),
        first_run_observation_to_submit_ms=first['mono_ms']-first_observation['received_mono_ms'] if first else None,
        first_run_capture_to_submit_ms=first['mono_ms']-(first_observation['received_mono_ms']-first_observation['source_age_ms']) if first else None,
        reconstructed_command_coverage=dict(retained=len(commands),accepted_total=end['commands_accepted']),
        reconstructed_absolute_command_velocity_us_s=dict(minimum=min(speeds),median=statistics.median(speeds),maximum=max(speeds)),
        changed_target_absolute_velocity_us_s=dict(minimum=min(changed),median=statistics.median(changed),maximum=max(changed)),
        rest_to_half_us_kinematic_lower_bound_ms=round(kinematic*1000.,6),
        kinematic_assumptions='rest position with zero velocity/acceleration; jerk800 acceleration100; 0.5us integer-rounding threshold; ignores capture/confirmation/tick/native/PWM delay and servo deadband',
        segments=rows,
        scope='pre-submit timestamp only, not ACK completion, external PWM or physical onset; unproven segment starts excluded')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);args=p.parse_args()
    print(json.dumps(analyze(args.trace),indent=2))
