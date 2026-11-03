import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parents[1]/'2026-10-29_audio_animation_polish'))
from board_guard import capture,same
before=json.loads((H/'board_preflight.json').read_text());after=capture()
same(before,after)
(H/'board_postflight.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
print(json.dumps(dict(read_only=True,safe=after['safe'],pins=len(after['pins']),mismatches=after['mismatches'],
 runtime=after['actual_runtime'],ui_pid=after['ui']['MainPID'],camera_pid=after['camera']['MainPID'],
 boot=after['boot'],actual_and_pending_entry_unchanged=True,listening=after['listening'],microphone_open=after['microphone_open'],
 automatic_following=after['pan']['automatic_following'])))
