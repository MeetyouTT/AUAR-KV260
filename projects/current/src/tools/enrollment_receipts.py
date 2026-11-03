"""Bridge real original-store commits into unsigned cross-modality receipts.

Face payloads must travel on the existing request-scoped IdentityReplyStream
token. Only its trusted server adapter may sign them for IdentityLinkRegistry.
Spoken success text is deliberately insufficient evidence.
"""
import copy,hashlib,json
from common.asr_wire import context
from board.interaction.ui_contract import identity_completion

def face_commit_payload(*,attempt_id,origin,commit,face_guard,gallery,name,command,ack,before,after,template_fingerprint=None):
    origin=context(origin);commit=context(commit)
    if command.get('action')!='identity_enroll' or command.get('params',{}).get('confirmed') is not True:
        raise ValueError('Original explicit face enrollment required')
    if command.get('params',{}).get('display_name')!=name or command.get('board_boot_id')!=origin['board_boot_id']:
        raise ValueError('Face enrollment name or boot changed')
    if not identity_completion(dict(ack,action='identity_enroll'),after):raise ValueError('Face ACK is not COMMITTED')
    if before.get('db_version')!=gallery['revision'] or after.get('db_version')!=gallery['revision']+1:
        raise ValueError('Face gallery changed during enrollment')
    replacement=command['params'].get('replace_person_id')
    old_ids={r['person_id'] for r in before.get('people',[])}
    new_ids={r['person_id'] for r in after.get('people',[])}-old_ids
    if replacement:
        if replacement not in old_ids:raise ValueError('Unknown explicitly selected replacement')
        identity=replacement
    elif len(new_ids)==1:identity=next(iter(new_ids))
    else:raise ValueError('Face commit did not identify exactly one original store record')
    if not any(r['person_id']==identity and r['display_name']==name for r in after.get('people',[])):
        raise ValueError('Committed face/name mismatch')
    return dict(version=1,attempt_id=attempt_id,origin_context=origin,commit_context=commit,modality='face',state='COMMITTED',
      operation_id=ack['command_id'],store_id=gallery['store_id'],identity_id=identity,model_id=gallery['model_id'],
      revision_before=gallery['revision'],revision_after=after['db_version'],template_fingerprint=template_fingerprint,display_name=name,
      checks=dict(quality_passed=True,explicit_confirmation=True,original_policy='original_face_enrollment',single_speaker_verified=False),
      face_guard=copy.deepcopy(face_guard),capture_ids=[],pcm_digests=[])

def existing_face_payload(*,attempt_id,origin,commit,face_guard,gallery,name,identity,confirmed_link=False,template_fingerprint=None):
    """Reuse a fresh original KNOWN face; never invent a new COMMITTED write."""
    origin=context(origin);commit=context(commit);person=face_guard['face_identity_id']
    if (confirmed_link is not True or person is None or identity.get('state')!='KNOWN' or identity.get('person_id')!=person
       or identity.get('display_name')!=name or identity.get('db_version')!=gallery['revision']
       or not any(p['person_id']==person and p['display_name']==name for p in identity.get('people',[]))):
        raise ValueError('Fresh original face match/name and explicit link consent required')
    return dict(version=1,attempt_id=attempt_id,origin_context=origin,commit_context=commit,modality='face',state='EXISTING_CONFIRMED',
      operation_id='face-existing-'+hashlib.sha256(json.dumps(commit,sort_keys=True).encode()).hexdigest()[:32],
      store_id=gallery['store_id'],identity_id=person,model_id=gallery['model_id'],revision_before=gallery['revision'],revision_after=gallery['revision'],
      template_fingerprint=template_fingerprint,display_name=name,checks=dict(quality_passed=True,explicit_confirmation=True,
        original_policy='original_face_match_and_explicit_link_consent',single_speaker_verified=False),face_guard=copy.deepcopy(face_guard),capture_ids=[],pcm_digests=[])

