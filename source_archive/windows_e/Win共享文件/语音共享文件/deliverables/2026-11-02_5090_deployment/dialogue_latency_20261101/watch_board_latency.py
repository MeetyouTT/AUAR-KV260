"""Bounded two-turn timing observation through the original GUI. No raw media/text export."""
import argparse
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import re
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
parser=argparse.ArgumentParser()
parser.add_argument('--observe-only',action='store_true')
args=parser.parse_args()
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
OWNER={'pid':16318,'birth':'1738515','cmd':'0773efafd4a34e1785cf7f7dd51398d591a7de42f40f7c169997118a47458963'}

def owner():
    proc=Path('/proc')/str(OWNER['pid'])
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==OWNER['birth']
    assert hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==OWNER['cmd']

def request(command=None):
    connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        if command is None:connection.request('GET','/api/state')
        else:
            data=json.dumps({'type':command}).encode()
            connection.request('POST','/api/command',data,{'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
        response=connection.getresponse();raw=response.read(2097153)
        assert response.status==200 and len(raw)<=2097152
        return json.loads(raw)
    finally:connection.close()

def obj(value,key):
    result=value.get(key,{}) if isinstance(value,dict) else {}
    return result if isinstance(result,dict) else {}

def token(value):
    return hashlib.sha256(value.encode()).hexdigest()[:16] if isinstance(value,str) and value else None

def metrics(value,depth=0):
    if not isinstance(value,dict) or depth>4:return {}
    result={}
    for key,item in value.items():
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,70}',key):continue
        if type(item) in (int,float,bool) or item is None:result[key]=item
        elif isinstance(item,dict):result[key]=metrics(item,depth+1)
        elif key in ('request_id','capture_id','session_id'):result[key+'_hash']=token(item)
        elif key=='error_class' and isinstance(item,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,80}',item):result[key]=item
    return result

def enum(value,allowed):return value if value in allowed else None

def jobs(state):
    business=obj(state,'board_business');dialogue=obj(business,'dialogue')
    alternate=obj(obj(state,'local_transcription'),'service')
    return dialogue if 'latency' in dialogue else alternate

def project(state):
    job=jobs(state);hf=obj(state,'handsfree_dialogue');rec=obj(state,'local_recording')
    transcription=obj(state,'local_transcription');ack=obj(job,'last_playback_ack')
    return {'event':'SAMPLE','board_mono':time.monotonic(),'api_sequence':state.get('sequence'),
        'phase':enum(state.get('phase'),('IDLE','VOICE_PREPARING','VOICE_STARTING','SPEAKING','ACTION','DIALOGUE_WAITING')),
        'playing':state.get('playing') is True,'hf_enabled':hf.get('enabled') is True,
        'hf_state':enum(hf.get('state'),('PAUSED','WAITING_SERVICE','WAITING_SPEECH','WAITING_WAKE','COOLDOWN','CONVERSATION')),
        'microphone_open':hf.get('microphone_open') is True,
        'recording_state':enum(rec.get('state'),('IDLE','READY','RECORDING','ERROR','STOPPING')),
        'recording_sample_count':rec.get('sample_count'),'recording_duration_seconds':rec.get('duration_seconds'),
        'recording_metadata':metrics(obj(rec,'result')),
        'transcription_state':enum(transcription.get('state'),('IDLE','DISABLED','PENDING','TRANSCRIBING','READY','ANSWERING','ANSWERED','ERROR','CANCELLED')),
        'turn_hash':token(transcription.get('request_id')),
        'job_pending':job.get('pending') is True,'latency':metrics(obj(job,'latency')),
        'ack':{'turn_hash':token(ack.get('request_id')),'committed':ack.get('committed'),
            'metrics':metrics(ack)},
        'automatic_conversation':metrics(obj(state,'automatic_conversation')),
        'audio_frontend':metrics(obj(state,'audio_frontend')),
        'audio_output':metrics(obj(state,'audio_output')),
        'stream_diagnostics':metrics(obj(state,'stream_diagnostics')),
        'job_diagnostics':metrics(obj(job,'diagnostics')),
        'stream_metrics':metrics(obj(state,'stream')),
        'native_frames':obj(state,'avatar_display').get('frames'),
        'gui_fault_count':obj(state,'runtime_faults').get('count'),
        'recording_error_present':bool(rec.get('error')),'hf_error_present':bool(hf.get('error'))}

def emit(value):print(json.dumps(value,separators=(',',':')),flush=True)

owner();baseline=request();base=project(baseline)
baseline_enabled=base['hf_enabled'];opened=False;seen=set()
if base['ack']['turn_hash']:seen.add(base['ack']['turn_hash'])
emit({'event':'BASELINE','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':BOOT,'baseline_listening_enabled':baseline_enabled,'baseline':base,
    'interval_seconds':0.25,'max_observation_seconds':180,'target_completed_turns':2,
    'speech_or_audio_or_images_exported':False})
completed=set();ready=False;started=time.monotonic();deadline=started+180;last_owner=started
try:
    if not baseline_enabled and not args.observe_only:
        assert base['hf_state']=='PAUSED' and not base['microphone_open'] and not base['playing'] and not base['job_pending']
        # Mark possible ownership before send; a lost HTTP reply must not cause a second toggle.
        opened=True
        request('conversation_toggle')
        emit({'event':'LISTENING_START_REQUESTED','board_mono':time.monotonic()})
    while time.monotonic()<deadline:
        tick=time.monotonic()
        if tick-last_owner>=2:owner();last_owner=tick
        current=request();sample=project(current);emit(sample)
        if not ready and sample['hf_enabled'] and sample['microphone_open'] and sample['hf_state']=='WAITING_SPEECH':
            ready=True;deadline=time.monotonic()+180
            emit({'event':'READY_FOR_TWO_TURNS','board_mono':time.monotonic(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        ack=sample['ack']
        if ack['turn_hash'] and ack['committed'] is True and ack['turn_hash'] not in seen:
            completed.add(ack['turn_hash']);seen.add(ack['turn_hash'])
            emit({'event':'TURN_COMPLETED','board_mono':time.monotonic(),'ordinal':len(completed),'turn_hash':ack['turn_hash']})
        if len(completed)>=2 and not sample['playing'] and not sample['job_pending']:break
        if ready and not sample['hf_enabled'] and not args.observe_only:break
        time.sleep(max(0,0.25-(time.monotonic()-tick)))
finally:
    # Restore only the paused preference that this observer enabled, using the normal UI action.
    owner();current=request();last=project(current)
    if opened and last['hf_enabled']:
        request('conversation_toggle')
        time.sleep(0.4);last=project(request())
        emit({'event':'LISTENING_RESTORED_PAUSED','board_mono':time.monotonic(),
            'hf_enabled':last['hf_enabled'],'microphone_open':last['microphone_open'],'hf_state':last['hf_state']})
    emit({'event':'FINISHED','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'completed_new_turns':len(completed),'ready_seen':ready,'baseline_listening_enabled':baseline_enabled,
        'observer_enabled_listening':opened,'final':last,'motion_requested':False,
        'raw_audio_text_or_identity_exported':False})
