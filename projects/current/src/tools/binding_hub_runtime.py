"""Actual Hub binding lifecycle on its existing sole CPU speaker worker.

Only the local model adapter may open a scoped exchange. Receipt signing is an
internal consequence of that exchange, not an arbitrary body/sign HTTP tool.
"""
from collections import OrderedDict
import copy,hashlib,json,os,secrets,sqlite3,time
from pathlib import Path
from common.asr_wire import context
from common.binding_api import attempt,decision,gallery,response,text,token
from common.identity_links import IdentityLinkRegistry,ReceiptAuthority
from common.speaker_turns import record
from tools.enrollment_receipts import SpeakerEnrollmentBridge
from tools.identity_resolution import face_proof
from tools.private_gallery_reference import private_gallery_reference,gallery_fields
from tools.progressive_speaker_hub import install_anonymous
from tools.unified_identity_binding import UnifiedBindingRouter
from tools.provisional_voice import query_reply

def private_key(root):
    path=Path(root)/'identity-link-receipt.key'
    if path.is_symlink():raise ValueError('Receipt key must be a private regular file')
    try:
        fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:pass
    else:
        with os.fdopen(fd,'wb') as stream:stream.write(secrets.token_bytes(32));stream.flush();os.fsync(stream.fileno())
    raw=path.read_bytes()
    if len(raw)!=32:raise ValueError('Invalid private receipt key')
    return raw

def production_private_root(root):
    root=Path(root).resolve()
    permitted=[Path(value).resolve() for value in (os.environ.get('LOCALAPPDATA'),os.environ.get('APPDATA')) if value]
    if not any(root!=base and root.is_relative_to(base) for base in permitted):
        raise ValueError('Identity stores require the existing private AppData root')
    return root

