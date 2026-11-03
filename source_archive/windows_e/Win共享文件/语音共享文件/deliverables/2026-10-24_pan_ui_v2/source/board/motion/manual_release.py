"""Bind manual-only availability to the observed trial without claiming a waveform."""
import hashlib
import json
from pathlib import Path


def observed_bounds(release,config,root):
    if (release.get('status')!='OBSERVED_MANUAL_VSRV2' or release.get('scope')!='finite_manual_only'
            or release.get('external_waveform_verified') is not False
            or release.get('physical_servo_response_verified') is not True
            or release.get('dpu_coexistence_verified') is not True
            or release.get('automatic_following_enabled') is not False
            or release.get('boot_id')!=config.get('boot_id')
            or config.get('maximum_step_us')!=20 or config.get('maximum_duration_s')!=2):
        raise RuntimeError('Observed manual scope is incomplete; no MMIO')
    documents={}
    for name,key in [('observed-trial.json','trial_sha256'),('human-observation.json','observation_sha256')]:
        path=Path(root)/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=release.get(key):
            raise RuntimeError('Observed manual evidence changed; no MMIO')
        documents[name]=json.loads(path.read_text())
    trial=documents['observed-trial.json'];human=documents['human-observation.json']
    if (trial.get('status')!='20US_RETURN_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
            or trial.get('boot_id')!=config['boot_id']
            or human.get('status')!='HUMAN_OBSERVED_20US_RETURN_CONFIRMED'
            or human.get('boot_id')!=config['boot_id']
            or human.get('trial_sha256')!=release['trial_sha256']
            or human.get('movement_and_return_stop_observed') is not True
            or human.get('external_waveform_verified') is not False):
        raise RuntimeError('Human observation does not bind this trial and boot; no MMIO')
    result=trial['result'];sequence=result['commanded_sequence_us'];stopped=result['stopped']
    minimum=release.get('manual_minimum_us');maximum=release.get('manual_maximum_us')
    if (type(minimum) is not int or type(maximum) is not int or not 1400<=minimum<maximum<=1600
            or maximum-minimum!=20 or sequence!=[minimum,maximum,minimum]
            or config.get('manual_minimum_us')!=minimum or config.get('manual_maximum_us')!=maximum
            or result.get('excursion_us')!=20 or stopped['flags']!=0 or stopped['lease_left_ms']!=0
            or stopped['width_us']!=minimum or stopped['target_us']!=minimum
            or not trial['events'] or min(e['width_us'] for e in trial['events'])!=minimum
            or max(e['width_us'] for e in trial['events'])!=maximum):
        raise RuntimeError('Manual bounds exceed the observed stopped trial; no MMIO')
    return minimum,maximum
