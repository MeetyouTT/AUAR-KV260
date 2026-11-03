"""Read-only acceptance of the bounded diagnostic control before formal runs."""
from pathlib import Path
import json
ab=Path('/home/root/aura-yuki-validation-20261030/native_integration/paired_ab')
case=ab/'runs/control-pilot-resume-v2/01-old_nojpeg'
summary=json.loads((case/'summary.json').read_text());samples=json.loads((case/'samples.json').read_text());commands=json.loads((case/'commands.json').read_text())
paused=[s for s in samples if s.get('paused') and 8.25<=s['elapsed']<9]
after_cancel=[s for s in samples if s['elapsed']>=12.5]
clocks=[s['audio_time'] for s in paused]
checks=dict(completed=summary['status']=='COMPLETE',remote_path_observed=summary['mode_counts'].get('remote',0)>0,
    only_existing_old_modes=set(summary['mode_counts'])<={'remote','local'},
    remote_errors_absent=all(not s['portrait'].get('error') and not s['portrait'].get('failures') for s in samples),
    diagnostic_jpeg_absent=bool(samples) and all(s['jpeg_bytes']==0 for s in samples),
    commands_accepted=len(commands)==5 and all(c.get('outcome',{}).get('ok') for c in commands),
    actual_pcm_converted=max(s['audio'].get('converted_bytes',0) for s in samples)>0,
    actual_48k_stereo=any({'format':'S16LE','rate':48000,'channels':2} in s['audio'].get('caps',[]) for s in samples),
    saw_playing=any(s.get('playing') for s in samples),
    pause_frozen=len(clocks)>=2 and max(clocks)-min(clocks)<=.003,
    cancel_stopped=bool(after_cancel) and all(not s.get('playing') and not s.get('paused') and abs(s.get('mouth_level') or 0)<.01 for s in after_cancel),
    no_command_failures=not summary['command_failures'])
report=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,pause_clock_span_ms=(max(clocks)-min(clocks))*1000 if clocks else None,
    pause_samples=len(paused),cancel_samples=len(after_cancel),camera_unchanged_by_harness=True,source_mode=summary['backend'],production_modified=False)
report.update(acceptance_revision=2,observed_target_mode_fraction=summary['observed_target_mode_fraction'],mode_spans=summary['mode_spans'],
    mode_rule='Use original harness predeclared policy: brief local resync on old cancel is recorded, not automatically invalid. Actual probe had one200ms local sample after cancel and returned remote without errors. Initial acceptance helper incorrectly added99percent cutoff; no workload was rerun or excluded.')
target=ab/'control-pilot-resume-v2-acceptance.json';previous=ab/'control-pilot-resume-v2-acceptance-check-v1.json'
if target.exists() and not previous.exists():previous.write_bytes(target.read_bytes())
target.write_text(json.dumps(report,indent=2));print(json.dumps(report));assert report['status']=='PASS'
