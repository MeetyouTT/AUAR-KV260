"""Board owns target binding, oral confirmation and the enrollment transaction."""
import copy
import threading
import time
import uuid
from common import voice_enrollment as speech
from board.interaction.ui_contract import millis,validate_snapshot,identity_completion,validate_ack

class VoiceEnrollment:
    def __init__(self,boot_id,snapshot,command,*,clock=time.monotonic,now_ms=millis,simple=False):
        self.boot=boot_id;self.snapshot=snapshot;self.command=command;self.clock=clock
        self.now_ms=now_ms
        self.simple=simple
        self.lock=threading.RLock();self.reset(trace_source='INITIALIZE')

    def reset(self,*,trace_source='EXTERNAL'):
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
            sampling_id=getattr(self,'sampling_id','')
            self.stage='idle';self.name='';self.owner=None;self.until=0;self.epoch=uuid.uuid4().hex
            self.sampling_id=''
            self.replace_id=''
            self.authorized=False
        if sampling_id:
            threading.Thread(target=self._cancel_sample,args=(sampling_id,),daemon=True).start()

    def _send(self, action, params, snapshot):
        now=self.now_ms()
        return self.command({'protocol_version':'aura-ui-1','board_boot_id':self.boot,'service_epoch':snapshot['service_epoch'],
            'command_id':'voice-'+uuid.uuid4().hex,'ui_epoch':self.epoch,'ui_generation':0,'context':snapshot['context'],
            'snapshot_sequence':snapshot['sequence'],'issued_mono_ms':now,'deadline_mono_ms':now+2500,
            'action':action,'params':params})

    def _cancel_sample(self, session_id):
        try:
            snapshot=self.snapshot()
            if snapshot['modules'].get('identity',{}).get('enrollment_sampling',{}).get('session_id')==session_id:
                self._send('identity_sample_cancel',{'session_id':session_id},snapshot)
        except (OSError,ValueError,KeyError,TypeError):pass

    def guide(self, emit, *, is_current=lambda:True):
        """Separate monitor: PCM reception/playback continues while sampling."""
        with self.lock:epoch=self.epoch;owner=copy.deepcopy(self.owner);session_id=self.sampling_id
        previous='front'
        try:
            while is_current():
                with self.lock:
                    if epoch!=self.epoch or self.stage!='sampling':raise InterruptedError('Sampling cancelled')
                current=validate_snapshot(self.snapshot(),self.boot,self.now_ms())
                sample=current['modules']['identity'].get('enrollment_sampling',{})
                if sample.get('session_id')!=session_id:raise ValueError('Sampling replaced')
                stage=sample.get('stage')
                actual_owner=self.owner_of(current)
                if actual_owner!=owner:
                    if actual_owner[:2]!=owner[:2] or actual_owner[3]!=owner[3]:raise ValueError('Sampling owner changed')
                    # Only the board camera's biometric-verified session binding
                    # may follow a recovered track. A geometric key alone cannot.
                    bound=sample.get('bound_target')
                    if (actual_owner[2] is not None and bound==actual_owner[2]
                            and bound['camera_epoch']==owner[2]['camera_epoch']):
                        with self.lock:
                            if epoch!=self.epoch:raise InterruptedError('Sampling cancelled')
                            self.owner=copy.deepcopy(actual_owner);owner=copy.deepcopy(actual_owner)
                    else:
                        if stage=='failed':
                            self.reset(trace_source='INTERNAL');emit(speech.result('sample_failed'),True);return
                        if self.clock()>=self.until:raise ValueError('Sampling timeout')
                        time.sleep(.15);continue
                if stage=='ready':
                    if self.authorized:
                        if self.clock()>=self.until:raise ValueError('Sampling timeout')
                        saved=self._save_ready(current,epoch,is_current)
                        if saved is None:
                            time.sleep(.15);continue
                        if saved:
                            with self.lock:self.sampling_id=''
                        self.reset(trace_source='INTERNAL');emit(speech.result('registered' if saved else 'failed'),True);return
                    with self.lock:
                        if epoch!=self.epoch:raise InterruptedError('Sampling cancelled')
                        self.stage='confirm';self.until=self.clock()+60;name=self.name
                        code='confirm_update_name' if self.replace_id else 'confirm_name'
                    emit(speech.result(code,name),True);return
                if stage=='failed':
                    self.reset(trace_source='INTERNAL');emit(speech.result('sample_failed'),True);return
                if self.clock()>=self.until:raise ValueError('Sampling timeout')
                # Automatic save removes the last confirmation, not the cue
                # that tells a naturally turning user when to face the lens.
                if stage!=previous and stage in ('left','right','validate') and (not self.authorized or stage=='validate'):
                    emit(speech.result('sample_'+stage),False);previous=stage
                time.sleep(.15)
            raise InterruptedError('Sampling request no longer current')
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            self.reset(trace_source='INTERNAL')
            if is_current():
                try:emit(speech.result('sample_failed'),True)
                except (OSError,ValueError):pass
        except InterruptedError:
            self.reset(trace_source='INTERNAL')

    def _save_ready(self, snapshot, epoch, is_current):
        """Use the upfront consent only for this name, revision and sample token."""
        with self.lock:
            if epoch!=self.epoch or not is_current():raise InterruptedError('Cancelled before automatic save')
            sample=snapshot['modules']['identity'].get('enrollment_sampling',{})
            if (not self.authorized or self.stage!='sampling' or sample.get('session_id')!=self.sampling_id
                    or sample.get('stage')!='ready' or self.owner_of(snapshot)!=self.owner):
                raise ValueError('Automatic enrollment ownership changed')
            if not snapshot['capabilities'].get('identity_enroll'):return None
            params={'target':copy.deepcopy(self.selected_target(snapshot)),'display_name':self.name,
                    'confirmed':True,'sampling_session_id':self.sampling_id}
            if self.replace_id:params.update(replace_person_id=self.replace_id,db_version=self.owner[3])
            ack=self._send('identity_enroll',params,snapshot)
            # A rejected command has not written; wait for another fresh frame.
            # A missing/uncertain response must fail, never retry a write blindly.
            if ack.get('accepted') is False:return None
            latest=validate_snapshot(self.snapshot(),self.boot,self.now_ms())
            return bool(identity_completion(dict(ack,action='identity_enroll'),latest['modules']['identity']))

    def _prepare(self,name,current):
        identity=current['modules']['identity']
        existing=next((p for p in identity['people'] if p['display_name'].casefold()==name.casefold()),None)
        self.name=name;self.replace_id=existing['person_id'] if existing else ''
        self.stage='authorize';self.until=self.clock()+120
        return speech.result('prepare_update_name' if self.replace_id else 'prepare_name',name)

    def _start_simple(self,current,*,is_current=lambda:True):
        epoch=self.epoch;owner=copy.deepcopy(self.owner);bound_id=''
        previous=current['modules']['identity'].get('enrollment_sampling',{}).get('session_id','')
        started=self.clock();publish_until=min(self.until,started+2.5)
        def discard():
            # Never reset/cancel a later local workflow or an unrelated token.
            if (epoch==self.epoch and self.owner==owner
                    and self.sampling_id in ('',bound_id)):
                self.reset(trace_source='INTERNAL')
        try:
            if not is_current():raise InterruptedError('Stale sampling start')
            params={'target':copy.deepcopy(self.selected_target(current))}
            if self.replace_id:params.update(replace_person_id=self.replace_id,db_version=owner[3])
            now=self.now_ms()
            command={'protocol_version':'aura-ui-1','board_boot_id':self.boot,
                'service_epoch':current['service_epoch'],'command_id':'voice-'+uuid.uuid4().hex,
                'ui_epoch':epoch,'ui_generation':0,'context':current['context'],
                'snapshot_sequence':current['sequence'],'issued_mono_ms':now,
                'deadline_mono_ms':now+2500,'action':'identity_sample_start','params':params}
            ack=self.command(command)  # Exactly once; an unknown outcome is never resent.
            ack_seen_ms=self.now_ms()
            accepted=validate_ack(ack,command,ack_seen_ms)
            if accepted['accepted'] is not True:raise ValueError('Sampling start rejected')
            # UiServices publishes a cached status about every 0.6s. Accepted
            # does not contain a sampling ID, so wait within the original command
            # window for its new, target-bound token rather than reading once.
            for _ in range(50):
                latest=validate_snapshot(self.snapshot(),self.boot,self.now_ms())
                if epoch!=self.epoch or self.owner!=owner:
                    raise InterruptedError('Sampling workflow replaced')
                actual=self.owner_of(latest)
                if (latest['source_kind']!='actual' or actual[:2]!=owner[:2]
                        or actual[3]!=owner[3] or latest['context']!=current['context']):
                    raise ValueError('Sampling source changed')
                sample=latest['modules']['identity'].get('enrollment_sampling',{})
                session_id=sample.get('session_id','')
                published=(latest['sequence']>current['sequence']
                    and ack_seen_ms<latest['observed_mono_ms']<command['deadline_mono_ms'])
                if (published and session_id and session_id!=previous
                        and sample.get('stage') in ('collect','front')):
                    if actual!=owner or sample.get('bound_target')!=owner[2]:
                        raise ValueError('Sampling target binding changed')
                    # Only a post-ACK, source-stamped new collection for this
                    # complete owner is retained before cancellation/deadline checks.
                    if self.sampling_id not in ('',session_id):
                        raise InterruptedError('Sampling token replaced')
                    self.sampling_id=bound_id=session_id
                    if not is_current():raise InterruptedError('Sampling request cancelled')
                    if self.clock()>=publish_until:raise ValueError('Sampling publication expired')
                    self.stage='sampling';self.authorized=True;self.until=started+90
                    return speech.result('sample_auto')
                if not is_current():raise InterruptedError('Sampling request cancelled')
                remaining=publish_until-self.clock()
                if remaining<=0:break
                time.sleep(min(.05,remaining))
            raise ValueError('Sampling status was not published before the original deadline')
        except InterruptedError:
            discard();raise
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            discard();return speech.result('sample_failed')


    def public(self):
        with self.lock:return {'stage':self.stage,'active':self.stage!='idle'}

    def _keep_ready(self, snapshot):
        """Retain a validated window; this never authorizes an enrollment write."""
        if self.stage!='confirm' or not snapshot:return False
        sample=snapshot['modules'].get('identity',{}).get('enrollment_sampling',{})
        actual=self.owner_of(snapshot);bound=sample.get('bound_target')
        if (sample.get('stage')!='ready' or sample.get('session_id')!=self.sampling_id
                or actual[:2]!=self.owner[:2] or actual[3]!=self.owner[3]):return False
        # Legacy windows have no recovery binding and may only keep the old key.
        if bound is None:return actual==self.owner
        if bound['camera_epoch']!=self.owner[2]['camera_epoch'] or actual[2] not in (None,bound):return False
        if actual[2] is not None:self.owner=copy.deepcopy(actual)
        return True

    @staticmethod
    def selected_target(snapshot):
        identity=snapshot['modules'].get('identity',{})
        return identity.get('face_target') if identity.get('target_kind')=='face' else snapshot['modules']['target'].get('selected')

    @staticmethod
    def single_target(snapshot):
        identity=snapshot['modules'].get('identity',{})
        return identity.get('face_count')==1 if identity.get('target_kind')=='face' else snapshot['modules']['vision'].get('people_count')==1

    @staticmethod
    def owner_of(snapshot):
        return (snapshot['board_boot_id'],snapshot['service_epoch'],VoiceEnrollment.selected_target(snapshot),
                snapshot['modules'].get('identity',{}).get('db_version'))

    def confirmation_diagnostics(self):
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
        if speech.identity_query_requested(text):
            self._trace_confirmation(gate='IDENTITY_QUERY')
            with self.lock:
                if not is_current():raise InterruptedError('Stale identity query')
                if self.stage!='idle':return speech.result('identity_busy')
                epoch=self.epoch
            from board.identity.spoken_query import answer_current_face
            try:reply=answer_current_face(self.snapshot(),capture_snapshot,self.boot,self.now_ms())
            except (OSError,ValueError,KeyError,TypeError):reply=speech.result('identity_unavailable')
            with self.lock:
                if epoch!=self.epoch or not is_current():raise InterruptedError('Cancelled identity query')
            return reply
        # Runs on the voice worker, never on the GTK thread. Holding this lock
        # serializes only workflow turns; reset below uses the same short-lived
        # phases and does not wait across a network request.
        with self.lock:
            if not is_current():raise InterruptedError('Stale enrollment turn')
            active=self.stage!='idle'
            if speech.cancelled(text):
                self._trace_confirmation(gate='CANCEL');self.reset(trace_source='INTERNAL');return speech.result('cancelled')
            if active and self.clock()>=self.until:
                self._trace_confirmation(gate='EXPIRED');self.reset(trace_source='INTERNAL');return speech.result('expired')
            if not active and not speech.enrollment_requested(text):
                self._trace_confirmation(gate='NOT_ENROLLMENT');return None
            epoch=self.epoch
        current=None
        self._trace_confirmation(gate='CURRENT_SNAPSHOT',current_snapshot_valid=False)
        try:
            now=self.now_ms();current=validate_snapshot(self.snapshot(),self.boot,now)
            self._trace_confirmation(current_snapshot_valid=True,current_actual=current['source_kind']=='actual',
                identity_enroll=current['capabilities'].get('identity_enroll') is True,
                identity_sample_start=current['capabilities'].get('identity_sample_start') is True)
            # The capture-start snapshot was validated at capture start. It can
            # now be older than its transport TTL; ownership must still match.
            if not capture_snapshot:
                self._trace_confirmation(gate='CAPTURE_MISSING');raise ValueError('No capture-start owner')
            if capture_snapshot['source_kind']!='actual':
                self._trace_confirmation(gate='CAPTURE_NOT_ACTUAL');raise ValueError('No capture-start owner')
            if current['source_kind']!='actual':
                self._trace_confirmation(gate='CURRENT_NOT_ACTUAL');raise ValueError('Capture owner changed')
            same=self.owner_of(capture_snapshot)==self.owner_of(current)
            self._trace_confirmation(gate='CAPTURE_CURRENT_OWNER',capture_current_owner_equal=same)
            if not same:raise ValueError('Capture owner changed')
            capture_single=self.single_target(capture_snapshot);current_single=self.single_target(current)
            self._trace_confirmation(capture_single=capture_single,current_single=current_single)
            if not capture_single:
                self._trace_confirmation(gate='CAPTURE_SINGLE');raise ValueError('Ambiguous target')
            if not current_single:
                self._trace_confirmation(gate='CURRENT_SINGLE');raise ValueError('Ambiguous target')
            if not self.selected_target(current):
                self._trace_confirmation(gate='CURRENT_TARGET');raise ValueError('Ambiguous target')
        except (ValueError,KeyError,TypeError,OSError):
            with self.lock:
                if epoch==self.epoch and is_current() and self._keep_ready(current):
                    self._trace_confirmation(gate='READY_WINDOW_RETAINED')
                    return speech.result('confirm_update_name' if self.replace_id else 'confirm_name',self.name)
            self.reset(trace_source='INTERNAL');return speech.result('changed' if active else 'face_unavailable')
        with self.lock:
            if epoch!=self.epoch or not is_current():raise InterruptedError('Cancelled enrollment workflow')
            owner=self.owner_of(current)
            identity=current['modules'].get('identity',{})
            sampling=identity.get('enrollment_sampling')
            self._trace_confirmation(gate='WORKFLOW_OWNER',workflow_owner_equal=owner==self.owner)
            if active and owner!=self.owner:
                if (self.stage=='confirm' and sampling and sampling.get('stage')=='ready'
                        and sampling.get('session_id')==self.sampling_id and sampling.get('bound_target')==owner[2]
                        and owner[:2]==self.owner[:2] and owner[3]==self.owner[3]
                        and owner[2]['camera_epoch']==self.owner[2]['camera_epoch']):
                    self.owner=copy.deepcopy(owner)
                else:self.reset(trace_source='INTERNAL');return speech.result('changed')
            if identity.get('state')=='KNOWN':
                self._trace_confirmation(gate='KNOWN_FACE');self.reset(trace_source='INTERNAL');return speech.result('already_known')
            self._trace_confirmation(gate='CAPABILITY')
            if not (current['capabilities'].get('identity_enroll') or
                    sampling and (current['capabilities'].get('identity_sample_start') or self.stage=='sampling')):
                if (self.stage=='confirm' and sampling and sampling.get('stage')=='ready'
                        and sampling.get('session_id')==self.sampling_id):
                    # The held-out window already passed. A new low-quality or
                    # low-score frame can block this write, but must not discard
                    # that window or silently authorize a weaker match.
                    return speech.result('confirm_update_name' if self.replace_id else 'confirm_name',self.name)
                self.reset(trace_source='INTERNAL');return speech.result('face_unavailable')
            self._trace_confirmation(gate='ORIGINAL_FLOW')
            if not active:
                self.stage='name';self.owner=copy.deepcopy(owner);self.until=self.clock()+120
                name=speech.requested_name(text)
                if self.simple and sampling and name:return self._prepare(name,current)
                return speech.result('ask_name')
            name=speech.spoken_name(text)
            if name:
                if self.simple and sampling and self.stage in ('name','authorize'):
                    return self._prepare(name,current)
                if sampling and self.stage=='name':
                    existing=next((p for p in identity['people'] if p['display_name'].casefold()==name.casefold()),None)
                    params={'target':copy.deepcopy(self.selected_target(current))}
                    self.replace_id=existing['person_id'] if existing else ''
                    if existing:params.update(replace_person_id=self.replace_id,db_version=identity['db_version'])
                    ack=self._send('identity_sample_start',params,current)
                    if not ack.get('accepted'):self.reset(trace_source='INTERNAL');return speech.result('sample_failed')
                    sample=self.snapshot()['modules']['identity'].get('enrollment_sampling',{})
                    if not sample.get('session_id'):self.reset(trace_source='INTERNAL');return speech.result('sample_failed')
                    self.name=name;self.stage='sampling';self.sampling_id=sample['session_id'];self.until=self.clock()+90
                    return speech.result('sample_front')
                self.name=name;self.stage='confirm';self.until=self.clock()+120
                if sampling:
                    # Renaming an already sampled replacement could silently
                    # change the future-gallery check. Re-sample instead.
                    self.reset(trace_source='INTERNAL');return speech.result('sample_failed')
                return speech.result('confirm_name',name)
            if self.stage=='name':return speech.result('bad_name')
            if self.replace_id:
                if not speech.update_confirmed(text):return speech.result('retry_update')
            elif not speech.confirmed(text):return speech.result('retry_confirm')
            if self.stage=='authorize':
                self._trace_confirmation(gate='SAMPLING_START')
                return self._start_simple(current,is_current=is_current)
            name=self.name;target=copy.deepcopy(self.selected_target(current))
            command_id='voice-enroll-'+uuid.uuid4().hex
            now=self.now_ms()
            command={'protocol_version':'aura-ui-1','board_boot_id':self.boot,'service_epoch':current['service_epoch'],
                'command_id':command_id,'ui_epoch':epoch,'ui_generation':0,'context':current['context'],
                'snapshot_sequence':current['sequence'],'issued_mono_ms':now,'deadline_mono_ms':now+2500,
                'action':'identity_enroll','params':{'target':target,'display_name':name,'confirmed':True}}
            if self.replace_id:command['params'].update(replace_person_id=self.replace_id,db_version=identity['db_version'])
            if not is_current():raise InterruptedError('Cancelled before enrollment submission')
        # Explicit oral confirmation authorizes this atomic transaction. A later
        # playback cancellation does not undo an already committed enrollment.
        try:
            self._trace_confirmation(gate='ENROLL_SUBMIT')
            ack=self.command(command)
            latest=validate_snapshot(self.snapshot(),self.boot,self.now_ms())
            state=latest['modules'].get('identity',{})
            done=identity_completion(dict(ack,action='identity_enroll'),state)
            if not done:
                with self.lock:
                    sample=state.get('enrollment_sampling',{})
                    if (ack.get('accepted') is False and self.stage=='confirm' and epoch==self.epoch
                            and is_current() and self._keep_ready(latest)):
                        return speech.result('confirm_update_name' if self.replace_id else 'confirm_name',self.name)
                raise ValueError('Enrollment transaction not confirmed')
        except Exception:
            self.reset(trace_source='INTERNAL');return speech.result('failed')
        with self.lock:self.sampling_id=''
        self.reset(trace_source='INTERNAL');return speech.result('registered')
