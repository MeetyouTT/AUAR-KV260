"""Bounded metadata-only live voice observation; does not control listening."""
import hashlib
import http.client
import json
from pathlib import Path
import time

E=None  # LIVE_MONITOR_EXPECTED
def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
    assert hashlib.sha256(Path(E['startup_path']).read_bytes()).hexdigest()==E['startup_sha256']
    for o in E['owners']:
        p=Path('/proc')/str(o['pid']);assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==o['birth_ticks'];assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()==o['command_sha256']
def state():
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:c.request('GET','/api/state');r=c.getresponse();data=r.read(2097153);assert r.status==200 and len(data)<=2097152;return json.loads(data)
    finally:c.close()
def hashed(value):return hashlib.sha256(value.encode()).hexdigest()[:16] if isinstance(value,str) and value else None
def sample(v):
    h=v.get('handsfree_dialogue') or {};b=v.get('board_business') or {};s=b.get('speaker') or {};d=b.get('dialogue') or {};ack=d.get('last_playback_ack') or {};address=s.get('conversation_address') or {};lat=d.get('latency') or {};rec=v.get('local_recording') or {}
    numeric=lambda x:{k:z for k,z in x.items() if type(z) in (int,float,bool) and 'score' not in k.lower()}
    return {'event':'SAMPLE','board_mono':time.monotonic(),'api_sequence':v.get('sequence'),'phase':v.get('phase'),'listening_enabled':h.get('enabled'),'microphone_open':h.get('microphone_open'),'handsfree_state':h.get('state'),'playing':bool(v.get('playing')),'pending_job':bool(v.get('pending_job')),'recording_state':rec.get('state'),'recording_duration_seconds':rec.get('duration_seconds'),'speaker_counts':{k:s.get(k) for k in ('submitted','complete','cancelled','unavailable','evidence_errors')},'speaker_mode':address.get('mode'),'address_phase':address.get('phase'),'current_capture_match':address.get('current_capture_match'),'session_cached':address.get('session_cached'),'required_captures':address.get('required_captures'),'matched_captures':address.get('matched_captures'),'identity_verified':address.get('identity_verified'),'personal_memory_allowed':address.get('personal_memory_allowed'),'latency_ms':numeric(lat),'ack_hash':hashed(ack.get('request_id')),'ack_committed':ack.get('committed'),'fault_count':(v.get('runtime_faults') or {}).get('count'),'following':(v.get('manual_pan') or {}).get('automatic_following')}
def emit(v):print(json.dumps(v),flush=True)
verify();base=sample(state());assert base['speaker_mode']=='PER_UTTERANCE';seen={base['ack_hash']} if base['ack_hash'] else set();completed=set();t=time.monotonic();reason='duration_limit';samples=0
emit({'event':'READY','board_mono':t,'maximum_seconds':150,'target_new_playback_ACKs':3,'baseline':base,'no_names_audio_vectors_scores_or_transcripts_exported':True,'control_commands':0})
try:
    while time.monotonic()-t<150:
        loop=time.monotonic()
        if samples%5==0:verify()
        row=sample(state());samples+=1;emit(row)
        if row['following'] or row['fault_count']!=0:reason='state_changed_or_fault';break
        if not row['listening_enabled']:reason='listening_paused';break
        if row['ack_hash'] and row['ack_committed'] is True and row['ack_hash'] not in seen:
            seen.add(row['ack_hash']);completed.add(row['ack_hash']);emit({'event':'TURN_COMPLETED','ordinal':len(completed),'board_mono':row['board_mono']})
        if len(completed)>=3 and not row['playing'] and not row['pending_job']:reason='three_new_ACKs';break
        time.sleep(max(0,.75-(time.monotonic()-loop)))
finally:
    emit({'event':'FINISHED','reason':reason,'elapsed_seconds':time.monotonic()-t,'sample_count':samples,'completed_new_ACKs':len(completed),'final':sample(state()),'control_commands':0,'observer_restored_or_paused_listening':False})
