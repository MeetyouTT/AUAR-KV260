"""Capture the user-confirmed new recording from the activated production UI."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,time,urllib.request
def get(port,path,host='127.0.0.1'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=3) as response:return json.load(response)
deadline=time.monotonic()+50
while True:
    state=get(8783,'/api/state')
    transcription=state.get('local_transcription',{})
    ack=transcription.get('service',{}).get('last_playback_ack') or {}
    if (state.get('turns') and transcription.get('state')=='ANSWERED' and ack.get('committed') and
            ack.get('request_id')==transcription.get('request_id') and state.get('phase')=='IDLE'):break
    if state.get('error') or transcription.get('error'):raise RuntimeError(state.get('error') or transcription['error'])
    if time.monotonic()>=deadline:raise RuntimeError('No completed live user turn with matching playback acknowledgement')
    time.sleep(.2)
capture=state['local_recording']['result']
assert capture and capture['capture_id']==transcription['capture_id']
health=get(8792,'/health','192.168.50.1');camera=get(8790,'/health')
assert health['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and health['num_step']==16
report={'status':'PASS_USER_RECORDING_PRODUCTION_STREAM_PLAYBACK_ACK','input_kind':'NEW_USER_MCP01_RECORDING',
        'user_report':'已听到完整回答','capture':capture,'transcript':transcription['text'],
        'request_id':transcription['request_id'],'playback_ack':ack,'turn':state['turns'][-1],
        'health':health,'camera_pid':camera['pid'],'final_state':state,'acoustic_onset_measured':False}
print(json.dumps(report))
'''
report=json.loads(ssh('python3 -',remote,timeout=60))
(HERE/'live_turn.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in report.items() if key!='final_state'},ensure_ascii=False))
