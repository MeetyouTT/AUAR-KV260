"""Count fixed word/grammar shapes in recent retained user text, board RAM only."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='44e8f154c9dd72d3b7619160f7a2dac64fda529daba91a96a196c12f68c8a295'
startup=json.loads(raw);aura=Path(startup['runtime'])/'aura'
for key in ('common/feature_intents.py','board/runtime/board_speaker_business.py','common/board_memory.py'):
    assert hashlib.sha256((aura/key).read_bytes()).hexdigest()==startup['component_sha256'][key]
sys.path.insert(0,str(aura))
from common.feature_intents import speaker_query_requested
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from common.board_memory import APPLICATION_ID
db_path=Path('/home/root/.local/share/aura-board-business/timeline.sqlite3')
assert db_path.is_file() and not db_path.is_symlink()
db=sqlite3.connect(db_path.as_uri()+'?mode=ro',uri=True,timeout=1,isolation_level=None)
deadline=time.monotonic()+2
try:
    db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
    db.execute('PRAGMA query_only=ON')
    assert db.execute('PRAGMA application_id').fetchone()==(APPLICATION_ID,)
    fixed={'has_voice':'声音','has_voiceprint':'声纹','has辨认':'辨认','has分辨':'分辨','has辨别':'辨别','has识别':'识别','has认出':'认出','has判断':'判断','has根据':'根据','has依据':'依据','has通过':'通过','has从':'从','has听出':'听出','has知道':'知道','has是谁':'是谁','has谁在说话':'谁在说话','has你可以':'你可以','has你能不能':'你能不能','has请问':'请问','has我的':'我的'}
    def shape(text,label):
        if type(text) is not str:return 0
        if label=='original_speaker_query':return int(speaker_query_requested(text))
        if label=='explicit_self_match':return int(BoardSpeakerBusiness._explicit_self_match(text))
        return int(fixed[label] in text)
    db.create_function('fixed_shape',2,shape)
    db.execute('BEGIN')
    base='FROM (SELECT b.text FROM bm_turns t JOIN bm_bodies b ON b.event_id=t.user_event_id ORDER BY t.created_utc DESC LIMIT 12) q'
    out={'recent_retained_user_texts':db.execute('SELECT COUNT(*) '+base).fetchone()[0]}
    for label in list(fixed)+['original_speaker_query','explicit_self_match']:
        out[label]=db.execute('SELECT COUNT(*) '+base+' WHERE fixed_shape(q.text,?)=1',(label,)).fetchone()[0]
    db.execute('ROLLBACK')
finally:db.close()
print(json.dumps(dict(counts=out,scope='latest twelve retained user bodies; no specific utterance or identity exported',raw_text_or_names_ids_audio_exported=False,read_only=True,model_or_project_store_constructed=False)))
