"""Verify playback blocks recording, then leave the interaction page idle."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
sys.path.insert(0,str(root/'aura'))
from board.runtime.character import DEMO_LINES
from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer


def api(data=None):
    base='http://127.0.0.1:8783'
    request=base+'/api/state' if data is None else urllib.request.Request(base+'/api/command',
        data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':base})
    with urllib.request.urlopen(request,timeout=4) as r:return json.load(r)


def wait(predicate,seconds=6):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        state=api()
        if predicate(state):return state
        time.sleep(.1)
    raise AssertionError('Playback/recording state did not settle')


cache=SelectedVoiceSynthesizer(root/'deliverables/2026-10-06_xilan_live/cache')
# The runtime root contains the source tree and a sibling deliverables tree.
records=[cache.cached(row['text']) for row in DEMO_LINES]
assert all(records)
index=max(range(len(records)),key=lambda i:records[i]['duration_seconds'])
request=api({'type':'demo','index':index})
playing=wait(lambda s:s['phase']=='SPEAKING' and s['playing'])
assert not playing['local_recording']['can_start']
record_request=api({'type':'service_action','action':'record_start'})
blocked=wait(lambda s:any(row['command_id']==record_request['command_id'] for row in s['avatar_renderer']['command_results']))
outcome=next(row for row in blocked['avatar_renderer']['command_results'] if row['command_id']==record_request['command_id'])
assert not outcome['ok'] and '结束当前录音或播放' in outcome['error'],outcome
assert blocked['local_recording']['state']!='RECORDING'
api({'type':'event','event':'reset'})
wait(lambda s:s['phase']=='IDLE' and s['audio_output_state']=='NULL')
api({'type':'service_action','action':'record_start'})
wait(lambda s:s['local_recording']['state']=='RECORDING' and s['local_recording']['sample_count']>=3200)
api({'type':'event','event':'cancel'})
final=wait(lambda s:s['local_recording']['state']=='CANCELLED' and s['local_recording']['can_start']
    and s['phase']=='IDLE' and s['audio_output_state']=='NULL' and not s['avatar_command_pending'])
assert final['local_recording']['result'] is None and not final['error']
assert api({'type':'ui_page','page':'main'})['ok']
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:camera=json.load(r)
assert not any(camera[k] for k in ('camera_error','detector_error','preview_error'))
services=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service',
    '-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts'],text=True)
assert services.count('ActiveState=active')==2 and services.count('NRestarts=0')==2
print(json.dumps({'status':'PASS_PLAYBACK_RECORDING_INTERLOCK_AND_FINAL_IDLE','play_request':request,
    'playing_observed':{k:playing[k] for k in ('phase','playing','audio_output_state')},
    'recording_rejected_during_playback':outcome,'final':final,'camera':camera,'services':services,
    'route':subprocess.check_output(['ip','route'],text=True),
    'addresses':subprocess.check_output(['ip','-j','address'],text=True)},ensure_ascii=False))
