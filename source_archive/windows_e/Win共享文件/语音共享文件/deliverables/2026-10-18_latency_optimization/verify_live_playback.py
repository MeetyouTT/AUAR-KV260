"""Observe one new production UI turn without starting or injecting recordings."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
prior_path=HERE/'live_playback_fragmented.json'
prior=json.loads(prior_path.read_text(encoding='utf-8'))['playback_ack']['request_id'] if prior_path.is_file() else None
remote=r'''
import json,time,urllib.request
def get(port,path,host='127.0.0.1'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=3) as response:return json.load(response)
health=get(8792,'/health','192.168.50.1')
assert health.get('latency_options')=={'reply_first':True,'early_sentence':True,'coalesce_chat':True}
before=get(8783,'/api/state');camera=get(8790,'/health');previous=PRIOR_REQUEST
samples=[];deadline=time.monotonic()+100;last=None
while time.monotonic()<deadline:
    state=get(8783,'/api/state');transcription=state['local_transcription']
    if transcription.get('request_id') and transcription['request_id']!=previous:
        last=state
        samples.append({key:state.get(key) for key in ('phase','state','playing','speech_gain','mouth_level','audio_time')})
        if state.get('error') or transcription.get('error'):raise RuntimeError(state.get('error') or transcription['error'])
        ack=transcription['service'].get('last_playback_ack') or {}
        if transcription['state']=='ANSWERED' and ack.get('committed') and ack['request_id']==transcription['request_id']:
            turn=state['turns'][-1];capture=state['local_recording']['result']
            assert capture['capture_id']==transcription['capture_id'] and 'llm' in turn['server_metrics']['timing']
            assert turn['audio_complete']
            print(json.dumps({'status':'PASS_NEW_USER_PRODUCTION_PLAYBACK_ACK','health':health,
                 'transcript':transcription['text'],'capture':capture,'turn':turn,'playback_ack':ack,
                 'camera_pid':get(8790,'/health')['pid'],'camera_preserved':get(8790,'/health')['pid']==camera['pid'],
                 'samples':samples,'final_state':state,'acoustic_onset_measured':False}));break
    time.sleep(.1)
else:
    print(json.dumps({'status':'NO_NEW_COMPLETED_USER_TURN','state':last or before,'health':health}))
'''.replace('PRIOR_REQUEST',repr(prior))
report=json.loads(ssh('python3 -',remote,timeout=115))
(HERE/'live_playback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in report.items() if key not in ('samples','state','final_state')},ensure_ascii=True))
