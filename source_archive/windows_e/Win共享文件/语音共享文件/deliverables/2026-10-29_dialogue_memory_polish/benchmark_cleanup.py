"""WMI-only maintenance for one exact public benchmark conversation."""
import argparse,json,sqlite3,time
from pathlib import Path
H=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--action',choices=['trim','all'],required=True);args=p.parse_args()
report={'status':'STARTING'}
try:
    exp=json.loads((H/'experiment.json').read_text(encoding='utf-8'));cid=exp['cid']
    attempts={r['context']['request_id']:r['context'] for r in exp['attempts']}
    base=exp['base_context']['request_id']
    with sqlite3.connect(str(H.parent/'2026-10-18_board_dialogue/model_host/conversations.sqlite3')) as db:
        db.execute('PRAGMA foreign_keys=ON');db.execute('BEGIN IMMEDIATE')
        assert not db.execute('SELECT 1 FROM conversation_profiles WHERE conversation_id=?',(cid,)).fetchone()
        rows=db.execute('SELECT seq,request_id,context FROM turns WHERE conversation_id=?',(cid,)).fetchall()
        for seq,request,context in rows:assert request in attempts and json.loads(context)==attempts[request]
        chosen=[r for r in rows if args.action=='all' or r[1]!=base]
        if args.action=='all':db.execute('DELETE FROM conversation_facts WHERE conversation_id=?',(cid,))
        for seq,request,context in chosen:
            db.execute('DELETE FROM recall_exclusions WHERE seq=?',(seq,));db.execute('DELETE FROM turns WHERE seq=?',(seq,))
        if args.action=='trim':
            remaining=db.execute('SELECT request_id FROM turns WHERE conversation_id=?',(cid,)).fetchall()
            assert remaining==[(base,)]
            facts=db.execute('SELECT key,value FROM conversation_facts WHERE conversation_id=?',(cid,)).fetchall()
            assert facts==[('颜色偏好','绿色')]
        else:
            db.execute('DELETE FROM conversations WHERE id=?',(cid,))
            db.execute('DELETE FROM memory_delete_previews WHERE owner=?',(exp['delete_owner'],))
            assert not db.execute('SELECT 1 FROM memory_fact_versions WHERE owner=?',('c:'+cid,)).fetchone()
        owner='c:'+cid;db.execute('DELETE FROM timeline_digests WHERE owner=?',(owner,))
        revision=db.execute('SELECT revision FROM timeline_digest_revisions WHERE owner=?',(owner,)).fetchone()
        if revision:db.execute('INSERT OR REPLACE INTO timeline_digest_builds VALUES(?,?,?)',(owner,revision[0],time.time()))
    report={'status':'PASS','action':args.action,'removed_only_public_attempts':True,'rows_removed':len(chosen)}
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/('cleanup_'+args.job+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')

