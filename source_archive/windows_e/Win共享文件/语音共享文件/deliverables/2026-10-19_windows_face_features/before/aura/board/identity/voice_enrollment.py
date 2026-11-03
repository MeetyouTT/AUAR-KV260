"""Board owns target binding, oral confirmation and the enrollment transaction."""
import copy
import threading
import time
import uuid
from common import voice_enrollment as speech
from board.interaction.ui_contract import millis,validate_snapshot,identity_completion

class VoiceEnrollment:
    def __init__(self,boot_id,snapshot,command,*,clock=time.monotonic,now_ms=millis,simple=False):
        self.boot=boot_id;self.snapshot=snapshot;self.command=command;self.clock=clock
        self.now_ms=now_ms
        self.simple=simple
        self.lock=threading.RLock();self.reset()

    def reset(self):
        with self.lock:
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
                            self.reset();emit(speech.result('sample_failed'),True);return
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
                        self.reset();emit(speech.result('registered' if saved else 'failed'),True);return
                    with self.lock:
                        if epoch!=self.epoch:raise InterruptedError('Sampling cancelled')
                        self.stage='confirm';self.until=self.clock()+60;name=self.name
                        code='confirm_update_name' if self.replace_id else 'confirm_name'
                    emit(speech.result(code,name),True);return
                if stage=='failed':
                    self.reset();emit(speech.result('sample_failed'),True);return
                if self.clock()>=self.until:raise ValueError('Sampling timeout')
                if not self.authorized and stage!=previous and stage in ('left','right','validate'):
                    emit(speech.result('sample_'+stage),False);previous=stage
                time.sleep(.15)
            raise InterruptedError('Sampling request no longer current')
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            self.reset()
            if is_current():
                try:emit(speech.result('sample_failed'),True)
                except (OSError,ValueError):pass
        except InterruptedError:
            self.reset()

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

    def _start_simple(self,current):
        params={'target':copy.deepcopy(self.selected_target(current))}
        if self.replace_id:params.update(replace_person_id=self.replace_id,db_version=self.owner[3])
        ack=self._send('identity_sample_start',params,current)
        if not ack.get('accepted'):self.reset();return speech.result('sample_failed')
        latest=validate_snapshot(self.snapshot(),self.boot,self.now_ms())
        sample=latest['modules']['identity'].get('enrollment_sampling',{})
        if (not sample.get('session_id') or sample.get('stage') not in ('collect','front')
                or self.owner_of(latest)!=self.owner):
            self.reset();return speech.result('sample_failed')
        self.stage='sampling';self.authorized=True;self.sampling_id=sample['session_id'];self.until=self.clock()+90
        return speech.result('sample_auto')

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

    def handle(self,text,capture_snapshot,*,is_current=lambda:True):
        # Runs on the voice worker, never on the GTK thread. Holding this lock
        # serializes only workflow turns; reset below uses the same short-lived
        # phases and does not wait across a network request.
        with self.lock:
            if not is_current():raise InterruptedError('Stale enrollment turn')
            active=self.stage!='idle'
            if speech.cancelled(text):self.reset();return speech.result('cancelled')
            if active and self.clock()>=self.until:self.reset();return speech.result('expired')
            if not active and not speech.enrollment_requested(text):return None
            epoch=self.epoch
        current=None
        try:
            now=self.now_ms();current=validate_snapshot(self.snapshot(),self.boot,now)
            # The capture-start snapshot was validated at capture start. It can
            # now be older than its transport TTL; ownership must still match.
            if not capture_snapshot or capture_snapshot['source_kind']!='actual':raise ValueError('No capture-start owner')
            if current['source_kind']!='actual' or self.owner_of(capture_snapshot)!=self.owner_of(current):raise ValueError('Capture owner changed')
            if (not self.single_target(capture_snapshot) or not self.single_target(current)
                    or not self.selected_target(current)):raise ValueError('Ambiguous target')
        except (ValueError,KeyError,TypeError,OSError):
            with self.lock:
                if epoch==self.epoch and is_current() and self._keep_ready(current):
                    return speech.result('confirm_update_name' if self.replace_id else 'confirm_name',self.name)
            self.reset();return speech.result('changed' if active else 'face_unavailable')
        with self.lock:
            if epoch!=self.epoch or not is_current():raise InterruptedError('Cancelled enrollment workflow')
            owner=self.owner_of(current)
            identity=current['modules'].get('identity',{})
            sampling=identity.get('enrollment_sampling')
            if active and owner!=self.owner:
                if (self.stage=='confirm' and sampling and sampling.get('stage')=='ready'
                        and sampling.get('session_id')==self.sampling_id and sampling.get('bound_target')==owner[2]
                        and owner[:2]==self.owner[:2] and owner[3]==self.owner[3]
                        and owner[2]['camera_epoch']==self.owner[2]['camera_epoch']):
                    self.owner=copy.deepcopy(owner)
                else:self.reset();return speech.result('changed')
            if identity.get('state')=='KNOWN':self.reset();return speech.result('already_known')
            if not (current['capabilities'].get('identity_enroll') or
                    sampling and (current['capabilities'].get('identity_sample_start') or self.stage=='sampling')):
                if (self.stage=='confirm' and sampling and sampling.get('stage')=='ready'
                        and sampling.get('session_id')==self.sampling_id):
                    # The held-out window already passed. A new low-quality or
                    # low-score frame can block this write, but must not discard
                    # that window or silently authorize a weaker match.
                    return speech.result('confirm_update_name' if self.replace_id else 'confirm_name',self.name)
                self.reset();return speech.result('face_unavailable')
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
                    if not ack.get('accepted'):self.reset();return speech.result('sample_failed')
                    sample=self.snapshot()['modules']['identity'].get('enrollment_sampling',{})
                    if not sample.get('session_id'):self.reset();return speech.result('sample_failed')
                    self.name=name;self.stage='sampling';self.sampling_id=sample['session_id'];self.until=self.clock()+90
                    return speech.result('sample_front')
                self.name=name;self.stage='confirm';self.until=self.clock()+120
                if sampling:
                    # Renaming an already sampled replacement could silently
                    # change the future-gallery check. Re-sample instead.
                    self.reset();return speech.result('sample_failed')
                return speech.result('confirm_name',name)
            if self.stage=='name':return speech.result('bad_name')
            if self.replace_id:
                if not speech.update_confirmed(text):return speech.result('retry_update')
            elif not speech.confirmed(text):return speech.result('retry_confirm')
            if self.stage=='authorize':return self._start_simple(current)
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
            self.reset();return speech.result('failed')
        with self.lock:self.sampling_id=''
        self.reset();return speech.result('registered')
