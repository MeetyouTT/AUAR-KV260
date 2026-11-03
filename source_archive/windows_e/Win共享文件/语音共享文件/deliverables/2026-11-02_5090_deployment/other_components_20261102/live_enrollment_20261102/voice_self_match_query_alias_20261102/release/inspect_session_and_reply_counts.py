"""Fixed session metadata and aggregate reply categories, no private contents."""
import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import time

root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()=='44e8f154c9dd72d3b7619160f7a2dac64fda529daba91a96a196c12f68c8a295'
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
    c.request('GET','/api/state');r=c.getresponse();raw=r.read(2097153)
    assert r.status==200 and len(raw)<=2097152
    v=json.loads(raw)
finally:c.close()
h=v.get('handsfree_dialogue') or {};timing=h.get('listening_timing') or {};tx=v.get('local_transcription') or {}
choices={'PAUSED','WAITING_SPEECH','CONVERSATION','COOLDOWN','CHECKING_SPEECH','WAITING_SERVICE','SERVICE_ERROR','CAPTURE_ERROR','CONVERSATION_SILENCE','AUDIO_OWNER_CHANGED','NO_VALID_INITIAL_SPEECH','NO_SINGLE_FACE','NOT_FRONTAL','TARGET_CHANGED','STALE_FACE','VISUAL_UNAVAILABLE','VISUAL_SPEECH_NOT_BOUND','SPEECH_TARGET_NOT_CONFIRMED','SILENCE_TIMEOUT','SPEECH_ACCEPTED','DIRECT_SPEECH','AUDIO_WAKE_WORD'}
result={'handsfree':{k:h.get(k) if type(h.get(k)) is bool else None for k in ('enabled','visual_bound','conversation_entered','microphone_open')},
        'state':h.get('state') if h.get('state') in choices else 'OTHER',
        'reason':h.get('reason') if h.get('reason') in choices else 'OTHER',
        'monitor_error_present':bool(h.get('error')),
        'last_stop_reason':timing.get('last_stop_reason') if timing.get('last_stop_reason') in choices else None,
        'stop_counts':{k:n for k,n in (timing.get('stop_reasons') or {}).items() if k in choices and type(n) is int},
        'transcription_state':tx.get('state') if tx.get('state') in {'IDLE','DISABLED','CANCELLED','TRANSCRIBING','GENERATING','PLAYING','ANSWERED','ERROR'} else None,
        'transcription_error_present':bool(tx.get('error'))}
db=sqlite3.connect('file:/home/root/.local/share/aura-board-business/timeline.sqlite3?mode=ro',uri=True,timeout=1,isolation_level=None)
deadline=time.monotonic()+2
try:
    db.execute('PRAGMA query_only=ON');db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000);db.execute('BEGIN')
    base='FROM (SELECT b.text FROM bm_turns t JOIN bm_bodies b ON b.event_id=t.assistant_event_id ORDER BY t.created_utc DESC LIMIT 12) q'
    counts={'recent_retained_assistant_bodies':db.execute('SELECT COUNT(*) '+base).fetchone()[0]}
    for label,prefix in {'self_candidate':'声音候选称呼是','self_progress':'已完成第','self_no_candidate':'这段声音还未形成','self_quality':'这段声音尚未通过','original_uncalibrated':'本机有声纹记录','original_saved':'声纹样本已保存'}.items():
        counts[label]=db.execute('SELECT COUNT(*) '+base+' WHERE instr(q.text,?)>0',(prefix,)).fetchone()[0]
    result['reply_category_counts']=counts;db.execute('ROLLBACK')
finally:db.close()
result.update(read_only=True,names_ids_transcripts_audio_or_reply_text_exported=False)
print(json.dumps(result))
