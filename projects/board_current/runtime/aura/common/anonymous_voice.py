"""Temporary local voice anchors; readable aN labels are never identity keys.

No PCM is accepted or persisted here. Every match remains a provisional cluster,
including after several distinct observations. Named identification is separate.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import copy,hashlib,json,math,re,sqlite3,threading,time,uuid
from pathlib import Path
from common.asr_wire import context
from board.identity.store import normalize

APPLICATION_ID=0x4155414E
ALIAS_FIELDS={'version','context','state','reason','registry_epoch','cluster_id','code','model_id',
              'distinct_captures','provisional','identity_verified','personal_memory_allowed'}

@dataclass(frozen=True)
class AnonymousPolicy:
    threshold:float=.90
    margin:float=.10
    ttl_seconds:int=86400
    max_clusters:int=32
    minimum_voiced_ms:int=2500
    stable_captures:int=3
    max_observations:int=4096
    def __post_init__(self):
        if type(self.threshold) not in (float,int) or not math.isfinite(self.threshold) or not .8<=self.threshold<=1:
            raise ValueError('Anonymous threshold must not lower the existing 0.8 operating floor')
        if type(self.margin) not in (float,int) or not math.isfinite(self.margin) or not .1<=self.margin<=1:
            raise ValueError('Anonymous separation margin must not lower 0.1')
        for value,low,high in ((self.ttl_seconds,60,604800),(self.max_clusters,1,128),
             (self.minimum_voiced_ms,2500,20000),(self.stable_captures,3,8),(self.max_observations,32,16384)):
            if type(value) is not int or not low<=value<=high:raise ValueError('Invalid bounded anonymous policy')

def validate_alias(value,meta):
    if not isinstance(value,dict) or set(value)!=ALIAS_FIELDS or value.get('version')!=1 or type(value['version']) is not int:
        raise ValueError('Invalid anonymous voice descriptor')
    if value['context']!=context(meta):raise ValueError('Anonymous voice belongs to another capture')
    if value['state'] not in ('PROVISIONAL','STABLE_CANDIDATE','AMBIGUOUS','UNAVAILABLE','CAPACITY'):
        raise ValueError('Invalid anonymous voice state')
    if not isinstance(value['reason'],str) or not re.fullmatch('[A-Z0-9_]{1,64}',value['reason']):raise ValueError('Invalid alias reason')
    if not isinstance(value['registry_epoch'],str) or not re.fullmatch('[0-9a-f]{32}',value['registry_epoch']):raise ValueError('Invalid anonymous registry epoch')
    if not isinstance(value['model_id'],str) or not 1<=len(value['model_id'])<=160:raise ValueError('Missing voice model provenance')
    if value['provisional'] is not True or value['identity_verified'] is not False or value['personal_memory_allowed'] is not False:
        raise ValueError('Anonymous clusters are never identity or profile authorization')
    if type(value['distinct_captures']) is not int or not 0<=value['distinct_captures']<=8:raise ValueError('Invalid cluster evidence count')
    if value['state'] in ('PROVISIONAL','STABLE_CANDIDATE'):
        if not re.fullmatch('[0-9a-f]{32}',value['cluster_id'] or '') or not re.fullmatch('a[1-9][0-9]{0,12}',value['code'] or ''):
            raise ValueError('Alias must carry an internal UUID and a readable code')
        if value['state']=='STABLE_CANDIDATE' and value['distinct_captures']<3:raise ValueError('Insufficient distinct anonymous evidence')
    elif value['cluster_id'] is not None or value['code'] is not None or value['distinct_captures']!=0:
        raise ValueError('Unknown or ambiguous voice must not carry an old alias')
    return copy.deepcopy(value)

class AnonymousVoiceStore:
    """An isolated application-marked database. Use a private production path."""
    def __init__(self,path,model_id,dimension,*,policy=None,clock=time.time):
        self.path=Path(path).resolve();self.model_id=model_id;self.dimension=dimension;self.policy=policy or AnonymousPolicy();self.clock=clock
        if not isinstance(model_id,str) or not 1<=len(model_id)<=160 or type(dimension) is not int or not 1<=dimension<=4096:
            raise ValueError('Invalid anonymous voice model')
        self.lock=threading.RLock();self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():
            db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
            try:
                if db.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_ID:raise ValueError('Not an anonymous voice database')
            finally:db.close()
        with self._db(write=True) as db:
            db.execute('PRAGMA application_id='+str(APPLICATION_ID))
            db.executescript('''
              CREATE TABLE IF NOT EXISTS anonymous_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS anonymous_labels(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,cluster_id TEXT UNIQUE NOT NULL,
                boot TEXT NOT NULL,created REAL NOT NULL,expires REAL NOT NULL,state TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS anonymous_anchors(
                cluster_id TEXT PRIMARY KEY REFERENCES anonymous_labels(cluster_id),anchor TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS anonymous_samples(
                cluster_id TEXT NOT NULL REFERENCES anonymous_labels(cluster_id),capture_id TEXT NOT NULL,
                digest TEXT NOT NULL,PRIMARY KEY(cluster_id,capture_id),UNIQUE(cluster_id,digest));
              CREATE TABLE IF NOT EXISTS anonymous_observations(
                request_id TEXT PRIMARY KEY,owner TEXT NOT NULL,result TEXT NOT NULL,received REAL NOT NULL,cluster_id TEXT);
            ''')
            expected={'model_id':model_id,'dimension':str(dimension)}
            for key,value in expected.items():
                row=db.execute('SELECT value FROM anonymous_meta WHERE key=?',(key,)).fetchone()
                if row is not None and row[0]!=value:raise ValueError('Anonymous model changed; use a new private registry')
                db.execute('INSERT OR IGNORE INTO anonymous_meta VALUES(?,?)',(key,value))
            db.execute('INSERT OR IGNORE INTO anonymous_meta VALUES(?,?)',('registry_epoch',uuid.uuid4().hex))
            db.execute('INSERT OR IGNORE INTO anonymous_meta VALUES(?,?)',('revision','0'))
            self.registry_epoch=db.execute("SELECT value FROM anonymous_meta WHERE key='registry_epoch'").fetchone()[0]
    @contextmanager
    def _db(self,*,write=False):
        if not self.lock.acquire(timeout=.03):raise TimeoutError('Anonymous voice registry busy')
        db=None
        try:
            db=sqlite3.connect(str(self.path),timeout=.03);db.row_factory=sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA busy_timeout=30')
            if write:db.execute('BEGIN IMMEDIATE')
            yield db
            if write:db.commit()
        except Exception:
            if db is not None:db.rollback()
            raise
        finally:
            if db is not None:db.close()
            self.lock.release()
    @staticmethod
    def _owner(meta):return json.dumps(context(meta),sort_keys=True,separators=(',',':'))
    def _descriptor(self,meta,state,reason,cluster=None,count=0):
        return validate_alias(dict(version=1,context=context(meta),state=state,reason=reason,registry_epoch=self.registry_epoch,
          cluster_id=cluster['cluster_id'] if cluster is not None else None,code='a'+str(cluster['seq']) if cluster is not None else None,
          model_id=self.model_id,distinct_captures=min(8,count),provisional=True,identity_verified=False,personal_memory_allowed=False),meta)
    def unavailable(self,meta,reason='INSUFFICIENT_SPEECH'):
        return self._descriptor(meta,'UNAVAILABLE',reason)
    @property
    def revision(self):
        with self._db() as db:return int(db.execute("SELECT value FROM anonymous_meta WHERE key='revision'").fetchone()[0])
    def _expire(self,db,now):
        ids=[r[0] for r in db.execute("SELECT cluster_id FROM anonymous_labels WHERE state='ACTIVE' AND expires<=?",(now,))]
        for identity in ids:
            db.execute('DELETE FROM anonymous_anchors WHERE cluster_id=?',(identity,))
            db.execute('DELETE FROM anonymous_samples WHERE cluster_id=?',(identity,))
            db.execute('DELETE FROM anonymous_observations WHERE cluster_id=?',(identity,))
            db.execute("UPDATE anonymous_labels SET state='EXPIRED' WHERE cluster_id=?",(identity,))
        if ids:db.execute("UPDATE anonymous_meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
        db.execute('DELETE FROM anonymous_observations WHERE received<?',(now-self.policy.ttl_seconds,))
    def observe(self,meta,vector,*,voiced_ms,overlap='unknown',expected_revision=None,is_current=lambda:True):
        meta=context(meta);vector=normalize(vector,self.dimension)
        if not is_current():raise InterruptedError('Anonymous capture cancelled')
        if type(voiced_ms) is not int or not 0<=voiced_ms<=20000:raise ValueError('Invalid speech duration')
        if overlap not in ('unknown','not_detected','detected'):raise ValueError('Invalid overlap evidence')
        if voiced_ms<self.policy.minimum_voiced_ms or overlap=='detected':
            return self.unavailable(meta,'OVERLAPPING_SPEECH' if overlap=='detected' else 'INSUFFICIENT_SPEECH')
        now=self.clock();owner=self._owner(meta)
        with self._db(write=True) as db:
            revision=int(db.execute("SELECT value FROM anonymous_meta WHERE key='revision'").fetchone()[0])
            if expected_revision is not None and revision!=expected_revision:raise ValueError('Anonymous registry changed during analysis')
            self._expire(db,now)
            if not is_current():raise InterruptedError('Anonymous capture cancelled')
            prior=db.execute('SELECT owner,result FROM anonymous_observations WHERE request_id=?',(meta['request_id'],)).fetchone()
            if prior:
                if prior['owner']!=owner:raise ValueError('Anonymous request reused with another recording')
                return validate_alias(json.loads(prior['result']),meta)
            rows=db.execute("SELECT l.*,a.anchor FROM anonymous_labels l JOIN anonymous_anchors a USING(cluster_id) WHERE l.state='ACTIVE' AND l.boot=?",(meta['board_boot_id'],)).fetchall()
            scored=sorted(((sum(a*b for a,b in zip(vector,json.loads(row['anchor']))),row) for row in rows),key=lambda pair:pair[0],reverse=True)
            row=None;count=0
            if scored and scored[0][0]>=self.policy.threshold:
                if len(scored)>1 and scored[0][0]-scored[1][0]<self.policy.margin:
                    result=self._descriptor(meta,'AMBIGUOUS','INSUFFICIENT_CLUSTER_MARGIN')
                else:row=scored[0][1]
            elif db.execute("SELECT count(*) FROM anonymous_labels WHERE state='ACTIVE'").fetchone()[0]>=self.policy.max_clusters:
                result=self._descriptor(meta,'CAPACITY','ANONYMOUS_REGISTRY_FULL')
            else:
                identity=uuid.uuid4().hex
                db.execute("INSERT INTO anonymous_labels(cluster_id,boot,created,expires,state) VALUES(?,?,?,?,'ACTIVE')",(identity,meta['board_boot_id'],now,now+self.policy.ttl_seconds))
                # Freeze the actual first anchor. Do not average uncertain matches
                # into it and gradually move an identity toward another voice.
                db.execute('INSERT INTO anonymous_anchors VALUES(?,?)',(identity,json.dumps(vector)))
                row=db.execute('SELECT * FROM anonymous_labels WHERE cluster_id=?',(identity,)).fetchone()
            if row is not None:
                db.execute('INSERT OR IGNORE INTO anonymous_samples VALUES(?,?,?)',(row['cluster_id'],meta['capture_id'],meta['pcm_sha256']))
                count=db.execute('SELECT count(*) FROM anonymous_samples WHERE cluster_id=?',(row['cluster_id'],)).fetchone()[0]
                result=self._descriptor(meta,'STABLE_CANDIDATE' if count>=self.policy.stable_captures else 'PROVISIONAL',
                  'DISTINCT_ANONYMOUS_CAPTURES' if count>=self.policy.stable_captures else 'TEMPORARY_VOICE_CLUSTER',row,count)
            db.execute('INSERT INTO anonymous_observations VALUES(?,?,?,?,?)',(meta['request_id'],owner,json.dumps(result,separators=(',',':')),now,result['cluster_id']))
            excess=db.execute('SELECT count(*) FROM anonymous_observations').fetchone()[0]-self.policy.max_observations
            if excess>0:db.execute('DELETE FROM anonymous_observations WHERE request_id IN (SELECT request_id FROM anonymous_observations ORDER BY received LIMIT ?)',(excess,))
            if not is_current():raise InterruptedError('Anonymous capture cancelled')
            return result
    def active(self,identity,*,boot=None):
        if not isinstance(identity,str) or not re.fullmatch('[0-9a-f]{32}',identity):raise ValueError('Use internal anonymous UUID, not aN')
        with self._db(write=True) as db:
            self._expire(db,self.clock())
            row=db.execute("SELECT * FROM anonymous_labels WHERE cluster_id=? AND state='ACTIVE'",(identity,)).fetchone()
            if row is None or boot is not None and row['boot']!=boot:raise ValueError('Anonymous voice expired or belongs to another boot')
            return dict(cluster_id=row['cluster_id'],code='a'+str(row['seq']),registry_epoch=self.registry_epoch,model_id=self.model_id)
    def evidence(self,meta):
        """Private readback, so an IPC descriptor cannot invent stable captures."""
        meta=context(meta)
        with self._db(write=True) as db:
            self._expire(db,self.clock())
            row=db.execute('SELECT owner,result FROM anonymous_observations WHERE request_id=?',(meta['request_id'],)).fetchone()
            if row is None or row['owner']!=self._owner(meta):raise ValueError('No current private anonymous observation')
            return validate_alias(json.loads(row['result']),meta)
    def delete(self,identity):
        with self._db(write=True) as db:
            if not db.execute('SELECT 1 FROM anonymous_labels WHERE cluster_id=?',(identity,)).fetchone():return False
            db.execute('DELETE FROM anonymous_anchors WHERE cluster_id=?',(identity,));db.execute('DELETE FROM anonymous_samples WHERE cluster_id=?',(identity,))
            db.execute("UPDATE anonymous_labels SET state='DELETED' WHERE cluster_id=?",(identity,))
            db.execute("UPDATE anonymous_meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
            # Purge descriptors that could otherwise resurrect a deleted alias.
            db.execute('DELETE FROM anonymous_observations WHERE cluster_id=?',(identity,))
            return True
    def health(self):
        with self._db(write=True) as db:
            self._expire(db,self.clock())
            return dict(version=1,active_clusters=db.execute("SELECT count(*) FROM anonymous_labels WHERE state='ACTIVE'").fetchone()[0],
              maximum_clusters=self.policy.max_clusters,retention_seconds=self.policy.ttl_seconds,
              biometric_anchor_persisted=True,pcm_persisted=False,provisional_only=True,automatic_profile_access=False)
