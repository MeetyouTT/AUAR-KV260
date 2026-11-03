"""Explicit cross-modality links over existing stores, never biometric authority.

The registry activates only after original enrollment adapters sign real commit
receipts. The template stores remain their own authorities; no vectors live here.
"""
from contextlib import contextmanager
import copy,hashlib,hmac,json,math,re,sqlite3,threading,time,uuid
from pathlib import Path
from common.asr_wire import context
from common.speaker_visual import validate_visual
from common.voice_enrollment import valid_name,confirmed,update_confirmed
from common.anonymous_voice import validate_alias
from common.binding_intent import binding_intent

APPLICATION_ID=0x41554C4B
TERMINAL={'ACTIVE','CANCELLED','EXPIRED','PARTIAL_CANCELLED','PARTIAL_EXPIRED','PARTIAL_CONFLICT'}
RESOLUTION_FIELDS={'version','context','state','reason','person_id','name','modalities','claim_scope',
  'provisional','field_calibrated','identity_verified','personal_memory_allowed','single_speaker_verified'}

def validate_resolution(value,meta):
    if not isinstance(value,dict) or set(value)!=RESOLUTION_FIELDS or type(value['version']) is not int or value['version']!=1:
        raise ValueError('Invalid linked identity evidence')
    if value['context']!=context(meta) or value['state'] not in ('UNKNOWN','CONFLICT','MATCH_CANDIDATE','PROVISIONAL_NAME_CANDIDATE'):
        raise ValueError('Foreign or invalid linked identity evidence')
    if not isinstance(value['reason'],str) or not re.fullmatch('[A-Z0-9_]{1,64}',value['reason']):raise ValueError('Invalid identity resolution reason')
    if (value['identity_verified'] is not False or value['personal_memory_allowed'] is not False or value['single_speaker_verified'] is not False
        or type(value['provisional']) is not bool or type(value['field_calibrated']) is not bool):raise ValueError('Identity evidence cannot grant authorization')
    if value['modalities'] not in ([],['face'],['voice'],['anonymous'],['face','voice'],['anonymous','face'],['anonymous','voice'],['anonymous','face','voice']):
        raise ValueError('Invalid identity evidence modalities')
    if value['state'] in ('UNKNOWN','CONFLICT'):
        if value['person_id'] is not None or value['name'] is not None or value['claim_scope']!='none':raise ValueError('Unknown identity retains a name')
    else:
        if not isinstance(value['person_id'],str) or not re.fullmatch('[0-9a-f]{32}',value['person_id']) or not valid_name(value['name']):
            raise ValueError('Invalid linked identity name')
        if value['claim_scope'] not in ('visible_person','voice_candidate','provisional_voice_candidate'):raise ValueError('Invalid linked identity scope')
    if value['state']=='PROVISIONAL_NAME_CANDIDATE' and (value['provisional'] is not True or value['field_calibrated'] is not False or value['claim_scope']!='provisional_voice_candidate'):
        raise ValueError('Uncalibrated candidate must remain provisional')
    return copy.deepcopy(value)

def _canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def _identifier(value):return isinstance(value,str) and bool(re.fullmatch('[A-Za-z0-9_-]{1,96}',value))
def _gallery(value):
    if not isinstance(value,dict) or set(value)!={'store_id','model_id','revision'} or not _identifier(value['store_id']):raise ValueError('Invalid gallery reference')
    if not isinstance(value['model_id'],str) or not 1<=len(value['model_id'])<=160 or type(value['revision']) is not int or value['revision']<0:
        raise ValueError('Invalid gallery model/revision')
    return copy.deepcopy(value)
def _guard(visual,meta):
    v=validate_visual(visual,meta)
    if v['state']!='FACE_AT_CAPTURE_BOUNDARIES':raise ValueError('Fresh single face is required only for this binding workflow')
    e=v['evidence']
    return {key:copy.deepcopy(e[key]) for key in ('service_epoch','camera_epoch','target','gallery_revision','face_identity_id')}

class ReceiptAuthority:
    """Internal adapter capability; do not expose sign() as an HTTP/LLM tool."""
    def __init__(self,key):
        if not isinstance(key,bytes) or len(key)<32:raise ValueError('A private receipt key is required')
        self.key=key
    def sign(self,payload):
        value=copy.deepcopy(payload)
        return {'payload':value,'mac':hmac.new(self.key,_canonical(value),hashlib.sha256).hexdigest()}
    def verify(self,envelope):
        if not isinstance(envelope,dict) or set(envelope)!={'payload','mac'} or not isinstance(envelope['mac'],str):raise ValueError('Unsigned enrollment receipt')
        expected=hmac.new(self.key,_canonical(envelope['payload']),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,envelope['mac']):raise ValueError('Untrusted enrollment receipt')
        return copy.deepcopy(envelope['payload'])

