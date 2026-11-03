"""Independent WMI cleanup: only the public acceptance's exact new conversation."""
import hashlib,json,sqlite3,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from common.memory_controls import MemoryControlsMixin
report={'status':'STARTING'}
try:
    probe=json.loads((H/'live_controls_acceptance.json').read_text(encoding='utf-8'))
    cid=probe['conversation_id'];attempts={r['context']['request_id']:r for r in probe['turns']}
    path=H.parent/'2026-10-18_board_dialogue/model_host/conversations.sqlite3'
    with sqlite3.connect(str(path)) as db:
        db.execute('PRAGMA foreign_keys=ON');db.execute('BEGIN IMMEDIATE')
        assert not db.execute('SELECT 1 FROM conversation_profiles WHERE conversation_id=?',(cid,)).fetchone()
        rows=db.execute('SELECT seq,request_id,context FROM turns WHERE conversation_id=?',(cid,)).fetchall()
        assert rows and len(rows)<=len(attempts)
        for seq,request,context in rows:assert request in attempts and json.loads(context)==attempts[request]['context'],'Unexpected test conversation row'
        db.execute('DELETE FROM conversation_facts WHERE conversation_id=?',(cid,))
        for seq,request,context in rows:
            db.execute('DELETE FROM recall_exclusions WHERE seq=?',(seq,))
            db.execute('DELETE FROM turns WHERE seq=?',(seq,))
        db.execute('DELETE FROM conversations WHERE id=?',(cid,))
        owner='c:'+cid
        db.execute('DELETE FROM timeline_digests WHERE owner=?',(owner,))
        revision=db.execute('SELECT revision FROM timeline_digest_revisions WHERE owner=?',(owner,)).fetchone()
        if revision:db.execute('INSERT OR REPLACE INTO timeline_digest_builds VALUES(?,?,?)',(owner,revision[0],probe['started_unix']))
        control_owner=MemoryControlsMixin._delete_owner(probe['turns'][0]['context'],cid,None)
        db.execute('DELETE FROM memory_delete_previews WHERE owner=?',(control_owner,))
        assert not db.execute('SELECT 1 FROM memory_fact_versions WHERE owner=?',(owner,)).fetchone()
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    report={'status':'PASS','only_public_test_conversation_removed':True,'remaining_test_rows':0,'private_view':'independent_WMI'}
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'public_probe_cleanup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

