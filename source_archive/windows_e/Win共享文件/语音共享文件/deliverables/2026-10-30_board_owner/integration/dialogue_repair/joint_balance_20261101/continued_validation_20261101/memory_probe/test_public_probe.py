"""Small new public SQLite fixtures; no private database, HTTP or device use."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('target_metadata_probe',HERE/'read_target_memory_metadata.py')
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
CID='a'*32
FOREIGN='b'*32
SEED='authored-public-seed-request'
ANSWER='authored-public-answer-request'
SEED_HASH=M.token(SEED)
ANSWER_HASH=M.token(ANSWER)
BODY_SENTINEL='public fixture body must never be read'


def fixture(*,compacted=False,answer=False,foreign=False):
    db=sqlite3.connect(':memory:')
    db.executescript('''
        PRAGMA application_id=1096110658; PRAGMA user_version=1;
        CREATE TABLE bm_turns(turn_id TEXT PRIMARY KEY,scope_kind TEXT,scope_id TEXT,user_event_id TEXT,
            assistant_event_id TEXT,status TEXT,closed_utc REAL,created_utc REAL);
        CREATE TABLE bm_events(event_id TEXT PRIMARY KEY,source TEXT,state TEXT,revision INTEGER,
            closed_utc REAL,compacted_summary_id TEXT,scope_kind TEXT,scope_id TEXT,turn_id TEXT,
            provenance_complete INTEGER,metadata TEXT);
        CREATE TABLE bm_bodies(event_id TEXT,text TEXT);
        CREATE TABLE bm_summaries(summary_id TEXT PRIMARY KEY,scope_kind TEXT,scope_id TEXT,state TEXT,summary TEXT);
        CREATE TABLE bm_summary_sources(summary_id TEXT,event_id TEXT,revision INTEGER);
        CREATE TABLE bm_tasks(task_id TEXT,scope_kind TEXT,scope_id TEXT,status TEXT,summary_id TEXT);
        CREATE TABLE bm_task_sources(task_id TEXT,event_id TEXT);
        CREATE TABLE bm_facts(scope_kind TEXT,scope_id TEXT,fact_key TEXT,revision INTEGER,state TEXT,value TEXT);
        CREATE TABLE bm_fact_sources(scope_kind TEXT,scope_id TEXT,fact_key TEXT,revision INTEGER,event_id TEXT);
        CREATE TABLE bm_event_dependencies(event_id TEXT,source_event_id TEXT);
    ''')
    db.execute('INSERT INTO bm_turns VALUES(?,?,?,?,?,?,?,?)',(SEED,'conversation',CID,'seed-user','seed-assistant','played',100.,90.))
    for eid,kind in [('seed-user','user_said'),('seed-assistant','assistant_played')]:
        db.execute('INSERT INTO bm_events VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (eid,kind,'valid',2,100.,'summary-public' if compacted else None,'conversation',CID,SEED,1,BODY_SENTINEL))
        if not compacted:
            db.execute('INSERT INTO bm_bodies VALUES(?,?)',(eid,BODY_SENTINEL))
    if compacted:
        db.execute('INSERT INTO bm_summaries VALUES(?,?,?,?,?)',('summary-public','conversation',CID,'valid',BODY_SENTINEL))
        db.execute('INSERT INTO bm_tasks VALUES(?,?,?,?,?)',('task-public','conversation',CID,'committed','summary-public'))
        for eid in ['seed-user','seed-assistant']:
            db.execute('INSERT INTO bm_summary_sources VALUES(?,?,?)',('summary-public',eid,2))
            db.execute('INSERT INTO bm_task_sources VALUES(?,?)',('task-public',eid))
    if answer:
        owner=FOREIGN if foreign else CID
        db.execute('INSERT INTO bm_turns VALUES(?,?,?,?,?,?,?,?)',(ANSWER,'conversation',owner,'answer-user','answer-assistant','played',450.,440.))
        db.execute('INSERT INTO bm_events VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            ('answer-assistant','assistant_played','valid',2,450.,None,'conversation',owner,ANSWER,1,BODY_SENTINEL))
        db.executemany('INSERT INTO bm_event_dependencies VALUES(?,?)',[('answer-assistant','seed-user'),('answer-assistant','seed-assistant')])
    db.commit()
    forbidden_reads=[]
    forbidden_columns={'text','summary','metadata','value','keywords','claims','body_hash','input_hash'}
    def authorizer(action,table,column,database,trigger):
        if action==sqlite3.SQLITE_READ and column in forbidden_columns:
            forbidden_reads.append((table,column))
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    db.set_authorizer(authorizer)
    return db,forbidden_reads


def inspect(db,answer=None,**kwargs):
    return M.inspect_connection(db,SEED_HASH,answer,selected_conversation=kwargs.pop('selected',CID),
        clock_lower=kwargs.pop('lower',450.),clock_safe=kwargs.pop('safe',True))


class PublicMetadataTests(unittest.TestCase):
    def test_recent_body_or_failed_retained_source_cannot_pass_compaction(self):
        db,reads=fixture()
        try:
            result=inspect(db,lower=150.)
            self.assertFalse(result['target_compaction_proven'])
            self.assertTrue(all(row['body_rows']==1 for row in result['seed_events']))
            result=inspect(db,lower=1000.)
            self.assertFalse(result['target_compaction_proven'])
            self.assertTrue(all(row['eligible_age_reached'] for row in result['seed_events']))
            self.assertEqual(reads,[])
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('DELETE FROM bm_bodies')
        finally:db.close()

    def test_committed_bodyless_sources_and_answer_dependencies_are_only_metadata(self):
        db,reads=fixture(compacted=True,answer=True)
        try:
            result=inspect(db,ANSWER_HASH)
            self.assertTrue(result['target_compaction_proven'])
            self.assertTrue(result['same_scope'])
            self.assertTrue(result['answer_provenance_complete'])
            self.assertTrue(all(v['recorded_dependency'] for v in result['answer_seed_dependencies']))
            self.assertFalse(result['actual_prompt_retrieval_observed'])
            text=json.dumps(result)
            for raw in [CID,SEED,ANSWER,'seed-user','seed-assistant','summary-public',BODY_SENTINEL]:
                self.assertNotIn(raw,text)
            self.assertEqual(reads,[])
        finally:db.close()

    def test_scope_or_selection_changes_fail_closed_without_event_reads(self):
        for answer_foreign,selected in [(True,CID),(False,FOREIGN)]:
            db,reads=fixture(compacted=True,answer=True,foreign=answer_foreign)
            accessed=[]
            def authorize(action,table,column,database,trigger):
                if action==sqlite3.SQLITE_READ and table=='bm_events':
                    accessed.append(column)
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorize)
            try:
                result=inspect(db,ANSWER_HASH,selected=selected)
                self.assertNotIn('seed_events',result)
                self.assertEqual(accessed,[])
                self.assertIn('MISMATCH',result['status'])
            finally:db.close()

    def test_clock_invalid_or_uncommitted_or_missing_summary_never_passes(self):
        for alteration in ['clock','age','task','summary']:
            db,reads=fixture(compacted=True)
            db.set_authorizer(None)
            if alteration=='task':db.execute("UPDATE bm_tasks SET status='failed'")
            if alteration=='summary':db.execute("UPDATE bm_summaries SET state='invalidated'")
            db.commit()
            try:
                result=inspect(db,safe=alteration!='clock',lower=399. if alteration=='age' else 450.)
                self.assertFalse(result['target_compaction_proven'],alteration)
            finally:db.close()

    def test_latest64_bound_and_hash_input_validation(self):
        db,reads=fixture()
        try:
            with self.assertRaises(M.Refused):inspect(db,SEED_HASH)
            with self.assertRaises(M.Refused):M.inspect_connection(db,'invalid',None,selected_conversation=CID)
            db.set_authorizer(None)
            for j in range(64):
                db.execute('INSERT INTO bm_turns VALUES(?,?,?,?,?,?,?,?)',
                    ('public-new-'+str(j),'conversation',CID,'u'+str(j),None,'interrupted',200+j,200+j))
            db.commit()
            with self.assertRaises(M.Refused) as error:inspect(db)
            self.assertEqual(error.exception.code,'target_not_unique_within_latest64')
        finally:db.close()

    def test_invalid_direct_summary_pointer_cannot_borrow_another_valid_summary(self):
        db,reads=fixture(compacted=True)
        db.set_authorizer(None)
        db.execute('INSERT INTO bm_summaries VALUES(?,?,?,?,?)',
            ('direct-invalid-summary','conversation',CID,'invalidated',BODY_SENTINEL))
        db.execute("UPDATE bm_events SET compacted_summary_id='direct-invalid-summary'")
        db.execute("UPDATE bm_tasks SET summary_id='direct-invalid-summary'")
        db.executemany('INSERT INTO bm_summary_sources VALUES(?,?,?)',
            [('direct-invalid-summary','seed-user',2),('direct-invalid-summary','seed-assistant',2)])
        db.commit()
        try:
            # An unrelated valid summary for the same event/revision still exists.
            self.assertEqual(db.execute("SELECT COUNT(*) FROM bm_summary_sources ss JOIN bm_summaries s USING(summary_id) "
                "WHERE ss.event_id='seed-user' AND ss.revision=2 AND s.state='valid'").fetchone()[0],1)
            result=inspect(db)
            self.assertFalse(result['target_compaction_proven'])
            self.assertTrue(all(row['valid_summary_link_count']==0 for row in result['seed_events']))
            self.assertTrue(all(row['committed_task_count']==1 for row in result['seed_events']))
        finally:db.close()


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PublicMetadataTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(schema='aura.target-memory-probe-public-tests.v1',tests=result.testsRun,failures=len(result.failures),
        errors=len(result.errors),passed=result.wasSuccessful(),only_authored_inmemory_sqlite=True,
        actual_HTTP_model_device_private_database_access=False)
    (HERE/'PUBLIC_TEST_RESULT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)
