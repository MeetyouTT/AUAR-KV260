"""Observe one user-operated live turn after the startup fix."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
s=r'''
import json,time,urllib.request

def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3))
initial=get(8783,'/api/state');camera=get(8790,'/health');count=len(initial['turns']);samples=[];end=time.monotonic()+90
while time.monotonic()<end:
 u=get(8783,'/api/state')
 samples.append({'at':time.monotonic(),'phase':u['phase'],'playing':u['playing'],'audio_time':u['audio_time'],'mouth_level':u['mouth_level'],'audio_output_state':u['audio_output_state'],'recording':u['local_recording']['state'],'transcription':u['local_transcription']['state']})
 if len(u['turns'])>count and u['phase']=='IDLE' and not u['playing']:break
 if u['local_transcription']['state']=='ERROR' or u['error']:break
 time.sleep(.08)
else:u=get(8783,'/api/state')
after=get(8790,'/health');new=u['turns'][-1] if len(u['turns'])>count else None
playing=[v for v in samples if v['playing'] and v['audio_time']>0];starting=[v for v in samples if v['audio_output_state']=='STARTING']
owner=u['local_recording'].get('result') or {};text=u['local_transcription'];same=bool(owner.get('capture_id') and owner.get('capture_id')==text.get('capture_id'))
passed=bool(new and playing and same and not u['error'] and text.get('voice_reply',{}).get('num_step')==16)
r={'status':'PASS_FIXED_LIVE_PLAYBACK_SOFTWARE' if passed else 'WAITING_OR_INCOMPLETE','initial':initial,'final':u,'samples':samples,'new_turn':new,'playing_samples':len(playing),'nonzero_mouth_samples':sum(v['mouth_level']>0 for v in playing),'capture_matched':same,'starting_samples':len(starting),'startup_mouth_stayed_closed':all(v['mouth_level']==0 and not v['playing'] for v in starting),'camera_pid_preserved':camera['pid']==after['pid'],'camera_pid':after['pid'],'auditory_quality_requires_user_confirmation':True}
print(json.dumps(r))
'''
v=json.loads(ssh('python3 -',s,timeout=110));(HERE/'fixed_live_turn.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v[k] for k in ('status','new_turn','playing_samples','nonzero_mouth_samples','capture_matched','starting_samples','startup_mouth_stayed_closed','camera_pid_preserved')}))
