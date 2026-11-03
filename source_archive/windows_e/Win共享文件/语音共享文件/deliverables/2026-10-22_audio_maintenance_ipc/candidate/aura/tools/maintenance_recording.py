"""Owner-thread barrier around the actual recording controller.

The first version deliberately admits only controllers without retained capture
or channel objects. It never cancels work or changes handsfree preferences to
manufacture idle. All activity must continue to enter through AvatarRenderWorker.
"""
import copy
import threading


def camera_only_services_idle(services):
    """V1 excludes a second audio-capable service, stale state or queued work."""
    view=services.read();snapshot=view.get('snapshot')
    if view.get('link')!='READY' or view.get('pending_count')!=0 or not snapshot:return False
    caps=snapshot.get('capabilities',{});modules=snapshot.get('modules',{})
    return (snapshot.get('source_kind')=='actual'
        and all(caps.get(name) is False for name in ('record_start','record_stop','ask_frame'))
        and modules.get('interaction',{}).get('state') in ('IDLE','CANCELLED')
        and modules.get('audio',{}).get('state') in ('READY','UNAVAILABLE'))


class MaintenanceRecordingController:
    def __init__(self,controller,output,*,transcription_store=None):
        self.controller,self.output=controller,output
        self._transcription_store=transcription_store
        self.external_idle=None
        self._owner=None;self._held=False;self._request=None;self._failure=''
        self._cached=copy.deepcopy(controller.public())
        self._base=controller.controller
        while 'controller' in vars(self._base):self._base=vars(self._base)['controller']

    def _check_owner(self):
        current=threading.get_ident()
        if self._owner is None:self._owner=current
        elif current!=self._owner:raise RuntimeError('Audio intents must use the avatar owner thread')

    def _idle(self):
        # Inspect actual owned objects, without calling public()/poll()/cancel().
        recording=vars(self.controller);base=vars(self._base)
        if self.external_idle is not None and self.external_idle() is not True:return False
        if recording.get('closed') or base.get('phase')!='IDLE':return False
        if any(base.get(name) is not None for name in ('pending','ready','audio_waiting','stream','pause_started')):
            return False
        if base.get('completed_streams'):return False
        if self.output.active or self.output.paused or self.output.streaming:return False
        if any(recording.get(name) is not None for name in
               ('capture','utterance','barge_capture','listen_id','barge_id','speech_proof','barge_speech',
                'rearm_at','ack_deadline','entry_deadline')):return False
        if any(recording.get(name) for name in ('auto_enabled','monitor_owned','awaiting_entry')):return False
        transcriber=recording.get('transcriber')
        if transcriber is None:return True
        flow=getattr(transcriber,'identity_flow',None)
        # Do not nest identity-flow and transcription locks: enrollment may
        # call back into transcription while holding its own lock.
        if flow is not None and flow.public().get('active') is not False:return False
        with transcriber.condition:
            if transcriber.closed:return False
            if any(getattr(transcriber,name,None) for name in ('waiting','active','results','progress','channel')):
                return False
        return True

    def audio_maintenance(self):
        self._check_owner()
        with self.output.lifecycle:
            if self._held:raise ValueError('音频维护屏障已建立')
            self._held=True;self._failure=''
            try:
                if not self._idle():raise ValueError('录音、转写或播放尚未完全空闲')
                self._request=self.output.begin_idle_maintenance()
            except Exception:
                # A transport write may have partly succeeded: keep that gate held.
                self._held=self.output.maintenance_status()['held']
                raise
        return {'request_id':self._request,'state':'REQUESTED','usb_playback_health':'UNVERIFIED'}

    def _activity(self):
        self._check_owner()
        if self._held:raise ValueError('音频维护中，新的录音和播放请求已暂停')

    def configure_transcription_saved(self,values):
        self._activity()
        if self._transcription_store is None:raise ValueError('Transcription settings store unavailable')
        values=self._transcription_store.update(values)
        return self.controller.configure_transcription(values)

    def conversation_start_selected(self,resume):
        self._activity()
        self.controller.transcriber.select_conversation(resume=resume)
        return self.controller.conversation_start()

    def tick(self):
        self._check_owner()
        if self._held:
            status=self.output.maintenance_status()
            if status['state']=='REJECTED' and not status['held']:self._held=False
            elif status['state']=='READY_HELD':
                if not self._idle():self._failure='FAILED_OWNER_RECHECK'
                elif not self._failure and self.output.finish_idle_maintenance(self._request):self._held=False
            if self._held:
                # No RecordingController.public/tick, _collect, ASR or capture
                # auto-rearm while held. Idle base tick only maintains visuals.
                if self._idle():return self._base.tick()
                self._failure=self._failure or 'FAILED_OWNER_RECHECK'
                return getattr(self._base,'last_meta',None)
        return self.controller.tick()

    def public(self):
        if not self._held:self._cached=copy.deepcopy(self.controller.public())
        result=copy.deepcopy(self._cached)
        status=self.output.maintenance_status()
        result['audio_maintenance']=dict(status,owner_held=self._held,owner_failure=self._failure)
        if self._held:
            for name in ('local_recording','automatic_conversation'):
                if name in result:result[name].update(can_start=False,can_stop=False)
            if 'handsfree_dialogue' in result:
                result['handsfree_dialogue'].update(state='AUDIO_MAINTENANCE',microphone_open=False)
        return result

    @property
    def last_error(self):return self.controller.last_error

    @last_error.setter
    def last_error(self,value):self.controller.last_error=value

    def __getattr__(self,name):
        value=getattr(self.controller,name)
        if not callable(value):return value
        def invoke(*args,**kwargs):
            self._check_owner()
            if self._held:
                allowed=name in ('cancel','conversation_stop','close') or (
                    name=='event' and args and args[0] in ('cancel','reset'))
                if not allowed:raise ValueError('音频维护中，新的录音和播放请求已暂停')
                self._failure='FAILED_CANCELLED'
                # Explicit user cancel/close retains original semantics; it
                # cannot release admission even if a matching READY arrives.
                self.output.stop()
            return value(*args,**kwargs)
        return invoke
