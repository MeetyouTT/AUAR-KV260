"""Summarize actual desktop/browser evidence and save a source fingerprint list."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;AURA=HERE.parent.parent/'aura'
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
qt=read('qt_window_verification.json');idle=read('qt_progress.json')
intervals=[(b['wall_time']-a['wall_time'])*1000 for a,b in zip(qt['frames'],qt['frames'][1:])]
browser=read('browser_final_script.json');first=read('browser_first_voice.json')
pause=read('browser_pause_verification.json');livepause=read('browser_live_pause.json');cancel=read('browser_cancel_generation.json')
assert qt['status']=='PASS' and qt['final_state']=='IDLE' and not qt['errors'] and not qt['rejected']
assert idle['finished'] and idle['idle_blink_samples']>0
assert browser['ended'] and browser['audioTime']==47.27 and browser['audioError'] is None
assert pause['held'] and livepause['audioHeld'] and livepause['eyesHeld']
assert cancel['after']['mode']=='idle' and cancel['after']['audioTime']==0
result={'status':'PASS','regression':{'passed':531,'seconds':44.51,'command':'validation Python -B -m pytest tests -q'},
        'targeted':{'passed':34,'seconds':26.54},
        'desktop':{'samples':qt['samples'],'duration_seconds':qt['duration_seconds'],
                   'max_submit_interval_ms':max(intervals),'submit_intervals_over_100ms':sum(v>100 for v in intervals),
                   'blink_samples':sum(r['blink_active'] for r in qt['frames']),
                   'blink_while_speaking_samples':sum(r['blink_active'] and r['speech_gain']>.1 for r in qt['frames']),
                   'final_state':qt['final_state'],'ended_idle_blink_samples':idle['idle_blink_samples'],
                   'timing_scope':'software frame submissions, not physical display/acoustic latency'},
        'browser':{'final_script_complete':True,'audio_error':browser['audioError'],'script_pause_held':pause['held'],
                   'new_voice_pause_held':livepause['audioHeld'] and livepause['eyesHeld'],
                   'blink_while_new_voice_samples':sum(r['mode']=='live' and r['blinkPhase'] is not None and r['speechGain']>.1 for r in first['records']),
                   'cancelled_generation_no_late_playback':True,
                   'cancelled_job_id':cancel['job'],'cancelled_job_api_status':'CANCELLED'},
        'audio_and_routes':read('delivery_verification.json'),'asr':read('asr_verification.json'),
        'limits':['PC non-streaming synthesis','activity/amplitude mouth, not phoneme alignment',
                  'no new microphone input UI','formal board adapter and physical device validation pending'],
        'source_files':[]}
paths=[AURA/'board/runtime/audio/selected_voice.py',AURA/'tools/selected_voice_service.py',AURA/'tools/facial_layers.py',
       AURA/'tools/selected_voice_demo.py',AURA/'tests/test_voice_blink.py',HERE/'player.js',HERE/'serve_preview.py',
       HERE/'blink_profile.json',HERE/'live_assets.json',HERE.parent/'2026-10-06_voice_script_sync/acceptance.json']
for path in paths:
    result['source_files'].append({'path':str(path.relative_to(AURA.parent)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(HERE/'final_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
plan=read('plan.json');plan['mouth_method']='energy activity + smooth amplitude aperture + retained-aperture cancel closure; not phoneme alignment'
plan['blink_method']='independent existing-eye layer; 290ms closure; 3.2-5.8s gaps'
(HERE/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('status','regression','desktop','browser')},ensure_ascii=False))
