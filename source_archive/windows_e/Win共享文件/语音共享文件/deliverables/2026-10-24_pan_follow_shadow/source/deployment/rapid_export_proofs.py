"""Export only motion records and hash-bound release evidence, never images."""
import json
from pathlib import Path
r=Path('/home/root/aura-pan-current-20261024/463c9307');s=json.loads((r/'state.json').read_text());release=Path(s['gui_release'])/'manual-release'
print(json.dumps({'trial':json.loads((release/'observed-trial.json').read_text()),
 'human_observation':json.loads((release/'human-observation.json').read_text()),
 'release':json.loads((release/'release.json').read_text()),
 'summary':{'phase':s['phase'],'boot':s['boot'],'camera_pid':s['current_camera_pid'],'gui_pid':s['current_gui_pid'],
 'gui_dropin_sha256':s['gui_dropin_sha256'],'checkpoint_sha256':s['checkpoint_sha256'],'checkpoint_source_pid':s['stop_source_pid'],
 'final_flags':s['final_flags'],'final_lease_ms':s['final_lease_ms'],'direction_verified':s['direction_verified'],'automatic_following':False}},ensure_ascii=False))
