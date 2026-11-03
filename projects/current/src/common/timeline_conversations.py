"""A time index over the authoritative conversation archive, without text copies."""
import json,sqlite3,time
from common.profile_memory import ProfileConversationStore
from common.timeline import event_id,select,sql_topic
from common.memory_controls import MemoryControlsMixin,install as install_controls,resolve_digest_sources

class TimelineConversationStore(MemoryControlsMixin,ProfileConversationStore):
    def __init__(self,path):
        super().__init__(path)
        with self.lock,self._connect() as db:
            db.executescript('''
                CREATE INDEX IF NOT EXISTS turns_timeline ON turns(conversation_id,created,seq);
                CREATE TABLE IF NOT EXISTS timeline_played (
                    seq INTEGER PRIMARY KEY REFERENCES turns(seq) ON DELETE CASCADE,
                    received REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS timeline_visual_dependency (
                    seq INTEGER PRIMARY KEY REFERENCES turns(seq) ON DELETE CASCADE,
                    revision INTEGER NOT NULL);
            ''')
            from common.timeline_summaries import install
            install(db)
            install_controls(db)
        self.digest_worker=None

    def start_summaries(self,*,zone='America/Los_Angeles',interval=3.):
        from common.timeline_summaries import DigestWorker
        self.memory_zone=zone
        if self.digest_worker is None:
            self.digest_worker=DigestWorker(self.path,self._digest_sources,zone=zone,interval=interval)
        self.digest_worker.start()

    def _digest_sources(self,db,owner,cutoff,now,maximum):
        cid=owner[2:]
        records=db.execute('SELECT t.*,p.received AS played_at,d.revision AS visual_revision FROM turns t '
            'LEFT JOIN timeline_played p ON p.seq=t.seq LEFT JOIN timeline_visual_dependency d ON d.seq=t.seq '
            'WHERE t.conversation_id=? AND t.seq NOT IN (SELECT seq FROM recall_exclusions) '
            'AND (t.created>=? OR p.received>=?) AND t.created<=? ORDER BY t.created DESC,t.seq DESC LIMIT ?',
            (cid,cutoff,cutoff,now,maximum)).fetchall()
        def normalized():
            for row in self._events(records):
                if cutoff<=row['end_utc']<=now:yield row
        return normalized()

    @staticmethod
    def _events(records):
        out=[]
        for r in records:
            meta=json.loads(r['context'])
            base={'source_seq':r['seq'],'conversation_id':r['conversation_id'],'scope':'conversation','boot':meta.get('board_boot_id'),
                  'identity_verified':False,'current':False,'visual_revision':r['visual_revision']}
            out.append(dict(base,event_id=event_id('user',r['request_id']),source='user_said',text=r['user'],
                            start_utc=r['created'],end_utc=r['created'],time_basis='host_received'))
            if r['status']=='played' and r['assistant']:
                at=r['played_at'] if r['played_at'] is not None else r['created']
                out.append(dict(base,event_id=event_id('assistant',r['request_id']),source='assistant_played',text=r['assistant'],
                    start_utc=at,end_utc=at,time_basis='host_playback_ack' if r['played_at'] is not None else 'legacy_turn_received_playback_time_unknown'))
        return out

    def summary_events(self,cid,q,*,profile=None,exclude=None,kind='day',limit=6):
        from common.timeline_summaries import read
        if not self.lock.acquire(timeout=.03):raise TimeoutError('Summary busy')
        try:
            with self._connect() as db:
                deadline=time.monotonic()+.06;db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
                db.execute('BEGIN');self._scope(db,cid,profile)
                owners=['c:'+cid] if profile is None else ['c:'+r[0] for r in db.execute(
                    'SELECT conversation_id FROM conversation_profiles WHERE profile_id=? LIMIT 2000',(profile,))]
                rows=read(db,owners,q,kind=kind,exclude_event_ids=[event_id('user',exclude or ''),event_id('assistant',exclude or '')],limit=limit)
                for row in rows:row['scope']='authorized_profile' if profile else 'conversation'
                return resolve_digest_sources(db,rows)
        finally:self.lock.release()

    def attach_visual(self,meta,revision):
        if type(revision) is not int or revision<0:raise ValueError('Invalid visual revision')
        with self.lock,self._connect() as db:
            self._current_revision(db,meta)
            row=db.execute('SELECT seq FROM turns WHERE request_id=? AND context=?',
                           (meta['request_id'],self._owner(meta))).fetchone()
            db.execute('INSERT OR REPLACE INTO timeline_visual_dependency VALUES(?,?)',(row[0],revision))

    def has_visual_dependencies(self):
        with self.lock,self._connect() as db:
            return db.execute('SELECT 1 FROM timeline_visual_dependency WHERE seq NOT IN '
                              '(SELECT seq FROM recall_exclusions) LIMIT 1').fetchone() is not None

    def invalidate_visual(self,revision):
        """Fail closed on unavailable provenance; no deleted text in tombstones."""
        if revision is not None and (type(revision) is not int or revision<0):raise ValueError('Invalid visual revision')
        with self.lock,self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute('SELECT t.seq,t.conversation_id FROM turns t JOIN timeline_visual_dependency v ON v.seq=t.seq '
                'WHERE t.seq NOT IN (SELECT seq FROM recall_exclusions) AND (? IS NULL OR v.revision!=?)',
                (revision,revision)).fetchall()
            db.executemany('INSERT INTO recall_exclusions VALUES(?,?)',[(r[0],'visual_source_invalidated') for r in rows])
            for cid in {r[1] for r in rows}:
                db.execute('UPDATE conversations SET revision=revision+1,memory_revision=memory_revision+1 WHERE id=?',(cid,))
            return len(rows)

    def visual_revision_for_records(self,records):
        revisions=set()
        with self.lock,self._connect() as db:
            for offset in range(0,len(records),400):
                ids=[r['seq'] for r in records[offset:offset+400]]
                if ids:
                    revisions.update(r[0] for r in db.execute('SELECT revision FROM timeline_visual_dependency WHERE seq IN ('+
                                     ','.join('?' for _ in ids)+')',ids))
        if len(revisions)>1:raise ValueError('Mixed obsolete visual revisions')
        return next(iter(revisions)) if revisions else None

    def played(self,meta,samples,digest):
        # Same transaction and revision check as the original ACK contract.
        with self.lock,self._connect() as db:
            row=db.execute('SELECT * FROM turns WHERE request_id=?',(meta['request_id'],)).fetchone()
            if (not row or row['context']!=self._owner(meta) or row['samples']!=samples
                or row['digest']!=digest or row['status'] not in ('generated','played')):
                raise ValueError('Invalid durable playback acknowledgement')
            self._current_revision(db,meta)
            if row['status']=='played':return False
            db.execute("UPDATE turns SET status='played' WHERE request_id=?",(meta['request_id'],))
            db.execute('INSERT INTO timeline_played VALUES(?,?)',(row['seq'],time.time()))
            db.execute('UPDATE conversations SET revision=revision+1 WHERE id=?',(row['conversation_id'],))
            return True

    def timeline_events(self,cid,q,*,profile=None,exclude=None,limit=8):
        if not 1<=limit<=12:raise ValueError('Invalid timeline bound')
        if not self.lock.acquire(timeout=.03):raise TimeoutError('Timeline busy')
        db=None
        try:
            db=sqlite3.connect(str(self.path),timeout=.03);db.row_factory=sqlite3.Row
            deadline=time.monotonic()+.08
            db.set_progress_handler(lambda:int(time.monotonic()>deadline),2000)
            db.execute('BEGIN');self._scope(db,cid,profile)
            if q.get('error'):return []
            scope=('t.conversation_id=?',[cid]) if profile is None else (
                't.conversation_id IN (SELECT conversation_id FROM conversation_profiles WHERE profile_id=?)',[profile])
            where='t.seq NOT IN (SELECT seq FROM recall_exclusions) AND t.request_id!=? AND '+scope[0]
            values=[exclude or '']+scope[1]
            # Include a turn if either its input or played reply is in range.
            where+=' AND t.created<=?';values.append(q['end'])
            if q['start'] is not None:
                where+=' AND (t.created>=? OR p.received>=?)';values.extend([q['start'],q['start']])
            topic_sql,topic_values=sql_topic(['t.user',"CASE WHEN t.status='played' THEN t.assistant ELSE '' END"],q['topic'])
            where+=topic_sql;values+=topic_values
            records=db.execute('SELECT t.*,p.received AS played_at,d.revision AS visual_revision FROM turns t '
                               'LEFT JOIN timeline_played p ON p.seq=t.seq LEFT JOIN timeline_visual_dependency d ON d.seq=t.seq WHERE '+
                               where+' ORDER BY t.created DESC,t.seq DESC LIMIT 500',values).fetchall()
            out=self._events(records)
            for row in out:row['scope']='authorized_profile' if profile else 'conversation'
            return select(out,q,limit=limit)
        finally:
            if db is not None:db.close()
            self.lock.release()

    def health(self):
        return dict(super().health(),timeline_version=1,timeline_scope='authorized_profile_or_exact_conversation',
                    timeline_source='authoritative_archive',timeline_playback_time=True,
                    fact_revision_history=1,confirmed_transcript_deletion=1,conversation_source_dependencies=1,
                    background_summaries=self.digest_worker.health() if self.digest_worker else {'version':0})
