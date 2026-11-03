"""Build private-data-free RAM diagnostics; never runs production code."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent
BASE = LIVE/'start_sync_fix/candidate_runtime'
TARGET = HERE/'candidate_runtime_v2'
assert not TARGET.exists()
TARGET.mkdir()
for path in BASE.rglob('*.py'):
    if '__pycache__' in path.parts: continue
    out = TARGET/path.relative_to(BASE)
    out.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,out)
(TARGET/'config').mkdir(exist_ok=True)
for public_name in ('character_profile.local.json','board_dialogue_model.json'):
    public_selection=BASE/'config'/public_name
    assert public_selection.is_file() and not public_selection.is_symlink() and public_selection.stat().st_size<=8192
    shutil.copyfile(public_selection,TARGET/'config'/public_name)
router = LIVE/'workflow_review/unified_identity_binding.current_a6d4.py'
assert hashlib.sha256(router.read_bytes()).hexdigest() == '85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
shutil.copyfile(router,TARGET/'tools/unified_identity_binding.py')

BEFORE = {
 'board/identity/voice_enrollment.py':'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb',
 'common/identity_links.py':'e623e5d15f81f5f66505b6345c6f807270409fea67a60f506c61e1f021b7150b',
 'board/runtime/board_speaker_business.py':'6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816',
 'board/runtime/board_business.py':'b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2',
}
originals = {}
for name,sha in BEFORE.items():
    raw=(BASE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
    originals[name]=raw.decode('utf-8')

voice = originals['board/identity/voice_enrollment.py']
voice=voice.replace('self.reset()',"self.reset(trace_source='INTERNAL')")
ctor="        self.lock=threading.RLock();self.reset(trace_source='INTERNAL')"
assert voice.count(ctor)==1
voice=voice.replace(ctor,"        self.lock=threading.RLock();self.reset(trace_source='INITIALIZE')")
reset="    def reset(self):\n        with self.lock:\n"
assert voice.count(reset)==1
voice=voice.replace(reset,"""    def reset(self,*,trace_source='EXTERNAL'):
        with self.lock:
            # Keep the last failed handle trace visible after ordinary cleanup.
            old=dict(getattr(self,'_reset_trace',{}))
            source=trace_source if trace_source in ('INITIALIZE','INTERNAL','EXTERNAL') else 'other'
            def count(key):
                value=old.get(key,0)
                return value if type(value) is int and 0<=value<2**53-1 else 0
            phase=getattr(self,'stage',None)
            self._reset_trace={'count':count('count')+1,'source':source,
                'internal_count':count('internal_count')+int(source=='INTERNAL'),
                'external_count':count('external_count')+int(source=='EXTERNAL'),
                'phase':phase if phase in ('idle','name','authorize','sampling','confirm') else None,
                'gate':self.confirmation_diagnostics()['gate'],
                'had_sampling':bool(getattr(self,'sampling_id',''))}
