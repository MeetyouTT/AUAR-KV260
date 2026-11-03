"""Observe a user-operated board recording and actual playback; do not trigger capture."""
import base64
import json
from board_ssh import ssh,HERE

script=r'''
import base64,http.client,json,os,sys,time
from pathlib import Path
def get(port,path):
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        connection.request('GET',path);reply=connection.getresponse();return json.loads(reply.read())
    finally:connection.close()
initial=get(8783,'/api/state');camera=get(8790,'/health')
turns=len(initial['turns']);samples=[];deadline=time.monotonic()+180
while time.monotonic()<deadline:
    state=get(8783,'/api/state')
    samples.append({'at':time.monotonic(),'phase':state['phase'],'playing':state['playing'],
                    'paused':state['paused'],'audio_time':state['audio_time'],'mouth_level':state['mouth_level'],
                    'speech_gain':state['speech_gain'],'recording':state['local_recording']['state'],
                    'transcription':state['local_transcription']['state']})
    if len(state['turns'])>turns and state['phase']=='IDLE' and not state['playing']:break
    if state['local_transcription']['state']=='ERROR':break
    time.sleep(.1)
else:state=get(8783,'/api/state')
after=get(8790,'/health')
played=[row for row in samples if row['playing'] and row['audio_time']>0]
new_turn=state['turns'][-1] if len(state['turns'])>turns else None
owner=state['local_recording'].get('result') or {}
transcription=state['local_transcription']
matched=bool(owner.get('capture_id') and owner.get('capture_id')==transcription.get('capture_id'))
okay=bool(new_turn and played and matched and transcription.get('voice_reply') and not state['error'])
recording_observed=any(row['recording']=='RECORDING' for row in samples) or bool(new_turn)
status='PASS_LIVE_BOARD_RECORDING_AND_PLAYBACK' if okay else 'WAITING_FOR_USER_RECORDING' if not recording_observed and not state['error'] else 'INCOMPLETE_OR_ERROR'
report={'status':status,
        'initial':initial,'final':state,'samples':samples,'actual_playing_samples':len(played),
        'nonzero_mouth_samples':sum(row['mouth_level']>0 for row in played),
        'capture_identity_matched':matched,'turn':new_turn,'camera_before':camera,'camera_after':after,
        'camera_pid_preserved':camera['pid']==after['pid'],'new_recording_user_operated':recording_observed,
        'auditory_quality_requires_user_confirmation':True}
try:
    sys.path.insert(0,'/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura')
    os.environ['DISPLAY']=':0'
    from tools.board_screen_capture import capture
    path=Path('/tmp/aura-live-voice-20261018.png');capture(path)
    report['screen_png']=base64.b64encode(path.read_bytes()).decode()
except Exception as exc:report['screen_error']=str(exc)
print(json.dumps(report,ensure_ascii=False))
'''
report=json.loads(ssh('python3 -',script,timeout=200))
screen=report.pop('screen_png',None)
if screen:
    (HERE/'board_live_voice.png').write_bytes(base64.b64decode(screen))
    report['screen_file']='board_live_voice.png'
(HERE/'live_turn_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'turn':report['turn'],'transcript':report['final']['local_transcription']['text'],
                  'playing_samples':report['actual_playing_samples'],'mouth_samples':report['nonzero_mouth_samples'],
                  'camera_preserved':report['camera_pid_preserved']},ensure_ascii=True))
