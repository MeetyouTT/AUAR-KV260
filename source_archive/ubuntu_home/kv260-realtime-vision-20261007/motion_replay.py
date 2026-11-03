#!/usr/bin/env python3
"""Repeatable synthetic controller trace; never opens a camera or device."""
import argparse
import json
from pathlib import Path
from motion_service import MotionService
from vision_core import FaceTracks


def replay():
    boot, epoch = 'synthetic-boot', 'synthetic-camera'
    tracks = FaceTracks(epoch)
    service = MotionService(boot, epoch)
    service.resume_simulation(0.)
    events = []
    for fid in range(1, 24):
        t = 1+(fid-1)*.1
        # Gradual motion preserves association; then a real missing observation.
        center = 320+min(160, (fid-1)*16)
        faces = [[center-40,100,80,80]+[0.]*10+[.99]] if fid < 20 else []
        snapshot = tracks.update(faces, fid, t, 640, 480)
        result = service.observe(snapshot, 640, 480, t+.05, boot)
        events.append({'frame_id': fid, 'source_time': t, 'simulator': result})
    # A new image alone must not restore permission after loss.
    for fid in range(24, 28):
        t = 1+(fid-1)*.1
        snapshot = tracks.update([[440,100,80,80]+[0.]*10+[.99]], fid, t, 640, 480)
        result = service.observe(snapshot, 640, 480, t+.05, boot)
        events.append({'frame_id': fid, 'source_time': t, 'simulator': result})
    accepted = [e for e in events if e['simulator']['control'].get('receipt', {}).get('outcome') == 'ACCEPTED']
    assert accepted and not result['simulated_output_active']
    assert result['state'] == 'DISARMED'
    assert result['control']['reason'] == 'SIM_REQUIRES_EXPLICIT_RESUME'
    assert all(not e['simulator']['motion_command_emitted'] for e in events)
    summary = {'passed': True, 'input_kind': 'SYNTHETIC_NOT_CAMERA',
               'scope': 'SIMULATED', 'events': len(events), 'accepted_commands': len(accepted),
               'last_accepted_mdeg': result['controller_accepted_mdeg'],
               'loss_disarmed': True, 'reappearance_did_not_rearm': True,
               'calibration_status': 'SIMULATION_PLACEHOLDER', 'motion_command_emitted': False,
               'physical_actuation_authorized': False}
    return summary, events


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    summary, events = replay()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output/'trace.jsonl').write_text(''.join(json.dumps(e, allow_nan=False)+'\n' for e in events))
        (args.output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