class IdentityLinkRegistry:
    def __init__(self,path,authority,*,anonymous_lookup=None,anonymous_evidence=None,voice_reference=None,clock=time.time,attempt_seconds=180,max_people=32):
        self.path=Path(path).resolve();self.authority=authority;self.clock=clock;self.attempt_seconds=attempt_seconds;self.max_people=max_people
        self.anonymous_lookup=anonymous_lookup
        self.anonymous_evidence=anonymous_evidence
        self.voice_reference=voice_reference
        if type(attempt_seconds) is not int or not 30<=attempt_seconds<=600 or type(max_people) is not int or not 1<=max_people<=128:raise ValueError('Invalid binding limits')
        self.lock=threading.RLock();self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():
            db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
            try:
                if db.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_ID:raise ValueError('Not an identity link database')
            finally:db.close()
        with self._db(write=True) as db:
            db.execute('PRAGMA application_id='+str(APPLICATION_ID))
            db.executescript('''
              CREATE TABLE IF NOT EXISTS linked_people(person_id TEXT PRIMARY KEY,name TEXT NOT NULL,name_key TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS modality_links(person_id TEXT NOT NULL REFERENCES linked_people(person_id),modality TEXT NOT NULL,
                store_id TEXT NOT NULL,identity_id TEXT NOT NULL,model_id TEXT NOT NULL,revision INTEGER NOT NULL,fingerprint TEXT,state TEXT NOT NULL,
                PRIMARY KEY(modality,store_id,identity_id,model_id));
              CREATE TABLE IF NOT EXISTS binding_attempts(attempt_id TEXT PRIMARY KEY,origin TEXT NOT NULL,name TEXT,anonymous_id TEXT,
                face_guard TEXT NOT NULL,face_gallery TEXT NOT NULL,voice_gallery TEXT NOT NULL,state TEXT NOT NULL,expires REAL NOT NULL,
                confirmed_context TEXT,face_receipt TEXT,voice_receipt TEXT,person_id TEXT,error TEXT NOT NULL DEFAULT '');
              CREATE TABLE IF NOT EXISTS anonymous_person_links(registry_epoch TEXT NOT NULL,anonymous_id TEXT NOT NULL,person_id TEXT NOT NULL REFERENCES linked_people(person_id),
                PRIMARY KEY(registry_epoch,anonymous_id));
            ''')
    @contextmanager
    def _db(self,*,write=False):
        if not self.lock.acquire(timeout=.03):raise TimeoutError('Identity links busy')
        db=None
        try:
            db=sqlite3.connect(str(self.path),timeout=.03);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA busy_timeout=30')
            if write:db.execute('BEGIN IMMEDIATE')
            yield db
            if write:db.commit()
        except Exception:
            if db is not None:db.rollback()
            raise
        finally:
            if db is not None:db.close()
            self.lock.release()
    def expire(self):
        with self._db(write=True) as db:
            db.execute("UPDATE binding_attempts SET state=CASE WHEN face_receipt IS NULL AND voice_receipt IS NULL THEN 'EXPIRED' ELSE 'PARTIAL_EXPIRED' END,"
              "name=CASE WHEN face_receipt IS NULL AND voice_receipt IS NULL THEN NULL ELSE name END,error='BINDING_DEADLINE' WHERE state NOT IN ('ACTIVE','CANCELLED','EXPIRED','PARTIAL_CANCELLED','PARTIAL_EXPIRED','PARTIAL_CONFLICT') AND expires<=?",(self.clock(),))
    @staticmethod
    def _actor(meta):return meta['board_boot_id'],meta['session_id']
    def _attempt(self,db,attempt_id,meta):
        row=db.execute('SELECT * FROM binding_attempts WHERE attempt_id=?',(attempt_id,)).fetchone()
        if row is None or self._actor(json.loads(row['origin']))!=self._actor(context(meta)):raise ValueError('Foreign binding attempt')
        if meta['generation']<json.loads(row['origin'])['generation']:raise ValueError('Old binding generation')
        return row
    def start(self,meta,text,*,visual,face_gallery,voice_gallery,anonymous=None,selected_person_id=None):
        meta=context(meta);intent=binding_intent(text)
        if intent['kind']!='remember_self' or intent['name'] is None:raise ValueError('Explicit self-enrollment with a name is required')
        face,voice=_gallery(face_gallery),_gallery(voice_gallery);guard=_guard(visual,meta)
        if guard['gallery_revision']!=face['revision']:raise ValueError('Face gallery changed')
        if anonymous is not None:
            anonymous=validate_alias(anonymous,meta)
            if anonymous['state'] not in ('PROVISIONAL','STABLE_CANDIDATE'):raise ValueError('Ambiguous alias cannot be bound')
            if self.anonymous_lookup is None:raise ValueError('Anonymous alias requires a live private registry lookup')
            live=self.anonymous_lookup(anonymous['cluster_id'],boot=meta['board_boot_id'])
            if any(live[key]!=anonymous[key] for key in ('cluster_id','code','registry_epoch','model_id')):raise ValueError('Anonymous alias registry changed')
        self.expire();name=intent['name']
        with self._db(write=True) as db:
            # Never infer an existing identity from a same-name record.
            names=db.execute("SELECT person_id FROM linked_people WHERE state='ACTIVE' AND name_key=?",(name.casefold(),)).fetchall()
            if names and selected_person_id is None:raise ValueError('EXPLICIT_EXISTING_IDENTITY_SELECTION_REQUIRED')
            if selected_person_id is not None:
                if not any(r[0]==selected_person_id for r in names):raise ValueError('Selected identity does not match the explicit name')
            active=db.execute("SELECT count(*) FROM binding_attempts WHERE state NOT IN ('ACTIVE','CANCELLED','EXPIRED','PARTIAL_CANCELLED','PARTIAL_EXPIRED','PARTIAL_CONFLICT')").fetchone()[0]
            if active>=8:raise ValueError('Binding queue is full')
            attempt=uuid.uuid4().hex
            alias=json.dumps({'registry_epoch':anonymous['registry_epoch'],'cluster_id':anonymous['cluster_id']}) if anonymous is not None else None
            db.execute('INSERT INTO binding_attempts(attempt_id,origin,name,anonymous_id,face_guard,face_gallery,voice_gallery,state,expires,person_id) VALUES(?,?,?,?,?,?,?,?,?,?)',
             (attempt,_canonical(meta).decode(),name,alias,json.dumps(guard),json.dumps(face),json.dumps(voice),'AWAIT_CONFIRMATION',self.clock()+self.attempt_seconds,selected_person_id))
            return {'attempt_id':attempt,'state':'AWAIT_CONFIRMATION','name':name,'face_already_saved':False,'unified_saved':False,'personal_memory_allowed':False}
    def confirmation_diagnostics(self):
        """Read RAM scalars only; never opens the registry or exports owners."""
        value=dict(getattr(self,'_confirmation_trace',{}))
        phases={'AWAIT_CONFIRMATION','SAMPLING_FACE','SAMPLING_VOICE','ACTIVE','CANCELLED','EXPIRED',
                'PARTIAL_CANCELLED','PARTIAL_EXPIRED','PARTIAL_CONFLICT'}
        gates={'CONTEXT','VISUAL','EXPIRE','ATTEMPT','STATE','DISTINCT_CAPTURE','EXPLICIT_CONFIRMATION',
            'GUARD','LIFECYCLE_CHANGED','CONFIRMED','NOT_CONFIRMATION','FOREIGN_ATTEMPT','OLD_GENERATION'}
        reasons={'NO_VISUAL_EVIDENCE','NO_SINGLE_FACE','MULTIPLE_FACES','FACE_LIFECYCLE_CHANGED',
            'CAMERA_SERVICE_CHANGED','CAMERA_NOT_READY','CAMERA_EPOCH_CHANGED','FACE_IDENTITY_CHANGED',
            'FACE_IDENTITY_UNVERIFIED','UNVERIFIED_VISUAL_SOURCE','VISUAL_STALE_OR_INVALID',
            'VISUAL_PROVIDER_UNAVAILABLE','VISUAL_EXPIRED_BEFORE_ANALYSIS','NOT_ACTIVE_SPEAKER_PROOF'}
        def fixed(key,allowed):
            item=value.get(key)
            return item if type(item) is str and item in allowed else None
        result={'version':1,'gate':fixed('gate',gates),'phase':fixed('phase',phases),
            'outcome':fixed('outcome',{'TRUE','FALSE','ValueError','TimeoutError','other'}),
            'visual_state':fixed('visual_state',{'UNAVAILABLE','FACE_AT_CAPTURE_BOUNDARIES'}),
            'visual_reason':fixed('visual_reason',reasons)}
        for key in ('visual_present','visual_actual','visual_context_matches','visual_guard_valid',
            'actor_matches','generation_not_old','request_distinct','capture_distinct','pcm_distinct',
            'explicit_confirmation','service_epoch_same','camera_epoch_same','target_same',
            'gallery_revision_same','face_identity_same','guard_same'):
            result[key]=value.get(key) if type(value.get(key)) is bool else None
        return result

    def confirm(self,attempt_id,meta,text,visual):
        # Only one bounded RAM trace. No prompt, name, identifier or target value.
        trace={'gate':'CONTEXT','visual_present':visual is not None}
        self._confirmation_trace=trace
        try:
            meta=context(meta)
            trace.update(gate='VISUAL',visual_actual=isinstance(visual,dict) and visual.get('source_kind')=='actual',
                visual_context_matches=isinstance(visual,dict) and visual.get('context')==meta)
            if isinstance(visual,dict):
                # Filter these before retention, as well as at the public boundary.
                state=visual.get('state');reason=visual.get('reason')
                if type(state) is str and state in ('UNAVAILABLE','FACE_AT_CAPTURE_BOUNDARIES'):trace['visual_state']=state
                allowed={'NO_VISUAL_EVIDENCE','NO_SINGLE_FACE','MULTIPLE_FACES','FACE_LIFECYCLE_CHANGED',
                    'CAMERA_SERVICE_CHANGED','CAMERA_NOT_READY','CAMERA_EPOCH_CHANGED','FACE_IDENTITY_CHANGED',
                    'FACE_IDENTITY_UNVERIFIED','UNVERIFIED_VISUAL_SOURCE','VISUAL_STALE_OR_INVALID',
                    'VISUAL_PROVIDER_UNAVAILABLE','VISUAL_EXPIRED_BEFORE_ANALYSIS','NOT_ACTIVE_SPEAKER_PROOF'}
                if type(reason) is str and reason in allowed:trace['visual_reason']=reason
            guard=_guard(visual,meta);trace.update(visual_guard_valid=True,gate='EXPIRE');self.expire()
            with self._db(write=True) as db:
                trace['gate']='ATTEMPT'
                try:row=self._attempt(db,attempt_id,meta)
                except ValueError as error:
                    if str(error)=='Foreign binding attempt':trace.update(gate='FOREIGN_ATTEMPT',actor_matches=False)
                    elif str(error)=='Old binding generation':trace.update(gate='OLD_GENERATION',generation_not_old=False)
                    raise
                trace.update(gate='STATE',phase=row['state'],actor_matches=True,generation_not_old=True)
                if row['state']!='AWAIT_CONFIRMATION':raise ValueError('Binding is not awaiting confirmation')
                original=json.loads(row['origin'])
                trace.update(gate='DISTINCT_CAPTURE',request_distinct=meta['request_id']!=original['request_id'],
                    capture_distinct=meta['capture_id']!=original['capture_id'],pcm_distinct=meta['pcm_sha256']!=original['pcm_sha256'])
                if meta['request_id']==original['request_id'] or meta['capture_id']==original['capture_id'] or meta['pcm_sha256']==original['pcm_sha256']:
                    raise ValueError('Confirmation must be a distinct capture')
                trace['gate']='EXPLICIT_CONFIRMATION'
                explicit=confirmed(text) or update_confirmed(text);trace['explicit_confirmation']=bool(explicit)
                if not explicit:
                    trace.update(gate='NOT_CONFIRMATION',outcome='FALSE');return False
                trace['gate']='GUARD';original_guard=json.loads(row['face_guard'])
                for key,label in (('service_epoch','service_epoch_same'),('camera_epoch','camera_epoch_same'),
                    ('target','target_same'),('gallery_revision','gallery_revision_same'),('face_identity_id','face_identity_same')):
                    trace[label]=guard[key]==original_guard[key]
                trace['guard_same']=guard==original_guard
                if guard!=original_guard:
                    db.execute("UPDATE binding_attempts SET state='CANCELLED',name=NULL,error='FACE_LIFECYCLE_CHANGED' WHERE attempt_id=?",(attempt_id,))
                    trace.update(gate='LIFECYCLE_CHANGED',phase='CANCELLED',outcome='FALSE');return False
                db.execute("UPDATE binding_attempts SET state='SAMPLING_FACE',confirmed_context=? WHERE attempt_id=?",(_canonical(meta).decode(),attempt_id))
                trace.update(gate='CONFIRMED',phase='SAMPLING_FACE',outcome='TRUE');return True
        except BaseException as error:
            kind=type(error).__name__
            trace['outcome']=kind if kind in ('ValueError','TimeoutError') else 'other'
            raise
    def _receipt(self,row,envelope):
        p=self.authority.verify(envelope)
        required={'version','attempt_id','origin_context','commit_context','modality','state','operation_id','store_id','identity_id','model_id',
          'revision_before','revision_after','template_fingerprint','display_name','checks','face_guard','capture_ids','pcm_digests'}
        if not isinstance(p,dict) or set(p)!=required or p.get('version')!=1 or type(p['version']) is not int or p.get('state') not in ('COMMITTED','EXISTING_CONFIRMED'):raise ValueError('Incomplete enrollment receipt')
        if p['attempt_id']!=row['attempt_id'] or p['origin_context']!=json.loads(row['origin']):raise ValueError('Receipt belongs to another attempt')
        commit=context(p['commit_context']);original=context(p['origin_context'])
        if self._actor(commit)!=self._actor(original) or commit['generation']<original['generation']:raise ValueError('Foreign receipt capture')
        if p['modality'] not in ('face','voice') or not _identifier(p['operation_id']) or not _identifier(p['identity_id']):raise ValueError('Invalid receipt identifiers')
        gallery=json.loads(row[p['modality']+'_gallery'])
        if p['store_id']!=gallery['store_id'] or p['model_id']!=gallery['model_id'] or type(p['revision_before']) is not int or p['revision_before']!=gallery['revision']:
            raise ValueError('Receipt model/store/revision changed')
        reuse=p['state']=='EXISTING_CONFIRMED'
        expected_revision=gallery['revision'] if reuse else gallery['revision']+1
        if type(p['revision_after']) is not int or p['revision_after']!=expected_revision:raise ValueError('Enrollment revision changed')
        if reuse and (p['modality']!='face' or p['identity_id']!=json.loads(row['face_guard'])['face_identity_id']):
            raise ValueError('Only the originally observed existing face may be reused')
        if p['display_name']!=row['name'] or p['face_guard']!=json.loads(row['face_guard']):raise ValueError('Enrollment target or name changed')
        fingerprint=p['template_fingerprint']
        if fingerprint is not None and (not isinstance(fingerprint,str) or not re.fullmatch('[0-9a-f]{64}',fingerprint)):raise ValueError('Invalid template fingerprint')
        checks=p['checks']
        if not isinstance(checks,dict) or set(checks)!={'quality_passed','explicit_confirmation','original_policy','single_speaker_verified'}:
            raise ValueError('Missing original enrollment checks')
        expected=('original_face_match_and_explicit_link_consent' if reuse else 'original_face_enrollment') if p['modality']=='face' else 'original_three_utterance_enrollment'
        if (checks!={'quality_passed':True,'explicit_confirmation':True,'original_policy':expected,'single_speaker_verified':False}
            or any(type(checks[key]) is not bool for key in ('quality_passed','explicit_confirmation','single_speaker_verified'))):
            raise ValueError('Original enrollment policy was not satisfied')
        if p['modality']=='voice':
            if (not isinstance(p['capture_ids'],list) or len(set(p['capture_ids']))<3 or len(p['capture_ids'])!=3
                or any(not _identifier(s) for s in p['capture_ids']) or not isinstance(p['pcm_digests'],list)
                or len(set(p['pcm_digests']))!=3 or any(not isinstance(s,str) or not re.fullmatch('[0-9a-f]{64}',s) for s in p['pcm_digests'])):
                raise ValueError('Three distinct original recordings required')
        elif p['capture_ids'] or p['pcm_digests']:raise ValueError('Face receipt cannot carry voice sample data')
        return p
    def accept_receipt(self,attempt_id,meta,envelope):
        meta=context(meta);self.expire()
        with self._db(write=True) as db:
            row=self._attempt(db,attempt_id,meta)
            if row['state'] in TERMINAL:raise ValueError('Late receipt for terminal binding')
            p=self._receipt(row,envelope);kind=p['modality']
            if p['commit_context']!=meta:raise ValueError('Receipt completion belongs to another capture')
            if kind=='face' and row['state']!='SAMPLING_FACE':raise ValueError('Face enrollment is out of order')
            if kind=='voice' and row['state']!='SAMPLING_VOICE':raise ValueError('Voice enrollment is out of order')
            db.execute('UPDATE binding_attempts SET '+kind+'_receipt=?,state=? WHERE attempt_id=?',(json.dumps(p),'SAMPLING_VOICE' if kind=='face' else 'READY_TO_LINK',attempt_id))
            if kind=='face':return {'state':'SAMPLING_VOICE','face_already_saved':True,'unified_saved':False,'personal_memory_allowed':False}
            row=db.execute('SELECT * FROM binding_attempts WHERE attempt_id=?',(attempt_id,)).fetchone()
            receipts=[json.loads(row['face_receipt']),p];person=row['person_id']
            conflict=any(db.execute("SELECT 1 FROM modality_links WHERE modality=? AND store_id=? AND identity_id=? AND model_id=? AND state='ACTIVE' AND person_id!=?",
                (r['modality'],r['store_id'],r['identity_id'],r['model_id'],person or '')).fetchone() for r in receipts)
            same_name=db.execute("SELECT 1 FROM linked_people WHERE name_key=? AND state='ACTIVE' AND person_id!=?",(row['name'].casefold(),person or '')).fetchone()
            if conflict or same_name:
                db.execute("UPDATE binding_attempts SET state='PARTIAL_CONFLICT',error='EXISTING_IDENTITY_CONFLICT' WHERE attempt_id=?",(attempt_id,))
                return {'state':'PARTIAL_CONFLICT','face_already_saved':True,'voice_already_saved':True,'unified_saved':False,'personal_memory_allowed':False}
            alias=json.loads(row['anonymous_id']) if row['anonymous_id'] is not None else None
            if alias is not None:
                try:
                    live=self.anonymous_lookup(alias['cluster_id'],boot=meta['board_boot_id'])
                    if live['registry_epoch']!=alias['registry_epoch']:raise ValueError('Anonymous registry reset')
                except (ValueError,TypeError,TimeoutError):
                    db.execute("UPDATE binding_attempts SET state='PARTIAL_CONFLICT',error='ANONYMOUS_ALIAS_EXPIRED' WHERE attempt_id=?",(attempt_id,))
                    return {'state':'PARTIAL_CONFLICT','unified_saved':False,'personal_memory_allowed':False}
                old_link=db.execute('SELECT person_id FROM anonymous_person_links WHERE registry_epoch=? AND anonymous_id=?',(alias['registry_epoch'],alias['cluster_id'])).fetchone()
                if old_link is not None and old_link[0]!=person:
                    db.execute("UPDATE binding_attempts SET state='PARTIAL_CONFLICT',error='ANONYMOUS_ALIAS_ALREADY_LINKED' WHERE attempt_id=?",(attempt_id,))
                    return {'state':'PARTIAL_CONFLICT','unified_saved':False,'personal_memory_allowed':False}
            if person is None:
                if db.execute("SELECT count(*) FROM linked_people WHERE state='ACTIVE'").fetchone()[0]>=self.max_people:
                    db.execute("UPDATE binding_attempts SET state='PARTIAL_CONFLICT',error='IDENTITY_REGISTRY_FULL' WHERE attempt_id=?",(attempt_id,))
                    return {'state':'PARTIAL_CONFLICT','unified_saved':False,'personal_memory_allowed':False}
                person=uuid.uuid4().hex;db.execute("INSERT INTO linked_people VALUES(?,?,?,'ACTIVE',?)",(person,row['name'],row['name'].casefold(),self.clock()))
            for receipt in receipts:
                db.execute("INSERT INTO modality_links VALUES(?,?,?,?,?,?,?,'ACTIVE') ON CONFLICT(modality,store_id,identity_id,model_id) DO UPDATE SET person_id=excluded.person_id,revision=excluded.revision,fingerprint=excluded.fingerprint,state='ACTIVE'",
                  (person,receipt['modality'],receipt['store_id'],receipt['identity_id'],receipt['model_id'],receipt['revision_after'],receipt['template_fingerprint']))
            if alias is not None:
                db.execute('INSERT OR IGNORE INTO anonymous_person_links VALUES(?,?,?)',(alias['registry_epoch'],alias['cluster_id'],person))
            db.execute("UPDATE binding_attempts SET state='ACTIVE',person_id=? WHERE attempt_id=?",(person,attempt_id))
            return {'state':'ACTIVE','person_id':person,'name':row['name'],'face_already_saved':True,'voice_already_saved':True,'unified_saved':True,'personal_memory_allowed':False}
    def cancel(self,attempt_id,meta):
        with self._db(write=True) as db:
            row=self._attempt(db,attempt_id,context(meta))
            if row['state']=='ACTIVE':raise ValueError('Committed links require explicit deletion, not cancellation')
            partial=row['face_receipt'] is not None or row['voice_receipt'] is not None
            state='PARTIAL_CANCELLED' if partial else 'CANCELLED'
            db.execute('UPDATE binding_attempts SET state=?,name=CASE WHEN ? THEN name ELSE NULL END,error=? WHERE attempt_id=?',(state,partial,'USER_CANCELLED',attempt_id))
            return {'state':state,'face_already_saved':row['face_receipt'] is not None,'voice_already_saved':row['voice_receipt'] is not None,'unified_saved':False,'personal_memory_allowed':False}
    def partial(self,attempt_id,meta,reason):
        if not isinstance(reason,str) or not re.fullmatch('[A-Z0-9_]{1,64}',reason):raise ValueError('Invalid partial outcome reason')
        with self._db(write=True) as db:
            row=self._attempt(db,attempt_id,context(meta))
            if row['state']=='ACTIVE':raise ValueError('An active binding cannot be demoted by a late failure')
            db.execute("UPDATE binding_attempts SET state='PARTIAL_CONFLICT',error=? WHERE attempt_id=?",(reason,attempt_id))
            return {'state':'PARTIAL_CONFLICT','unified_saved':False,'personal_memory_allowed':False}
    def attach_alias(self,attempt_id,meta,alias):
        alias=validate_alias(alias,meta)
        if alias['state'] not in ('PROVISIONAL','STABLE_CANDIDATE') or self.anonymous_lookup is None:return False
        live=self.anonymous_lookup(alias['cluster_id'],boot=meta['board_boot_id'])
        if any(live[k]!=alias[k] for k in ('registry_epoch','cluster_id','model_id','code')):raise ValueError('Anonymous registry changed')
        with self._db(write=True) as db:
            row=self._attempt(db,attempt_id,context(meta))
            if row['state']!='SAMPLING_VOICE':return False
            value={'registry_epoch':alias['registry_epoch'],'cluster_id':alias['cluster_id']}
            if row['anonymous_id'] is not None:return json.loads(row['anonymous_id'])==value
            db.execute('UPDATE binding_attempts SET anonymous_id=? WHERE attempt_id=?',(json.dumps(value),attempt_id));return True
    def attempt(self,attempt_id,meta):
        self.expire()
        with self._db() as db:
            row=self._attempt(db,attempt_id,context(meta))
            return dict(row)
    def resolve(self,meta,proofs,*,anonymous=None):
        """Fresh proofs; uncalibrated ACTIVE links expose only a name candidate."""
        meta=context(meta);now=self.clock();hits={};reasons=[]
        if not isinstance(proofs,list) or len(proofs)>2:raise ValueError('At most one face and voice proof')
        def result(state,reason,hit=None):
            kinds=sorted(hits);calibrated=bool('voice' in hits and not hits['voice'].get('provisional',False))
            provisional=state=='PROVISIONAL_NAME_CANDIDATE'
            return validate_resolution(dict(version=1,context=meta,state=state,reason=reason,
              person_id=hit['person_id'] if hit else None,name=hit['name'] if hit else None,modalities=kinds,
              claim_scope=('provisional_voice_candidate' if provisional else 'voice_candidate' if calibrated else 'visible_person') if hit else 'none',
              provisional=provisional,field_calibrated=calibrated,identity_verified=False,personal_memory_allowed=False,single_speaker_verified=False),meta)
        alias=None
        if anonymous is not None and self.anonymous_evidence is not None:
            try:
                candidate=validate_alias(anonymous,meta);actual=self.anonymous_evidence(meta)
                if candidate==actual and candidate['state']=='STABLE_CANDIDATE':alias=candidate
            except (ValueError,TypeError,TimeoutError,sqlite3.Error):pass
        with self._db() as db:
            for p in proofs:
                if not isinstance(p,dict) or p.get('context')!=meta or p.get('modality') not in ('face','voice'):
                    reasons.append('FOREIGN_PROOF');continue
                kind=p['modality']
                if kind in hits:return result('CONFLICT','MULTIPLE_SAME_MODALITY_PROOFS')
                limit=3 if kind=='face' else 30
                observed,expires=p.get('observed_at'),p.get('expires_at')
                provisional=(kind=='voice' and p.get('match_state')=='PROVISIONAL_NAME_CANDIDATE'
                  and p.get('field_calibrated') is False and p.get('consecutive_distinct')==3)
                accepted=(p.get('match_state')=='KNOWN' and (kind=='face' or p.get('field_calibrated') is True)) or provisional
                if (p.get('source_kind')!='actual' or not accepted or p.get('original_matcher_accepted') is not True
                    or type(observed) not in (int,float) or type(expires) not in (int,float)
                    or not math.isfinite(observed) or not math.isfinite(expires) or not observed<=now<expires<=observed+limit):
                    reasons.append('STALE_OR_UNCALIBRATED');continue
                row=db.execute("SELECT l.*,p.name FROM modality_links l JOIN linked_people p USING(person_id) WHERE l.modality=? AND l.store_id=? AND l.identity_id=? AND l.model_id=? AND l.state='ACTIVE' AND p.state='ACTIVE'",
                   (kind,p.get('store_id'),p.get('identity_id'),p.get('model_id'))).fetchone()
                if row is None:reasons.append('NO_ACTIVE_LINK');continue
                revision=p.get('gallery_revision')
                if type(revision) is not int or revision<row['revision']:reasons.append('OLD_GALLERY');continue
                if row['fingerprint'] is not None:
                    if p.get('template_fingerprint')!=row['fingerprint']:reasons.append('TEMPLATE_CHANGED');continue
                elif revision!=row['revision']:reasons.append('GALLERY_REVALIDATION_REQUIRED');continue
                hits[kind]={'person_id':row['person_id'],'name':row['name'],'provisional':provisional}
            if alias is not None and self.voice_reference is not None:
                row=db.execute("SELECT p.person_id,p.name,v.identity_id,v.store_id,v.model_id,v.revision,v.fingerprint FROM anonymous_person_links l JOIN linked_people p USING(person_id) JOIN modality_links v ON v.person_id=p.person_id AND v.modality='voice' AND v.state='ACTIVE' WHERE l.registry_epoch=? AND l.anonymous_id=? AND p.state='ACTIVE'",
                  (alias['registry_epoch'],alias['cluster_id'])).fetchone()
                if row is not None:
                    try:
                        current=self.voice_reference(row['identity_id'])
                        valid=(current['identity_id']==row['identity_id'] and current['store_id']==row['store_id'] and current['model_id']==row['model_id']
                          and current['revision']>=row['revision'] and current.get('source_kind')=='actual'
                          and (current.get('template_fingerprint')==row['fingerprint'] if row['fingerprint'] is not None else current['revision']==row['revision']))
                    except (ValueError,TypeError,KeyError,TimeoutError,sqlite3.Error):valid=False
                    if valid:hits['anonymous']={'person_id':row['person_id'],'name':row['name'],'provisional':True}
        people={hit['person_id'] for hit in hits.values()}
        if len(people)>1:return result('CONFLICT','MODALITY_IDENTITIES_DISAGREE')
        if not hits:return result('UNKNOWN',reasons[0] if reasons else 'NO_ACTIVE_MATCH')
        hit=next(iter(hits.values()))
        if all(value['provisional'] for value in hits.values()):return result('PROVISIONAL_NAME_CANDIDATE','UNCALIBRATED_ACTIVE_LINK_CANDIDATE',hit)
        return result('MATCH_CANDIDATE','ORIGINAL_MATCHER_ACTIVE_LINK',hit)
    def revoke_person(self,person_id,*,confirmed=False):
        if confirmed is not True:raise ValueError('Explicit deletion confirmation required')
        with self._db(write=True) as db:
            changed=db.execute("UPDATE linked_people SET state='REVOKED' WHERE person_id=? AND state='ACTIVE'",(person_id,)).rowcount
            db.execute("UPDATE modality_links SET state='REVOKED' WHERE person_id=?",(person_id,));db.execute('DELETE FROM anonymous_person_links WHERE person_id=?',(person_id,))
            return bool(changed)
    def health(self):
        self.expire()
        with self._db() as db:
            return dict(version=1,active_people=db.execute("SELECT count(*) FROM linked_people WHERE state='ACTIVE'").fetchone()[0],
              pending=db.execute("SELECT count(*) FROM binding_attempts WHERE state IN ('AWAIT_CONFIRMATION','SAMPLING_FACE','SAMPLING_VOICE')").fetchone()[0],
              partial=db.execute("SELECT count(*) FROM binding_attempts WHERE state LIKE 'PARTIAL_%'").fetchone()[0],
              biometric_templates_persisted=False,pcm_persisted=False,automatic_profile_access=False)
