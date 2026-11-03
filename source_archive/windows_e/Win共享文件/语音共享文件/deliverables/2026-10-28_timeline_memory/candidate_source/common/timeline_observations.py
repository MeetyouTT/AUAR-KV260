"""Bounded cross-boot observations for one explicitly configured wired device.

The original 24-hour live cache remains separate from the 30-day event history.
No images, personal identities or inferred actions are stored.
"""
import json,math,re,sqlite3,time
from common.device_memory import ObservationStore
from common.timeline import event_id,select,sql_topic

class TimelineObservationStore(ObservationStore):
    def __init__(self,path,*,device_id,clock=time.time,history_days=30,history_limit=10000,**kwargs):
        if not re.fullmatch('[a-zA-Z0-9_-]{1,64}',device_id):raise ValueError('Invalid configured device')
        if type(history_days) is not int or not 1<=history_days<=366:raise ValueError('Invalid retention')
        if type(history_limit) is not int or not 1<=history_limit<=50000:raise ValueError('Invalid history cap')
        self.device_id=device_id;self.history_retention=history_days*86400;self.history_limit=history_limit
        super().__init__(path,clock=clock,**kwargs)
        with self.lock,self.db:
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS visual_timeline (
                    id TEXT PRIMARY KEY,device TEXT NOT NULL,boot TEXT NOT NULL,epoch TEXT NOT NULL,
                    first_frame INTEGER NOT NULL,last_frame INTEGER NOT NULL,
                    first_received REAL NOT NULL,last_received REAL NOT NULL,
                    samples INTEGER NOT NULL,summary TEXT NOT NULL,frame_meta TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS visual_timeline_time ON visual_timeline(device,last_received);
                CREATE TABLE IF NOT EXISTS visual_timeline_revision(device TEXT PRIMARY KEY,revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS visual_timeline_cursor(
                    device TEXT NOT NULL,boot TEXT NOT NULL,epoch TEXT NOT NULL,last_frame INTEGER NOT NULL,
                    received REAL NOT NULL,PRIMARY KEY(device,boot,epoch));
            ''')
            self.db.execute('INSERT OR IGNORE INTO visual_timeline_revision VALUES(?,0)',(device_id,))
            self._prune_timeline()

    def generation(self,boot):
        with self.lock:
            return self.db.execute('SELECT revision FROM visual_timeline_revision WHERE device=?',(self.device_id,)).fetchone()[0]

    def add(self,frame,summary,received,*,generation=None):
        now=self.clock()
        if not isinstance(summary,str) or not 1<=len(summary)<=240 or '\x00' in summary:raise ValueError('Invalid visual summary')
        if not isinstance(received,(int,float)) or not math.isfinite(received) or not 0<=now-received<=20:raise ValueError('Observation expired before storage')
        boot,epoch,number=frame['board_boot_id'],frame['camera_epoch'],frame['frame_id']
        if any(not isinstance(v,str) or not 1<=len(v)<=64 for v in (boot,epoch)) or type(number) is not int or number<0:
            raise ValueError('Invalid observation identity')
        # Source monotonic values are provenance, never calendar timestamps.
        source={k:frame[k] for k in ('captured_mono_ms','observed_mono_ms') if k in frame}
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in source.values()):raise ValueError('Invalid source time')
        with self.lock,self.db:
            if generation is not None and generation!=self.generation(boot):return False
            cursor=self.db.execute('SELECT last_frame FROM visual_timeline_cursor WHERE device=? AND boot=? AND epoch=?',
                                   (self.device_id,boot,epoch)).fetchone()
            if cursor and number<=cursor[0]:return False
            self.db.execute('INSERT OR IGNORE INTO observations(boot,epoch,frame,received,summary) VALUES(?,?,?,?,?)',
                            (boot,epoch,number,received,summary))
            self.db.execute('INSERT OR REPLACE INTO visual_timeline_cursor VALUES(?,?,?,?,?)',(self.device_id,boot,epoch,number,received))
            previous=self.db.execute('SELECT id,boot,epoch,first_received,last_received,summary FROM visual_timeline WHERE device=? ORDER BY last_received DESC LIMIT 1',
                                     (self.device_id,)).fetchone()
            if (previous and previous[1:3]==(boot,epoch) and previous[5]==summary
                and 0<=received-previous[4]<=30 and received-previous[3]<=300):
                self.db.execute('UPDATE visual_timeline SET last_frame=?,last_received=?,samples=samples+1,frame_meta=? WHERE id=?',
                                (number,received,json.dumps(source),previous[0]))
            else:
                key=event_id('visual',json.dumps([self.device_id,boot,epoch,number]))
                self.db.execute('INSERT INTO visual_timeline VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    (key,self.device_id,boot,epoch,number,number,received,received,1,summary,json.dumps(source)))
            self._prune();self._prune_timeline()
        return True

    def _prune_timeline(self):
        self.db.execute('DELETE FROM visual_timeline WHERE device=? AND last_received<?',(self.device_id,self.clock()-self.history_retention))
        self.db.execute('DELETE FROM visual_timeline WHERE device=? AND id NOT IN (SELECT id FROM visual_timeline WHERE device=? ORDER BY last_received DESC LIMIT ?)',
                        (self.device_id,self.device_id,self.history_limit))
        self.db.execute('DELETE FROM visual_timeline_cursor WHERE device=? AND received<?',(self.device_id,self.clock()-self.history_retention))
        self.db.execute('DELETE FROM visual_timeline_cursor WHERE device=? AND rowid NOT IN (SELECT rowid FROM visual_timeline_cursor WHERE device=? ORDER BY received DESC LIMIT 256)',
                        (self.device_id,self.device_id))

    def timeline_events(self,q,*,limit=8):
        if not 1<=limit<=12:raise ValueError('Invalid timeline bound')
        if not self.lock.acquire(timeout=.03):raise TimeoutError('Observation store busy')
        try:
            deadline=time.monotonic()+.08
            self.db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
            with self.db:self._prune_timeline()
            where='device=? AND first_received<=? AND last_received>=?'
            values=[self.device_id,q['end'],max(q['start'] or 0,self.clock()-self.history_retention)]
            topic_sql,topic_values=sql_topic(['summary'],q['topic']);where+=topic_sql;values+=topic_values
            records=self.db.execute('SELECT * FROM visual_timeline WHERE '+where+' ORDER BY last_received DESC LIMIT 500',values).fetchall()
            out=[dict(event_id=r[0],source='camera_observed',scope='configured_device',boot=r[2],camera_epoch=r[3],
                      first_frame=r[4],last_frame=r[5],start_utc=r[6],end_utc=r[7],observation_count=r[8],text=r[9],
                      time_basis='host_received',current=False,identity_verified=False,
                      continuity='sampled_not_continuous') for r in records]
            return select(out,q,limit=limit)
        finally:
            self.db.set_progress_handler(None,0);self.lock.release()

    def forget(self,boot):
        with self.lock,self.db:
            self.db.execute('UPDATE visual_timeline_revision SET revision=revision+1 WHERE device=?',(self.device_id,))
            self.db.execute('DELETE FROM observations WHERE boot=?',(boot,))
            self.db.execute('DELETE FROM visual_timeline WHERE device=? AND boot=?',(self.device_id,boot))

    def forget_timeline(self,q):
        from common.timeline import tokens
        if q.get('error'):raise ValueError(q['error'])
        with self.lock,self.db:
            self.db.execute('UPDATE visual_timeline_revision SET revision=revision+1 WHERE device=?',(self.device_id,))
            rows=self.db.execute('SELECT id,boot,epoch,first_received,last_received,summary FROM visual_timeline WHERE device=?',(self.device_id,)).fetchall()
            wanted=tokens(q['topic']);selected=[]
            all_range=q['start'] is None and not q['topic']
            for row in rows:
                if not all_range and (row[3]>q['end'] or q['start'] is not None and row[4]<q['start']):continue
                if wanted and not wanted & tokens(row[5]):continue
                selected.append(row)
            # Removing a compressed event removes its entire short source span.
            for row in selected:
                self.db.execute('DELETE FROM observations WHERE boot=? AND epoch=? AND received>=? AND received<=?',row[1:5])
                self.db.execute('DELETE FROM visual_timeline WHERE id=?',(row[0],))
            # The pre-upgrade live cache has no event projections; explicit range
            # deletion must remove those sources too, rather than expose them later.
            if not wanted:
                if all_range:self.db.execute('DELETE FROM observations')
                else:self.db.execute('DELETE FROM observations WHERE received>=? AND received<?',(q['start'] or 0,q['end']))
            return len(selected)

    def timeline_health(self):
        return {'version':1,'retention_seconds':self.history_retention,'event_limit':self.history_limit,
                'cross_boot':True,'device_binding':'operator_configured_wired_endpoint',
                'calendar_source':'host_received_utc','raw_images':False,'identity_inference':False}