class BindingHubRuntime:
    def __init__(self,hub,config,*,clock=time.time,validate_root=production_private_root,voice_reference=None):
        validate_root(hub.root);self.hub=hub;self.clock=clock
        self.routes=OrderedDict();self.references=OrderedDict();self.gates=OrderedDict();self.reused=OrderedDict();self.packets=OrderedDict()
        self.latest=OrderedDict();self.gallery_versions=OrderedDict()
        self.current_face=None
        hub.progressive_speaker=install_anonymous(hub,config)
        if hub.progressive_speaker is None:raise ValueError('Binding requires explicit anonymous collection configuration')
        store=hub.progressive_speaker.anonymous_store;self.anonymous=store
        self.voice_reference=voice_reference or (lambda identity:private_gallery_reference(hub.root/'speakers.sqlite3',hub.speaker.encoder.model_id,
          hub.speaker.encoder.dimension,identity_id=identity,expected_application_id=hub.speaker.store.APPLICATION_ID))
        self.registry=IdentityLinkRegistry(hub.root/'identity-links.sqlite3',ReceiptAuthority(private_key(hub.root)),clock=clock,
          anonymous_lookup=store.active,anonymous_evidence=store.evidence,voice_reference=self.voice_reference)
        self.speaker=SpeakerEnrollmentBridge(hub.speaker,anonymous_store=store)
        self.router=UnifiedBindingRouter(self.registry,self.speaker,voice_gallery=lambda:gallery_fields(self.voice_reference(None)),
          face_gallery=lambda:gallery_fields(self._face_current()))
        hub.identity_links=self.registry;hub.voice_reference=self.voice_reference;hub.face_naming_proof=self.face_naming_proof
        with self.registry._db(write=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS binding_invalidations(person_id TEXT NOT NULL,modality TEXT NOT NULL,reason TEXT NOT NULL,at REAL NOT NULL)')
        self.reconcile_voice()
    @staticmethod
    def key(meta):return meta['board_boot_id'],meta['session_id'],meta['request_id']
    def _trim(self):
        now=self.clock()
        for collection in (self.routes,self.references,self.gates,self.reused,self.packets):
            for key,row in list(collection.items()):
                if row['until']<=now:collection.pop(key,None)
        for collection,limit in ((self.routes,128),(self.references,128),(self.gates,8),(self.reused,128),(self.packets,128)):
            while len(collection)>limit:collection.popitem(last=False)
    def _face_current(self):
        if self.current_face is None:raise ValueError('No actual board gallery reference')
        return self.current_face
    def _face_reference(self,meta,visual,reference):
        current=gallery(reference,meta,visual) if reference is not None else None
        self.current_face=current
        if current is not None:
            self.references[self.key(meta)]={'meta':dict(meta),'value':current,'observed':self.clock(),'until':self.clock()+120}
            self._invalidate_changed_reference('face',current)
        return current
    def face_naming_proof(self,meta,visual):
        self._trim();row=self.references.get(self.key(meta))
        if row is None or row['meta']!=meta or self.clock()-row['observed']>3:return None
        return face_proof(meta,visual,row['value'],now=row['observed'])
    def _invalidate(self,person,modality,reason):
        # Revokes only derived associations; never deletes original templates,
        # audio or memory. Existing original consent preceded original deletes.
        with self.registry._db(write=True) as db:
            changed=db.execute("UPDATE linked_people SET state='INVALIDATED' WHERE person_id=? AND state='ACTIVE'",(person,)).rowcount
            db.execute("UPDATE modality_links SET state='INVALIDATED' WHERE person_id=?",(person,))
            db.execute('DELETE FROM anonymous_person_links WHERE person_id=?',(person,))
            if changed:db.execute('INSERT INTO binding_invalidations VALUES(?,?,?,?)',(person,modality,reason,self.clock()))
        return bool(changed)
    def revoke_derived_identity(self,person_id,*,reason='ORIGINAL_AUTHORIZATION_REVOKED'):
        """Internal original authorization callback; intentionally no HTTP route."""
        if reason not in ('ORIGINAL_AUTHORIZATION_REVOKED','ORIGINAL_FACE_DELETED','ORIGINAL_VOICE_DELETED','ORIGINAL_TEMPLATE_CHANGED'):
            raise ValueError('Invalid original revocation event')
        return self._invalidate(person_id,'original',reason)
    def _links(self,modality):
        with self.registry._db() as db:
            return [dict(row) for row in db.execute("SELECT l.* FROM modality_links l JOIN linked_people p USING(person_id) WHERE l.modality=? AND l.state='ACTIVE' AND p.state='ACTIVE'",(modality,))]
    def reconcile_voice(self):
        changed=0
        for row in self._links('voice'):
            try:current=self.voice_reference(row['identity_id'])
            except ValueError:
                # The original model-bound identity/template is absent in a
                # successful read-only transaction. Busy/IO failures do not revoke.
                changed+=self._invalidate(row['person_id'],'voice','ORIGINAL_VOICE_DELETED');continue
            except (OSError,sqlite3.Error,TimeoutError):continue
            if (current['store_id']!=row['store_id'] or current['model_id']!=row['model_id']
               or current.get('template_fingerprint')!=row['fingerprint']):
                changed+=self._invalidate(row['person_id'],'voice','ORIGINAL_TEMPLATE_CHANGED')
        return changed
    def _invalidate_changed_reference(self,modality,current):
        identity=current.get('identity_id')
        if identity is None:return 0
        changed=0
        for row in self._links(modality):
            if row['identity_id']==identity and (row['store_id']!=current['store_id'] or row['model_id']!=current['model_id']
                or row['fingerprint'] is not None and row['fingerprint']!=current.get('template_fingerprint')):
                changed+=self._invalidate(row['person_id'],modality,'ORIGINAL_TEMPLATE_CHANGED')
        return changed
    def state(self,meta):
        meta=context(meta);self._trim();actor=self.router.actor(meta)
        return dict(version=1,context=meta,binding_active=actor in self.router.active,name_waiting=actor in self.router.name_waiting,
          original_speaker=self.hub.speaker.state(meta),automatic_profile_access=False)
    def _control_evidence(self,meta,visual=None,*,voice=None,identity=None):
        alias=None
        try:alias=self.anonymous.evidence(meta)
        except (ValueError,TimeoutError,sqlite3.Error):pass
        self.reused[self.key(meta)]={'meta':dict(meta),'anonymous':alias,'visual':visual,'voice':voice,'identity':identity,'until':self.clock()+600}
        self._trim()
    def precomputed_analysis(self,meta,cid,visual=None):
        row=self.reused.get(self.key(context(meta)))
        if row is None or row['until']<=self.clock():return None
        if row['meta']!=meta:raise ValueError('Foreign precomputed enrollment evidence')
        return record(meta,cid,status='COMPLETE',reason='ORIGINAL_ENROLLMENT_CAPTURE_REUSED',visual=visual,
          voice=row.get('voice'),anonymous=row['anonymous'],identity=row.get('identity'))
    def ingest_gallery(self,packet):
        from common.face_binding_wire import validate_packet,packet_sha256
        packet=validate_packet(packet);meta=context(packet['context']);digest=packet_sha256(packet)
        if len(json.dumps({'context':meta,'packet':packet},ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())>24576:
            raise ValueError('Gallery transport body exceeds original bounded route')
        self._trim();old=self.packets.get(self.key(meta));namespace=(packet['gallery']['store_id'],packet['gallery']['model_id'])
        prior=self.gallery_versions.get(namespace);signature=hashlib.sha256(json.dumps(packet['inventory'],separators=(',',':')).encode()).hexdigest()
        if prior is not None and (packet['gallery']['revision']<prior[0] or packet['gallery']['revision']==prior[0] and signature!=prior[1]):
            raise ValueError('Old or inconsistent gallery inventory')
        if old is not None and (old['meta']!=meta or old['digest']!=digest):raise ValueError('Gallery capture packet was replaced')
        self.packets[self.key(meta)]={'meta':meta,'digest':digest,'packet':packet,'until':self.clock()+120}
        self.gallery_versions[namespace]=(packet['gallery']['revision'],signature);self.gallery_versions.move_to_end(namespace)
        while len(self.gallery_versions)>8:self.gallery_versions.popitem(last=False)
        current=packet['gallery'];inventory=dict(packet['inventory'])
        for row in self._links('face'):
            # Complete bounded inventory is a successful actual-model readback.
            # Namespace changes invalidate derived associations conservatively.
            if row['store_id']!=current['store_id'] or row['model_id']!=current['model_id']:
                self._invalidate(row['person_id'],'face','ORIGINAL_TEMPLATE_CHANGED')
            elif current['revision']>=row['revision']:
                fingerprint=inventory.get(row['identity_id'])
                if fingerprint is None:self._invalidate(row['person_id'],'face','ORIGINAL_FACE_DELETED')
                elif row['fingerprint'] is not None and fingerprint!=row['fingerprint']:
                    self._invalidate(row['person_id'],'face','ORIGINAL_TEMPLATE_CHANGED')
        return dict(accepted=True,packet_sha256=digest)
    def _gallery_for(self,meta,digest):
        if digest is None:return None
        row=self.packets.get(self.key(meta))
        if row is None or row['meta']!=meta or row['digest']!=digest or row['until']<=self.clock():raise ValueError('No matching accepted board gallery packet')
        packet=row['packet'];reference=dict(packet['gallery'])
        if packet['current'] is not None:reference.update(packet['current'])
        return reference
    def _identity_query(self,meta,utterance,pcm,visual):
        if query_reply(utterance,{'state':'UNKNOWN'}) is None:return None
        from tools.identity_resolution import voice_proof
        voice,alias=self.hub.progressive_speaker.analyze(meta,pcm)
        proofs=[];reference=self.voice_reference(None)
        p=self.hub.progressive_speaker.provisional.proof(meta,store_id=reference['store_id'])
        if voice['state']=='CANDIDATE':
            # Continue the existing tracker's three-distinct-capture streak;
            # a query does not bypass its original stability requirement.
            tracker=self.hub.speaker_turns;actor=tracker.actor(meta);old=tracker.streaks.get(actor);now=tracker.clock()
            signature=(voice['model_id'],voice['gallery_revision'],voice['candidate_id']);count=1
            if old and old['signature']==signature and now-old['at']<=30:
                distinct=meta['pcm_sha256'] not in old['digests'] and meta['capture_id'] not in old['captures']
                count=min(3,old['count']+int(distinct));digests=(old['digests']+[meta['pcm_sha256']])[-3:] if distinct else old['digests'];captures=(old['captures']+[meta['capture_id']])[-3:] if distinct else old['captures']
            else:digests=[meta['pcm_sha256']];captures=[meta['capture_id']]
            tracker.streaks[actor]=dict(signature=signature,count=count,digests=digests,captures=captures,at=now)
            tracker.streaks.move_to_end(actor)
            while len(tracker.streaks)>32:tracker.streaks.popitem(last=False)
            voice=dict(voice,consecutive_distinct=count,state='CANDIDATE_STABLE' if count==3 else 'CANDIDATE')
            p=voice_proof(self.hub.speaker,meta,voice,store_id=reference['store_id'],now=self.clock())
        if p is not None:proofs.append(p)
        p=self.face_naming_proof(meta,visual)
        if p is not None:proofs.append(p)
        result=self.registry.resolve(meta,proofs,anonymous=alias)
        self._control_evidence(meta,visual,voice=voice,identity=result)
        return query_reply(utterance,result)
    def route(self,meta,utterance,pcm,*,visual=None,gallery_digest=None):
        meta=context(meta,pcm);text(utterance);self._trim();self.reconcile_voice()
        actor=self.router.actor(meta);previous=self.latest.get(actor)
        if previous is not None and (meta['generation']<previous[0] or meta['generation']==previous[0] and meta['request_id']!=previous[1]):
            raise ValueError('Stale binding generation')
        self.latest[actor]=(meta['generation'],meta['request_id']);self.latest.move_to_end(actor)
        while len(self.latest)>32:self.latest.popitem(last=False)
        fingerprint=hashlib.sha256(json.dumps([utterance,visual,gallery_digest],sort_keys=True,separators=(',',':')).encode()).hexdigest();old=self.routes.get(self.key(meta))
        if old is not None:
            if old['meta']!=meta or old['fingerprint']!=fingerprint:raise ValueError('Binding request reused with different content')
            return copy.deepcopy(old['response'])
        reference=self._gallery_for(meta,gallery_digest)
        self._face_reference(meta,visual,reference)
        alias=None
        try:alias=self.anonymous.evidence(meta)
        except (ValueError,TimeoutError,sqlite3.Error):pass
        active_attempt=self.router.active.get(actor)
        if active_attempt is not None:
            state=self.registry.attempt(active_attempt,meta)['state']
            if state in ('EXPIRED','PARTIAL_EXPIRED','CANCELLED','PARTIAL_CANCELLED','PARTIAL_CONFLICT') and actor in self.speaker.sessions:
                # The derived deadline can expire before the original voice
                # session; release it before ordinary speech can hit legacy turn.
                self.speaker.cancel(meta,pcm)
        routed=self.router.route(meta,utterance,pcm,visual=visual,anonymous=alias)
        identity_query=None
        if routed['route']=='ordinary':
            identity_query=self._identity_query(meta,utterance,pcm,visual)
            if identity_query is not None:routed=self.router.decision('device_reply',reply=identity_query,reason='EXPLICIT_IDENTITY_QUERY')
        if routed['route']=='face_exchange':routed=dict(routed,reply=None)
        request=None
        if routed['route']=='face_exchange':
            actor=self.router.actor(meta);waiting=self.router.name_waiting.get(actor)
            if waiting is not None and waiting['ticket']==routed['attempt_id']:
                origin=waiting['context'];guard=waiting['face_guard'];name='';confirmed=False
            else:
                row=self.registry.attempt(routed['attempt_id'],meta);origin=json.loads(row['origin']);guard=json.loads(row['face_guard']);name=row['name'] or ''
                confirmed=(guard['face_identity_id'] is not None and row['confirmed_context'] is not None)
            request=dict(version=1,attempt_id=routed['attempt_id'],origin_context=origin,face_guard=guard,name=name,
              board_text=routed['board_text'],confirmed_existing=confirmed)
        controlled=routed['route'] in ('face_exchange','device_reply')
        if controlled and identity_query is None:self._control_evidence(meta,visual)
        result=response(dict(version=1,context=meta,decision=decision(routed),binding_request=request,
          analysis_mode='CONTROL_REUSED' if controlled else 'TRACKER'),meta)
        self.routes[self.key(meta)]={'meta':meta,'fingerprint':fingerprint,'response':result,'until':self.clock()+120};self._trim()
        return copy.deepcopy(result)
    def open_exchange(self,meta,attempt_id,exchange_token,timeout):
        meta=context(meta);attempt(attempt_id);token(exchange_token);self._trim()
        row=self.routes.get(self.key(meta))
        if row is None or row['meta']!=meta or row['response']['decision']['route']!='face_exchange' or row['response']['decision']['attempt_id']!=attempt_id:
            raise ValueError('No matching face route for this exchange')
        if type(timeout) not in (int,float) or not 0<timeout<=110:raise ValueError('Invalid exchange deadline')
        cap=secrets.token_hex(32)
        self.gates[cap]=dict(meta=meta,attempt=attempt_id,token=exchange_token,until=self.clock()+timeout)
        self._trim();return dict(version=1,context=meta,capability=cap)
    def face_result(self,meta,pcm,attempt_id,exchange_token,capability,reply,*,binding_receipt=None,final=True):
        meta=context(meta,pcm);attempt(attempt_id);token(exchange_token);self._trim();gate=self.gates.get(capability)
        if (gate is None or gate['meta']!=meta or gate['attempt']!=attempt_id or gate['token']!=exchange_token
           or self.latest.get(self.router.actor(meta))!=(meta['generation'],meta['request_id'])
           or type(final) is not bool):raise ValueError('Foreign or expired original identity exchange')
        signed=None
        if binding_receipt is not None:
            if not final or reply.get('code') not in ('registered','already_known'):raise ValueError('Unexpected original face receipt')
            # Validate all exact original policy/owner fields before signing.
            row=self.registry.attempt(attempt_id,meta)
            candidate=self.registry.authority.sign(binding_receipt)
            checked=self.registry._receipt(row,candidate)
            if checked['modality']!='face' or checked['commit_context']!=meta:raise ValueError('Face receipt belongs to another completion')
            signed=candidate
        value=self.router.face_result(meta,pcm,attempt_id,reply,signed)
        if final:self.gates.pop(capability,None)
        self._control_evidence(meta)
        return dict(version=1,context=meta,reply=text(value,240),personal_memory_allowed=False)
    def after_original_voice_turn(self,meta,utterance):
        """Actual hook after legacy SpeakerDevice.turn, including confirmed delete."""
        context(meta);self.reconcile_voice();self._control_evidence(meta)
    def health(self):
        self._trim()
        return dict(version=1,enabled=True,registry=self.registry.health(),private_key_persisted=True,
          scoped_exchanges=len(self.gates),maximum_scoped_exchanges=8,pcm_persisted=False,automatic_profile_access=False)