""")
anchor='    def handle(self,text,capture_snapshot,*,is_current=lambda:True):\n'
assert voice.count(anchor)==1
helpers='''    def confirmation_diagnostics(self):
        """Fixed enums/booleans only; no name, owner value, text, PCM or token."""
        with self.lock:
            value=dict(getattr(self,'_confirmation_trace',{}))
        phases={'idle','name','authorize','sampling','confirm'}
        gates={'HANDLE','IDENTITY_QUERY','CANCEL','EXPIRED','NOT_ENROLLMENT',
            'CURRENT_SNAPSHOT','CAPTURE_MISSING','CAPTURE_NOT_ACTUAL','CURRENT_NOT_ACTUAL',
            'CAPTURE_CURRENT_OWNER','CAPTURE_SINGLE','CURRENT_SINGLE','CURRENT_TARGET',
            'READY_WINDOW_RETAINED','WORKFLOW_OWNER','KNOWN_FACE','CAPABILITY',
            'ORIGINAL_FLOW','SAMPLING_START','ENROLL_SUBMIT','RAISED'}
        def fixed(key,allowed):
            item=value.get(key)
            return item if type(item) is str and item in allowed else None
        result={'version':1,'phase_enter':fixed('phase_enter',phases),'phase_exit':fixed('phase_exit',phases),
            'gate':fixed('gate',gates),'reply_code':fixed('reply_code',speech.PROMPTS),
            'exception':fixed('exception',{'ValueError','TypeError','KeyError','OSError','RuntimeError','InterruptedError','other'})}
        for key in ('capture_present','capture_actual','current_snapshot_valid','current_actual',
                    'capture_single','current_single','capture_current_owner_equal',
                    'workflow_owner_equal','identity_enroll','identity_sample_start'):
            result[key]=value.get(key) if type(value.get(key)) is bool else None
        with self.lock:reset=dict(getattr(self,'_reset_trace',{}))
        for key in ('count','internal_count','external_count'):
            item=reset.get(key)
            result['reset_'+key]=item if type(item) is int and 0<=item<2**53 else 0
        result['reset_source']=reset.get('source') if reset.get('source') in ('INITIALIZE','INTERNAL','EXTERNAL','other') else None
        result['reset_phase']=reset.get('phase') if reset.get('phase') in ('idle','name','authorize','sampling','confirm') else None
        item=reset.get('gate');result['reset_gate']=item if type(item) is str and item in gates else None
        result['reset_had_sampling']=reset.get('had_sampling') if type(reset.get('had_sampling')) is bool else None
        return result

    def _trace_confirmation(self,**values):
        # Never retain a supplied snapshot, target, command, reply or exception.
        enums={'phase_enter':{'idle','name','authorize','sampling','confirm'},
            'phase_exit':{'idle','name','authorize','sampling','confirm'},
            'gate':{'HANDLE','IDENTITY_QUERY','CANCEL','EXPIRED','NOT_ENROLLMENT','CURRENT_SNAPSHOT',
                'CAPTURE_MISSING','CAPTURE_NOT_ACTUAL','CURRENT_NOT_ACTUAL','CAPTURE_CURRENT_OWNER',
                'CAPTURE_SINGLE','CURRENT_SINGLE','CURRENT_TARGET','READY_WINDOW_RETAINED','WORKFLOW_OWNER',
                'KNOWN_FACE','CAPABILITY','ORIGINAL_FLOW','SAMPLING_START','ENROLL_SUBMIT','RAISED'},
            'reply_code':speech.PROMPTS,'exception':{'ValueError','TypeError','KeyError','OSError','RuntimeError','InterruptedError','other'}}
        booleans={'capture_present','capture_actual','current_snapshot_valid','current_actual','capture_single',
            'current_single','capture_current_owner_equal','workflow_owner_equal','identity_enroll','identity_sample_start'}
        with self.lock:
            old=dict(getattr(self,'_confirmation_trace',{}))
            for key,value in values.items():
                if key in booleans:old[key]=value if type(value) is bool else None
                elif key in enums:old[key]=value if type(value) is str and value in enums[key] else None
            self._confirmation_trace=old

    def handle(self,text,capture_snapshot,*,is_current=lambda:True):
        with self.lock:
            previous_trace=dict(getattr(self,'_confirmation_trace',{}))
            self._confirmation_trace={'phase_enter':self.stage if self.stage in ('idle','name','authorize','sampling','confirm') else None,'gate':'HANDLE',
                'capture_present':capture_snapshot is not None,
                'capture_actual':isinstance(capture_snapshot,dict) and capture_snapshot.get('source_kind')=='actual'}
        try:
            reply=self._handle(text,capture_snapshot,is_current=is_current)
        except BaseException as error:
            kind=type(error).__name__
            self._trace_confirmation(phase_exit=self.stage,exception=kind if kind in
                {'ValueError','TypeError','KeyError','OSError','RuntimeError','InterruptedError'} else 'other')
            raise
        if reply is None:
            with self.lock:
                if self._confirmation_trace.get('gate')=='NOT_ENROLLMENT':
                    self._confirmation_trace=previous_trace
                    return None
        self._trace_confirmation(phase_exit=self.stage,
            reply_code=reply.get('code') if isinstance(reply,dict) and type(reply.get('code')) is str and reply.get('code') in speech.PROMPTS else None)
        return reply

    def _handle(self,text,capture_snapshot,*,is_current=lambda:True):
'''
voice=voice.replace(anchor,helpers)
patches=[
 ("        if speech.identity_query_requested(text):\n", "        if speech.identity_query_requested(text):\n            self._trace_confirmation(gate='IDENTITY_QUERY')\n"),
 ("            if speech.cancelled(text):self.reset();return speech.result('cancelled')", "            if speech.cancelled(text):\n                self._trace_confirmation(gate='CANCEL');self.reset();return speech.result('cancelled')"),
 ("            if active and self.clock()>=self.until:self.reset();return speech.result('expired')", "            if active and self.clock()>=self.until:\n                self._trace_confirmation(gate='EXPIRED');self.reset();return speech.result('expired')"),
 ("            if not active and not speech.enrollment_requested(text):return None", "            if not active and not speech.enrollment_requested(text):\n                self._trace_confirmation(gate='NOT_ENROLLMENT');return None"),
 ("        current=None\n        try:\n            now=self.now_ms();current=validate_snapshot(self.snapshot(),self.boot,now)", "        current=None\n        self._trace_confirmation(gate='CURRENT_SNAPSHOT',current_snapshot_valid=False)\n        try:\n            now=self.now_ms();current=validate_snapshot(self.snapshot(),self.boot,now)\n            self._trace_confirmation(current_snapshot_valid=True,current_actual=current['source_kind']=='actual',\n                identity_enroll=current['capabilities'].get('identity_enroll') is True,\n                identity_sample_start=current['capabilities'].get('identity_sample_start') is True)"),
 ("            if not capture_snapshot or capture_snapshot['source_kind']!='actual':raise ValueError('No capture-start owner')", "            if not capture_snapshot:\n                self._trace_confirmation(gate='CAPTURE_MISSING');raise ValueError('No capture-start owner')\n            if capture_snapshot['source_kind']!='actual':\n                self._trace_confirmation(gate='CAPTURE_NOT_ACTUAL');raise ValueError('No capture-start owner')"),
 ("            if current['source_kind']!='actual' or self.owner_of(capture_snapshot)!=self.owner_of(current):raise ValueError('Capture owner changed')", "            if current['source_kind']!='actual':\n                self._trace_confirmation(gate='CURRENT_NOT_ACTUAL');raise ValueError('Capture owner changed')\n            same=self.owner_of(capture_snapshot)==self.owner_of(current)\n            self._trace_confirmation(gate='CAPTURE_CURRENT_OWNER',capture_current_owner_equal=same)\n            if not same:raise ValueError('Capture owner changed')"),
 ("            if (not self.single_target(capture_snapshot) or not self.single_target(current)\n                    or not self.selected_target(current)):raise ValueError('Ambiguous target')", "            capture_single=self.single_target(capture_snapshot);current_single=self.single_target(current)\n            self._trace_confirmation(capture_single=capture_single,current_single=current_single)\n            if not capture_single:\n                self._trace_confirmation(gate='CAPTURE_SINGLE');raise ValueError('Ambiguous target')\n            if not current_single:\n                self._trace_confirmation(gate='CURRENT_SINGLE');raise ValueError('Ambiguous target')\n            if not self.selected_target(current):\n                self._trace_confirmation(gate='CURRENT_TARGET');raise ValueError('Ambiguous target')"),
 ("                if epoch==self.epoch and is_current() and self._keep_ready(current):\n                    return speech.result", "                if epoch==self.epoch and is_current() and self._keep_ready(current):\n                    self._trace_confirmation(gate='READY_WINDOW_RETAINED')\n                    return speech.result"),
 ("            if active and owner!=self.owner:\n", "            self._trace_confirmation(gate='WORKFLOW_OWNER',workflow_owner_equal=owner==self.owner)\n            if active and owner!=self.owner:\n"),
 ("            if identity.get('state')=='KNOWN':self.reset();return speech.result('already_known')", "            if identity.get('state')=='KNOWN':\n                self._trace_confirmation(gate='KNOWN_FACE');self.reset();return speech.result('already_known')"),
 ("            if not (current['capabilities'].get('identity_enroll') or\n", "            self._trace_confirmation(gate='CAPABILITY')\n            if not (current['capabilities'].get('identity_enroll') or\n"),
 ("            if not active:\n                self.stage='name'", "            self._trace_confirmation(gate='ORIGINAL_FLOW')\n            if not active:\n                self.stage='name'"),
 ("            if self.stage=='authorize':return self._start_simple(current,is_current=is_current)", "            if self.stage=='authorize':\n                self._trace_confirmation(gate='SAMPLING_START')\n                return self._start_simple(current,is_current=is_current)"),
 ("            ack=self.command(command)\n            latest=validate_snapshot", "            self._trace_confirmation(gate='ENROLL_SUBMIT')\n            ack=self.command(command)\n            latest=validate_snapshot"),
]
for old,new in patches:
    old=old.replace('self.reset()',"self.reset(trace_source='INTERNAL')")
    new=new.replace('self.reset()',"self.reset(trace_source='INTERNAL')")
    assert voice.count(old)==1,(old,voice.count(old))
    voice=voice.replace(old,new)

links=originals['common/identity_links.py']
start=links.index('    def confirm(self,attempt_id,meta,text,visual):\n')
end=links.index('    def _receipt(self,row,envelope):\n',start)
new_confirm='''    def confirmation_diagnostics(self):
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
                    trace[label]=isinstance(original_guard,dict) and key in original_guard and guard[key]==original_guard[key]
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
'''
links=links[:start]+new_confirm+links[end:]

speaker=originals['board/runtime/board_speaker_business.py']
anchor="        with self.lock:\n            self.public_state = value\n"
assert speaker.count(anchor)==1
speaker=speaker.replace(anchor,"        if binding is not None:\n            value['confirmation_trace']=binding.registry.confirmation_diagnostics()\n"+anchor)

business=originals['board/runtime/board_business.py']
anchor="    def public(self):\n        state = self.flow.public()\n"
assert business.count(anchor)==1
business=business.replace(anchor,anchor+"        state['confirmation_trace']={'face':self.flow.confirmation_diagnostics()}\n")
anchor="                         speaker=self.business.public())\n        return state\n"
assert business.count(anchor)==1
business=business.replace(anchor,"                         speaker=self.business.public())\n            state['confirmation_trace']['unified']=copy.deepcopy(state['speaker'].get('confirmation_trace'))\n        return state\n")

modified={'board/identity/voice_enrollment.py':voice,'common/identity_links.py':links,
          'board/runtime/board_speaker_business.py':speaker,'board/runtime/board_business.py':business}
manifest=[];diff=[]
for name,source in modified.items():
    ast.parse(source)
    path=TARGET/name
    path.write_text(source,encoding='utf-8',newline='\n')
    manifest.append({'file':name,'before_sha256':BEFORE[name],'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    diff.extend(difflib.unified_diff(originals[name].splitlines(True),source.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(HERE/'CANDIDATE.diff').write_text(''.join(diff),encoding='utf-8')
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps({'schema':'aura-confirmation-fixed-metadata-candidate-1',
    'status':'LOCAL_ONLY_NOT_DEPLOYED','changed_files':manifest,'router_unchanged_sha256':hashlib.sha256((TARGET/'tools/unified_identity_binding.py').read_bytes()).hexdigest(),
    'production_changed':False,'board_accessed':False,'new_endpoint':False,'raw_private_values_retained':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changed_files':manifest,'router_preserved':True}))
