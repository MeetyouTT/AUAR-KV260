"""Background extractive digests, transactionally invalidated by their sources.

Caches live beside their authoritative data. They never become personal facts.
All triggers use built-in SQLite operations, so old code can still write after
a code rollback. No model, network, media capture or identity inference is used.
"""
from datetime import datetime,timedelta
from contextlib import contextmanager
import hashlib,json,sqlite3,threading,time
from zoneinfo import ZoneInfo

LABELS={'user_said':'用户原话','assistant_played':'已播回复','camera_observed':'相机观察'}

def summary_mode(text):
    if any(word in text for word in ('总结','回顾','概括','日记','一天都','当天都')):return 'day'
    if any(word in text for word in ('这段','那段','聊到哪里')):return 'episode'
    return None

def install(db,*,visual_device=None):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS timeline_digests(
            owner TEXT NOT NULL,id TEXT NOT NULL,kind TEXT NOT NULL,day TEXT NOT NULL,
            bucket_start REAL NOT NULL,bucket_end REAL NOT NULL,start_utc REAL NOT NULL,end_utc REAL NOT NULL,
            text TEXT NOT NULL,sources TEXT NOT NULL,source_count INTEGER NOT NULL,limited INTEGER NOT NULL,
            visual_revision INTEGER,computed REAL NOT NULL,PRIMARY KEY(owner,id));
        CREATE INDEX IF NOT EXISTS timeline_digest_range ON timeline_digests(owner,kind,bucket_start,bucket_end);
        CREATE INDEX IF NOT EXISTS timeline_digest_computed ON timeline_digests(computed);
        CREATE TABLE IF NOT EXISTS timeline_digest_revisions(owner TEXT PRIMARY KEY,revision INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS timeline_digest_builds(owner TEXT PRIMARY KEY,revision INTEGER NOT NULL,computed REAL NOT NULL);
    ''')
    def bump(owner):
        return ('INSERT OR IGNORE INTO timeline_digest_revisions VALUES('+owner+',0);'
                'UPDATE timeline_digest_revisions SET revision=revision+1 WHERE owner='+owner+';')
    def purge(owner,predicate='1'):
        return 'DELETE FROM timeline_digests WHERE owner='+owner+' AND ('+predicate+');'
    def point(value):return '(bucket_start<='+value+' AND bucket_end>'+value+')'
    def trigger(name,when,body):db.executescript('CREATE TRIGGER IF NOT EXISTS '+name+' '+when+' BEGIN '+body+' END;')
    if visual_device is not None:
        # The operator config validates this before reaching the SQL literal.
        import re
        if not re.fullmatch('[a-zA-Z0-9_-]{1,64}',visual_device):raise ValueError('Invalid digest device')
        db.execute('INSERT OR IGNORE INTO timeline_digest_revisions VALUES(?,0)',('v:'+visual_device,));db.commit()
        def overlap(prefix):return '(bucket_start<='+prefix+'.last_received AND bucket_end>'+prefix+'.first_received)'
        for operation,predicate in [('INSERT',overlap('NEW')),('UPDATE',overlap('OLD')+' OR '+overlap('NEW')),('DELETE',overlap('OLD'))]:
            owner="'v:'||"+('OLD.device' if operation=='DELETE' else 'NEW.device')
            body=bump(owner)+purge(owner,predicate)
            if operation=='UPDATE':body=bump("'v:'||OLD.device")+purge("'v:'||OLD.device",predicate)+body
            trigger('td_visual_'+operation.lower(),'AFTER '+operation+' ON visual_timeline',body)
    else:
        db.execute("INSERT OR IGNORE INTO timeline_digest_revisions SELECT 'c:'||id,0 FROM conversations");db.commit()
        owner="'c:'||NEW.conversation_id";old_owner="'c:'||OLD.conversation_id"
        trigger('td_turn_insert','AFTER INSERT ON turns',bump(owner)+purge(owner,point('NEW.created')))
        trigger('td_turn_update','AFTER UPDATE OF user,assistant,status,created ON turns',
                bump(old_owner)+bump(owner)+purge(old_owner,point('OLD.created'))+purge(owner,point('NEW.created')))
        trigger('td_turn_delete','BEFORE DELETE ON turns',bump(old_owner)+purge(old_owner))
        seq_owner="(SELECT 'c:'||conversation_id FROM turns WHERE seq=NEW.seq)"
        trigger('td_exclusion','AFTER INSERT ON recall_exclusions',bump(seq_owner)+purge(seq_owner))
        for operation in ('INSERT','UPDATE'):
            trigger('td_visual_dependency_'+operation.lower(),'AFTER '+operation+' ON timeline_visual_dependency',bump(seq_owner)+purge(seq_owner))
        dependency_owner="(SELECT 'c:'||conversation_id FROM turns WHERE seq=OLD.seq)"
        trigger('td_visual_dependency_delete','BEFORE DELETE ON timeline_visual_dependency',bump(dependency_owner)+purge(dependency_owner))
        # Both transcript date and actual completed-playback date can contribute.
        trigger('td_played_insert','AFTER INSERT ON timeline_played',bump(seq_owner)+purge(seq_owner,point('NEW.received')))
        trigger('td_played_update','AFTER UPDATE ON timeline_played',bump(seq_owner)+purge(seq_owner))
        seq_old_owner="(SELECT 'c:'||conversation_id FROM turns WHERE seq=OLD.seq)"
        trigger('td_played_delete','BEFORE DELETE ON timeline_played',bump(seq_old_owner)+purge(seq_old_owner))

def _digest(owner,kind,day,rows,start,end,limited,now):
    # Keep a mix of first/last observations and distinct original statements.
    ordered=sorted(rows,key=lambda r:(r['start_utc'],r['event_id']))
    candidates=[];seen=set()
    for r in ordered[-2:]+ordered[:2]+list(reversed(ordered)):
        key=(r['source'],r['text'])
        if key not in seen:candidates.append(r);seen.add(key)
        if len(candidates)>=8:break
    chosen=[];pieces=[];characters=0
    for row in sorted(candidates,key=lambda r:(r['start_utc'],r['event_id'])):
        excerpt=row['text'][:80]
        if len(row['text'])>80:excerpt+='…（摘录）'
        part=LABELS.get(row['source'],row['source'])+'：'+excerpt
        if characters+len(part)>460:continue
        chosen.append(row);pieces.append(part);characters+=len(part)+1
    revisions={r['visual_revision'] for r in rows if r.get('visual_revision') is not None}
    if not chosen or len(revisions)>1:return None
    key=owner+'|'+kind+'|'+day+'|'+ordered[0]['event_id']
    return (owner,'digest:'+hashlib.sha256(key.encode()).hexdigest()[:32],kind,day,start,end,
            min(r['start_utc'] for r in rows),max(r['end_utc'] for r in rows),'；'.join(pieces),
            json.dumps([r['event_id'] for r in chosen]),len(rows),int(limited),
            next(iter(revisions)) if revisions else None,now)

def build(owner,events,*,zone,now,limited=False,cap=256):
    tz=ZoneInfo(zone);days={}
    for row in events:
        if row['start_utc']>now or not row['text']:continue
        day=datetime.fromtimestamp(row['start_utc'],tz).date()
        last=datetime.fromtimestamp(min(now,row['end_utc']),tz).date()
        # Sources are points or <=5 minute sampled spans. Bound corrupt archives.
        if (last-day).days>1:continue
        while day<=last:
            days.setdefault(day,[]).append(row);day+=timedelta(days=1)
    result=[]
    for day,rows in sorted(days.items()):
        boundary=datetime.combine(day,datetime.min.time(),tz)
        start,end=boundary.timestamp(),(boundary+timedelta(days=1)).timestamp()
        row=_digest(owner,'day',day.isoformat(),rows,start,end,limited,now)
        if row:result.append(row)
        episodes=[]
        for event in sorted(rows,key=lambda r:(r['start_utc'],r['event_id'])):
            scope=(event.get('boot'),event.get('camera_epoch')) if event['source']=='camera_observed' else event.get('conversation_id')
            if (not episodes or episodes[-1][0]!=scope or event['start_utc']-episodes[-1][2]>300):
                episodes.append([scope,[event],event['end_utc']])
            else:episodes[-1][1].append(event);episodes[-1][2]=max(episodes[-1][2],event['end_utc'])
        for _,sources,_ in episodes:
            row=_digest(owner,'episode',day.isoformat(),sources,start,end,limited,now)
            if row:result.append(row)
    # Prefer day digests when many tiny episodes consume the capacity.
    days=[r for r in result if r[2]=='day'][-31:]
    episodes=sorted((r for r in result if r[2]=='episode'),key=lambda r:r[7],reverse=True)[:max(0,cap-len(days))]
    return days+episodes

class DigestWorker:
    def __init__(self,path,loader,*,zone,clock=time.time,retention_days=30,source_limit=10000,interval=3.,owner=None,cache_limit=4096):
        self.path=str(path);self.loader=loader;self.zone=zone;self.clock=clock
        self.retention=retention_days*86400;self.source_limit=source_limit;self.interval=interval
        self.owner=owner
        self.cache_limit=cache_limit
        self.stop=threading.Event();self.thread=None;self.completed=0;self.discarded=0;self.error='';self.pending=0
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=.03);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()
    def prepare(self,owner):
        now=self.clock()
        with self.connect() as db:
            deadline=time.monotonic()+.12;db.set_progress_handler(lambda:int(time.monotonic()>deadline),2000)
            db.execute('BEGIN')
            revision=db.execute('SELECT revision FROM timeline_digest_revisions WHERE owner=?',(owner,)).fetchone()
            if revision is None:return None
            events=self.loader(db,owner,now-self.retention,now,self.source_limit+1)
        # The loaders snapshot rows first and normalize lazily. Release SQLite's
        # read transaction before JSON decoding, clipping and grouping sources.
        events=list(events)
        limited=len(events)>self.source_limit
        events=sorted(events,key=lambda r:(r['start_utc'],r['event_id']))[-self.source_limit:]
        return revision[0],build(owner,events,zone=self.zone,now=now,limited=limited),now
    def commit(self,owner,prepared):
        revision,rows,computed=prepared
        with self.connect() as db:
            deadline=time.monotonic()+.08;db.set_progress_handler(lambda:int(time.monotonic()>deadline),2000)
            db.execute('BEGIN IMMEDIATE')
            actual=db.execute('SELECT revision FROM timeline_digest_revisions WHERE owner=?',(owner,)).fetchone()
            if actual is None or actual[0]!=revision:self.discarded+=1;return False
            db.execute('DELETE FROM timeline_digests WHERE owner=?',(owner,))
            db.executemany('INSERT INTO timeline_digests VALUES('+','.join('?' for _ in range(14))+')',rows)
            if self.owner is None:
                db.execute('DELETE FROM timeline_digests WHERE rowid NOT IN '
                           '(SELECT rowid FROM timeline_digests ORDER BY computed DESC,rowid DESC LIMIT ?)',(self.cache_limit,))
            db.execute('INSERT OR REPLACE INTO timeline_digest_builds VALUES(?,?,?)',(owner,revision,computed))
        self.completed+=1;return True
    def step(self,max_owners=8):
        with self.connect() as db:
            dirty=db.execute('SELECT r.owner FROM timeline_digest_revisions r LEFT JOIN timeline_digest_builds b ON b.owner=r.owner '
                'WHERE (b.revision IS NULL OR b.revision!=r.revision) AND (? IS NULL OR r.owner=?) ORDER BY coalesce(b.computed,0) LIMIT ?',
                (self.owner,self.owner,max_owners+1)).fetchall()
            # Cache retention does not lengthen the authoritative source lifetime.
            db.execute('DELETE FROM timeline_digests WHERE bucket_end<? AND (? IS NULL OR owner=?)',
                       (self.clock()-self.retention,self.owner,self.owner))
        self.pending=len(dirty)
        for row in dirty[:max_owners]:
            if self.stop.is_set():break
            prepared=self.prepare(row[0])
            if prepared:self.commit(row[0],prepared)
        return min(len(dirty),max_owners)
    def start(self):
        if self.thread and self.thread.is_alive():return
        def run():
            while not self.stop.is_set():
                try:self.step();self.error=''
                except (sqlite3.Error,TimeoutError):self.error='database_busy_or_unavailable'
                except Exception:self.error='digest_build_failed'
                self.stop.wait(self.interval)
        self.thread=threading.Thread(target=run,name='bounded-timeline-digests',daemon=True);self.thread.start()
    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=2)
    def health(self):
        return {'version':1,'running':bool(self.thread and self.thread.is_alive()),'mode':'source_excerpts',
                'completed':self.completed,'discarded_stale':self.discarded,'pending_sample':self.pending,'error':self.error,
                'retention_days':self.retention//86400,'model_inference':False,'cache_limit':self.cache_limit,
                'source_limit_per_build':self.source_limit}

def read(db,owners,q,*,kind,exclude_event_ids=(),limit=6,retention_days=30,now=None):
    if q.get('error') or q.get('topic') or kind not in ('day','episode') or not owners:return []
    now=time.time() if now is None else now;result=[]
    for offset in range(0,len(owners),200):
        chunk=owners[offset:offset+200]
        where='owner IN ('+','.join('?' for _ in chunk)+') AND kind=? AND end_utc<=? AND start_utc>=?'
        params=chunk+[kind,q['end'],now-retention_days*86400]
        if q['start'] is not None:
            where+=' AND '+('bucket_start' if kind=='day' else 'start_utc')+'>=?';params.append(q['start'])
        rows=db.execute('SELECT * FROM timeline_digests WHERE '+where+' ORDER BY end_utc DESC LIMIT ?',params+[limit]).fetchall()
        for row in rows:
            sources=json.loads(row['sources'])
            if set(sources)&set(exclude_event_ids):continue
            # Sub-day windows must not gain other hours through a day summary.
            if kind=='day' and q['start'] is not None and row['bucket_start']<q['start']:continue
            result.append({'event_id':row['id'],'source':'daily_digest' if kind=='day' else 'episode_digest','text':row['text'],
                'start_utc':row['start_utc'],'end_utc':row['end_utc'],'day':row['day'],'source_events':sources,
                'source_count':row['source_count'],'limited':bool(row['limited']),'current':False,'identity_verified':False,
                'time_basis':'host_received_source_excerpts','visual_revision':row['visual_revision'],
                'conversation_id':row['owner'][2:] if row['owner'].startswith('c:') else None,
                'scope':'conversation' if row['owner'].startswith('c:') else 'configured_device'})
    return sorted(result,key=lambda r:r['end_utc'],reverse=True)[:limit]
