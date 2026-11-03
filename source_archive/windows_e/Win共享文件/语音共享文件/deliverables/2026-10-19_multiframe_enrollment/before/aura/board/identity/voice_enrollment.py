"""Board owns target binding, oral confirmation and the enrollment transaction."""
import copy
import threading
import time
import uuid
from common import voice_enrollment as speech
from board.interaction.ui_contract import millis,validate_snapshot,identity_completion

class VoiceEnrollment:
    def __init__(self,boot_id,snapshot,command,*,clock=time.monotonic,now_ms=millis):
        self.boot=boot_id;self.snapshot=snapshot;self.command=command;self.clock=clock
        self.now_ms=now_ms
        self.lock=threading.RLock();self.reset()

    def reset(self):
        with self.lock:
            self.stage='idle';self.name='';self.owner=None;self.until=0;self.epoch=uuid.uuid4().hex

    def public(self):
        with self.lock:return {'stage':self.stage,'active':self.stage!='idle'}

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
        try:
            now=self.now_ms();current=validate_snapshot(self.snapshot(),self.boot,now)
            # The capture-start snapshot was validated at capture start. It can
            # now be older than its transport TTL; ownership must still match.
            if not capture_snapshot or capture_snapshot['source_kind']!='actual':raise ValueError('No capture-start owner')
            if current['source_kind']!='actual' or self.owner_of(capture_snapshot)!=self.owner_of(current):raise ValueError('Capture owner changed')
            if (not self.single_target(capture_snapshot) or not self.single_target(current)
                    or not self.selected_target(current)):raise ValueError('Ambiguous target')
        except (ValueError,KeyError,TypeError,OSError):
            self.reset();return speech.result('changed' if active else 'face_unavailable')
        with self.lock:
            if epoch!=self.epoch or not is_current():raise InterruptedError('Cancelled enrollment workflow')
            owner=self.owner_of(current)
            if active and owner!=self.owner:self.reset();return speech.result('changed')
            identity=current['modules'].get('identity',{})
            if identity.get('state')=='KNOWN':self.reset();return speech.result('already_known')
            if not current['capabilities'].get('identity_enroll'):
                self.reset();return speech.result('face_unavailable')
            if not active:
                self.stage='name';self.owner=copy.deepcopy(owner);self.until=self.clock()+120
                return speech.result('ask_name')
            name=speech.spoken_name(text)
            if name:
                self.name=name;self.stage='confirm';self.until=self.clock()+120
                return speech.result('confirm_name',name)
            if self.stage=='name':return speech.result('bad_name')
            if not speech.confirmed(text):return speech.result('retry_confirm')
            name=self.name;target=copy.deepcopy(self.selected_target(current))
            command_id='voice-enroll-'+uuid.uuid4().hex
            now=self.now_ms()
            command={'protocol_version':'aura-ui-1','board_boot_id':self.boot,'service_epoch':current['service_epoch'],
                'command_id':command_id,'ui_epoch':epoch,'ui_generation':0,'context':current['context'],
                'snapshot_sequence':current['sequence'],'issued_mono_ms':now,'deadline_mono_ms':now+2500,
                'action':'identity_enroll','params':{'target':target,'display_name':name,'confirmed':True}}
            if not is_current():raise InterruptedError('Cancelled before enrollment submission')
        # Explicit oral confirmation authorizes this atomic transaction. A later
        # playback cancellation does not undo an already committed enrollment.
        try:
            ack=self.command(command)
            state=self.snapshot()['modules'].get('identity',{})
            done=identity_completion(dict(ack,action='identity_enroll'),state)
            if not done:raise ValueError('Enrollment transaction not confirmed')
        except Exception:
            self.reset();return speech.result('failed')
        self.reset();return speech.result('registered')
