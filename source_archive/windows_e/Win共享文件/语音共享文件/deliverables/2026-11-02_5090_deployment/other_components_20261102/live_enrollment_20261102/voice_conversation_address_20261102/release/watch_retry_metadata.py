"""Continuous fixed metadata and SQL COUNTs. No audio, names or text exported."""
import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import sys
import time

root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='d667b871e159a9f2b52cfb48a16a31ba39847e4d68658a521aee006e7db915ef'
startup=json.loads(raw);aura=Path(startup['runtime'])/'aura';sys.path.insert(0,str(aura))
from common.feature_intents import speaker_query_requested
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from common.board_memory import APPLICATION_ID
phases={'MATCHED','WAITING','NO_MATCH','NO_FRESH_RESULT','IDLE','PROCESSING','COLLECTING','CANDIDATE','EXPIRED','CANCELLED','INSUFFICIENT_SPEECH','NO_CANDIDATE','NO_ENROLLMENT','SOURCE_CHANGED','UNAVAILABLE'}
states={'PAUSED','WAITING_SPEECH','CONVERSATION','COOLDOWN','CHECKING_SPEECH','WAITING_SERVICE','SERVICE_ERROR','CAPTURE_ERROR','CONVERSATION_SILENCE','AUDIO_OWNER_CHANGED','SPEECH_ACCEPTED','DIRECT_SPEECH','CURRENT_TURN_CANCELLED','BUSINESS_OR_NATIVE_NOT_READY'}
words={'voice':'声音','recognize':'识别','discern':'辨认','distinguish':'辨别','according':'根据','who':'是谁','extra_lai':'来','extra_chu':'出'}
def shape(text,label):
    if type(text) is not str:return 0
    if label=='query':return int(speaker_query_requested(text))
    if label=='probe':return int(BoardSpeakerBusiness._explicit_self_match(text))
    return int(words[label] in text)
db=sqlite3.connect('file:/home/root/.local/share/aura-board-business/timeline.sqlite3?mode=ro',uri=True,timeout=.2,isolation_level=None)
db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA application_id').fetchone()==(APPLICATION_ID,)
db.create_function('fixed_shape',2,shape)
db.execute('ATTACH DATABASE ? AS named',('file:/home/root/.local/share/aura-board-business/speaker/speakers.sqlite3?mode=ro',))
assert db.execute('PRAGMA named.application_id').fetchone()==(0x41555350,)
start=time.monotonic()
try:
    for index in range(120):
        record=dict(kind='sample',elapsed=round(time.monotonic()-start,2))
        c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
        try:
            c.request('GET','/api/state');r=c.getresponse();data=r.read(2097153)
            assert r.status==200 and len(data)<=2097152
            v=json.loads(data);h=v.get('handsfree_dialogue') or {};timing=h.get('listening_timing') or {};s=(v.get('board_business') or {}).get('speaker') or {};p=s.get('conversation_address') or {};d=(v.get('board_business') or {}).get('dialogue') or {};route=d.get('last_voice_route') or {}
            record.update(session_cached=p.get('session_cached'),required_captures=p.get('required_captures'),identity_match_threshold=s.get('identity_match_threshold'), field_calibrated=p.get('field_calibrated'), identity_verified=p.get('identity_verified'), personal_memory_allowed=p.get('personal_memory_allowed'), phase=p.get('phase') if p.get('phase') in phases else None,
                count=p.get('matched_captures') if type(p.get('matched_captures')) is int else None,
                historical_candidates=p.get('matched_captures') if type(p.get('matched_captures')) is int else None,
                state=h.get('state') if h.get('state') in states else 'OTHER',reason=h.get('reason') if h.get('reason') in states else 'OTHER',
                last_stop=timing.get('last_stop_reason') if timing.get('last_stop_reason') in states else None,
                enabled=h.get('enabled') is True,mic=h.get('microphone_open') is True,playing=v.get('playing') is True,
                monitor_error=bool(h.get('error')),route_generation=route.get('generation') if type(route.get('generation')) is int else None,
                asr_characters=route.get('transcript_characters') if type(route.get('transcript_characters')) is int else None,
                runtime_fault_count=(v.get('runtime_faults') or {}).get('count'))
        except Exception:record['api_available']=False
        finally:c.close()
        try:
            db.execute('BEGIN')
            user='FROM (SELECT b.text FROM bm_turns t JOIN bm_bodies b ON b.event_id=t.user_event_id WHERE t.created_utc>=? ORDER BY t.created_utc DESC LIMIT 12) q'
            answer='FROM (SELECT b.text FROM bm_turns t JOIN bm_bodies b ON b.event_id=t.assistant_event_id WHERE t.created_utc>=? ORDER BY t.created_utc DESC LIMIT 12) q'
            counts={'users':db.execute('SELECT COUNT(*) '+user,(SINCE_UTC,)).fetchone()[0],
                'scopes':db.execute('SELECT COUNT(DISTINCT scope_id) FROM bm_turns WHERE created_utc>=?',(SINCE_UTC,)).fetchone()[0]}
            for label in list(words)+['query','probe']:
                counts[label]=db.execute('SELECT COUNT(*) '+user+' WHERE fixed_shape(q.text,?)=1',(SINCE_UTC,label)).fetchone()[0]
            for label,prefix in {'candidate_reply':'声音候选称呼是','progress_reply':'已完成第','no_candidate_reply':'这段声音还未形成','quality_reply':'这段声音尚未通过','old_uncalibrated_reply':'本机有声纹记录'}.items():
                counts[label]=db.execute('SELECT COUNT(*) '+answer+' WHERE instr(q.text,?)>0',(SINCE_UTC,prefix)).fetchone()[0]
            counts['registered_name_in_reply']=db.execute('SELECT COUNT(*) FROM bm_turns t JOIN bm_bodies b ON b.event_id=t.assistant_event_id CROSS JOIN named.identities i WHERE t.created_utc>=? AND instr(b.text,i.name)>0',(SINCE_UTC,)).fetchone()[0]
            db.execute('ROLLBACK');record['counts']=counts
        except sqlite3.Error:
            if db.in_transaction:db.execute('ROLLBACK')
            record['counts_available']=False
        print(json.dumps(record),flush=True)
        if record.get('counts',{}).get('registered_name_in_reply',0)>0 and record.get('mic') and not record.get('playing'):break
        if index<119:time.sleep(1)
finally:db.close()
print(json.dumps(dict(kind='finished',read_only=True,names_ids_text_scores_audio_images_exported=False)),flush=True)