class SpeakerEnrollmentBridge:
    """Calls the existing three-recording workflow, including its final consent."""
    def __init__(self,device,*,anonymous_store=None,fingerprint=None):
        self.device=device;self.sessions={};self.fingerprint=fingerprint or self._fingerprint
        self.anonymous_store=anonymous_store;self.aliases={}
    @staticmethod
    def actor(meta):return meta['board_boot_id'],meta['session_id']
    def _fingerprint(self,identity):
        store=self.device.store
        row=store.db.execute('SELECT embedding FROM templates WHERE identity_id=? AND model_id=?',(identity,store.model_id)).fetchone()
        if row is None:raise ValueError('Committed voice template disappeared')
        return hashlib.sha256(row[0].encode()).hexdigest()
    def start(self,meta,pcm,*,attempt_id,origin,name,gallery,face_guard):
        context(meta,pcm);origin=context(origin);key=self.actor(meta)
        if key in self.sessions:raise ValueError('Speaker binding already active')
        if len(self.sessions)>=4:raise ValueError('Speaker binding session limit')
        if self.device.store.revision!=gallery['revision']:raise ValueError('Voice gallery changed before sampling')
        row=dict(attempt_id=attempt_id,origin=origin,name=name,gallery=copy.deepcopy(gallery),face_guard=copy.deepcopy(face_guard),captures=[],digests=[])
        reply=self.device.turn(meta,'登记我的声纹，我叫'+name,pcm)
        actual=self.device.sessions.get(self.device.key(meta))
        if not actual or actual.get('stage')!='samples' or actual.get('name')!=name:raise ValueError('Original voice enrollment did not start')
        self.sessions[key]=row
        return reply
    def turn(self,meta,text,pcm):
        context(meta,pcm);key=self.actor(meta);row=self.sessions.get(key)
        if row is None:raise ValueError('No unified speaker enrollment')
        active=self.device.sessions.get(self.device.key(meta))
        if not active or active.get('name')!=row['name']:raise ValueError('Original voice workflow changed')
        before_count=len(active.get('vectors',[]));stage=active['stage'];revision=self.device.store.revision
        ids={p['person_id'] for p in self.device.store.people()}
        # Only the combined explicit save phrase is mapped, while the original
        # SpeakerDevice continues to enforce its own confirm state and checks.
        compact=text.strip(' 。！!？?')
        forwarded='确认保存声纹' if stage=='confirm' and compact in ('确认保存身份关联','确认关联身份') else text
        alias_revision=self.anonymous_store.revision if self.anonymous_store is not None else None
        reply=self.device.turn(meta,forwarded,pcm)
        current=self.device.sessions.get(self.device.key(meta))
        if stage=='samples' and current and len(current.get('vectors',[]))==before_count+1:
            if meta['capture_id'] not in row['captures'] and meta['pcm_sha256'] not in row['digests']:
                row['captures'].append(meta['capture_id']);row['digests'].append(meta['pcm_sha256'])
                if self.anonymous_store is not None:
                    try:
                        # The original voiced_pcm gate proves at least 2.5s;
                        # reuse its accepted vector instead of encoding twice.
                        self.aliases[key]=self.anonymous_store.observe(meta,current['vectors'][-1],voiced_ms=2500,expected_revision=alias_revision)
                    except (ValueError,TimeoutError):self.aliases.pop(key,None)
        if stage!='confirm' or forwarded!='确认保存声纹':return reply,None
        if self.device.store.revision==revision:
            # A rejected duplicate/ambiguous enrollment is not a commit.
            if current is None:self.sessions.pop(key,None)
            return reply,None
        if self.device.store.revision!=revision+1 or revision!=row['gallery']['revision'] or current is not None:
            raise ValueError('Voice commit revision or workflow changed')
        created=[p for p in self.device.store.people() if p['person_id'] not in ids]
        if len(created)!=1 or created[0]['display_name']!=row['name'] or len(set(row['captures']))!=3 or len(set(row['digests']))!=3:
            raise ValueError('Original three distinct sample commit not proven')
        identity=created[0]['person_id']
        payload=dict(version=1,attempt_id=row['attempt_id'],origin_context=row['origin'],commit_context=dict(meta),modality='voice',state='COMMITTED',
          operation_id='voice-'+meta['request_id'],store_id=row['gallery']['store_id'],identity_id=identity,model_id=row['gallery']['model_id'],
          revision_before=revision,revision_after=revision+1,template_fingerprint=self.fingerprint(identity),display_name=row['name'],
          checks=dict(quality_passed=True,explicit_confirmation=True,original_policy='original_three_utterance_enrollment',single_speaker_verified=False),
          face_guard=row['face_guard'],capture_ids=list(row['captures']),pcm_digests=list(row['digests']))
        self.sessions.pop(key,None)
        return reply,payload
    def cancel(self,meta,pcm):
        context(meta,pcm);self.sessions.pop(self.actor(meta),None);self.aliases.pop(self.actor(meta),None)
        return self.device.turn(meta,'取消登记',pcm)
    def take_alias(self,meta):
        value=self.aliases.pop(self.actor(meta),None)
        return value if value is not None and value['context']==context(meta) else None
