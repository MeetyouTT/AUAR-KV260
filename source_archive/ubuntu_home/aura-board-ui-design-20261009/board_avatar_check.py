"""Check cached playback on its new owner while actual camera preview continues."""
import json,time,urllib.request
from pathlib import Path

root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
base='http://127.0.0.1:8783'
def api(value=None):
    request=base+'/api/state' if value is None else urllib.request.Request(base+'/api/command',
        data=json.dumps(value).encode(),headers={'Origin':base,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=4) as s:return json.load(s)
def wait(predicate,seconds=15):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        state=api()
        if predicate(state):return state
        assert not state['error'],state['error']
        time.sleep(.05)
    raise RuntimeError('Playback condition timed out')
initial=api();launch=json.loads((root/'launch.json').read_text())
assert initial['phase']=='IDLE' and not initial['playing'] and not initial['avatar_command_pending']
assert initial['ui_runtime']['snapshot']['source_kind']=='actual' and initial['ui_runtime']['frame_visible']
settings={k:initial['ui_settings'][k] for k in ('volume','muted','fullscreen','economy')}
times={};states={}
def command(label,data):
    start=time.monotonic();value=api(data);times[label]=round((time.monotonic()-start)*1000,2)
    assert value['ok'],value
    return value
try:
    queued=command('demo',{'type':'demo','index':0})
    assert queued['queued'] and queued['command_id']
    states['playing']=wait(lambda s:s['playing'] and s['audio_time']>.2)
    command('pause',{'type':'pause'})
    states['paused']=wait(lambda s:s['paused'])
    time.sleep(.15);a=api()['audio_time'];time.sleep(.35);b=api()['audio_time']
    assert abs(b-a)<.05,(a,b)
    command('resume',{'type':'pause'})
    states['resumed']=wait(lambda s:not s['paused'] and s['audio_time']>b+.1)
finally:
    command('cancel',{'type':'event','event':'cancel'})
    final=wait(lambda s:s['phase']=='IDLE' and not s['playing'] and not s['avatar_command_pending'])
assert final['ui_runtime']['frame_visible']
assert final['ui_runtime']['preview_metrics']['displayed_frames']>initial['ui_runtime']['preview_metrics']['displayed_frames']
assert json.loads((root/'launch.json').read_text())['pid']==launch['pid']
assert {k:final['ui_settings'][k] for k in settings}==settings
assert any(r['command_id']==queued['command_id'] and r['ok'] and r.get('result')
    for r in final['avatar_renderer']['command_results'])
print(json.dumps({'checks_passed':['actual_cached_playback','audio_clock_pause','resume',
    'cancel_to_idle','preview_continues_during_playback','gui_pid_unchanged','settings_preserved'],
    'command_ack_ms':times,'pause_audio_delta_seconds':b-a,'initial':initial,'final':final,
    'states':states,'gui_pid':launch['pid']},ensure_ascii=False))
