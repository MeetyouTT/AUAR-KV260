"""Observe new automatic rounds; never inject audio or start the microphone."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
minimum=int(sys.argv[1]) if len(sys.argv)>1 else 2
assert minimum in (1,2)

remote=r'''
import json,time,urllib.request
def get():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:return json.load(r)
before=get();seen={};transitions=[];previous=None;started=time.monotonic();deadline=started+180
report={'status':'WAITING_FOR_USER','actual_user_input':True,'audio_injected':False,'before':before,'rounds':seen,'transitions':transitions}
while time.monotonic()<deadline:
    state=get();auto=state.get('automatic_conversation',{});rec=state.get('local_recording',{});tx=state.get('local_transcription',{})
    signature=(auto.get('enabled'),auto.get('state'),rec.get('state'),tx.get('state'),tx.get('request_id'))
    if signature!=previous:
        transitions.append({'elapsed_s':round(time.monotonic()-started,3),'automatic':auto,'recording':rec.get('state'),
                            'capture_id':(rec.get('result') or {}).get('capture_id'),'request_id':tx.get('request_id'),'transcription_state':tx.get('state'),'phase':state.get('phase')})
        previous=signature
    request=tx.get('request_id')
    if request:
        row=seen.setdefault(request,{'request_id':request})
        row.update(capture_id=tx.get('capture_id'),transcript=tx.get('text'),last_transcription_state=tx.get('state'))
        if rec.get('result'):row['capture']=rec['result']
        ack=tx.get('service',{}).get('last_playback_ack') or {}
        if ack.get('request_id')==request:row['ack']=ack
        if tx.get('state')=='ANSWERED' and state.get('turns'):row['turn']=state['turns'][-1]
    if auto.get('error') or tx.get('state')=='ERROR' or state.get('error'):
        report.update(status='LIVE_ERROR',final=state);break
    completed=[r for r in seen.values() if r.get('ack',{}).get('committed') and r.get('turn',{}).get('audio_complete')]
    if len(completed)>=MINIMUM and not auto.get('enabled') and rec.get('state')!='RECORDING' and state.get('phase')=='IDLE' and not tx.get('service',{}).get('pending'):
        report.update(status='PASS_TWO_AUTOMATIC_ROUNDS_AND_USER_STOP',final=state);break
    time.sleep(.1)
else:report.update(status='OBSERVATION_TIMEOUT',final=get())
report['acoustic_onset_measured']=False
print(json.dumps(report))
'''
result=json.loads(ssh('python3 -',remote.replace('MINIMUM',str(minimum)),timeout=195))
result['minimum_rounds_required']=minimum
if minimum==1 and result['status']=='PASS_TWO_AUTOMATIC_ROUNDS_AND_USER_STOP':result['status']='PASS_ONE_AUTOMATIC_ROUND_AND_USER_STOP'
(HERE/'live_playback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'rounds':[{'request_id':row['request_id'],
    'transcript':row.get('transcript'),'reply':row.get('turn',{}).get('text'),
    'ack':row.get('ack'),'seconds':row.get('turn',{}).get('request_to_answer_seconds')}
    for row in result['rounds'].values()],'transitions':len(result['transitions'])},ensure_ascii=True))
