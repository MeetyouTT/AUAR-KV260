"""Live-stage orchestration, using the existing event/FSM/action policy."""
from __future__ import annotations
import time
from board.runtime.events import EventType as E
from board.runtime.audio.selected_voice import normalize_text
from board.runtime.avatar_actions import ALLOWED_AVATAR_ACTIONS
from tools.realtime_facials import RealtimeFacials

class RealtimeController:
    def __init__(self,core,jobs,output,clock=time.monotonic):
        self.core=core;self.jobs=jobs;self.output=output;self.clock=clock;self.origin=clock()
        self.pause_started=None;self.pause_total=0.;self.facials=RealtimeFacials(core)
        self.pending=None;self.ready=None;self.audio_waiting=None;self.reply='';self.phase='IDLE';self.log=[];self.turns=[]
        self.last_meta=None;self.last_error='';self.last_job=None;self.metrics={'late_results_dropped':0}

    def now(self):return (self.pause_started if self.pause_started is not None else self.clock())-self.origin-self.pause_total

    def record(self,event,**fields):
        self.log.append({'at':round(self.now(),4),'event':event,**fields})
        if len(self.log)>200:self.log.pop(0)

    def send(self,event,payload=None):
        before=self.core.fsm.rejected_count;self.core.send(event,payload)
        self.record(str(event),state=self.core.fsm.state.label,rejected=self.core.fsm.rejected_count>before)

    def resume_visual(self):
        if self.pause_started is not None:
            self.pause_total+=self.clock()-self.pause_started;self.pause_started=None

    def cancel(self):
        self.resume_visual();self.facials.stop(self.now());self.output.stop()
        if self.pending:
            try:self.jobs.cancel(self.pending['id'])
            except KeyError:pass
        self.pending=None;self.ready=None;self.audio_waiting=None;self.core.cancel()
        if self.core.fsm.state.label not in {'IDLE','PRESENT'}:self.send(E.AUDIO_CANCEL_REQUESTED)
        self.phase='IDLE';self.record('cancel',generation=self.core.talk_gen)

    def submit(self,text,emotion='neutral',action='',requested_at=None,*,prepared_job=None):
        if prepared_job:
            import unicodedata
            text=unicodedata.normalize('NFC',text).strip()
        else:text=getattr(self.jobs,'normalize_text',normalize_text)(text)
        if emotion not in {'neutral','friendly','happy','excited','sad','low'}:raise ValueError('Unsupported emotion')
        if action and action not in ALLOWED_AVATAR_ACTIONS:raise ValueError('Unsupported action')
        self.cancel();self.last_error='';self.reply=text
        self.send(E.BOARD_KEY_PRESSED);self.send(E.AUDIO_VAD_END)
        generation=self.core.new_turn()
        try:job=self.jobs.get(prepared_job) if prepared_job else self.jobs.submit(text,'happy' if emotion in {'happy','excited'} else 'sad' if emotion in {'sad','low'} else 'neutral')
        except Exception:
            self.cancel();raise
        self.pending={'id':job['id'],'generation':generation,'text':text,'emotion':emotion,'action':action,'submitted':self.clock() if requested_at is None else requested_at}
        self.last_job=job['id'];self.phase='VOICE_PREPARING';self.record('voice_requested',text=text,emotion=emotion,action=action,generation=generation)
        return job['id']

    def submit_generated(self,value,requested_at=None):
        job=self.jobs.import_generated(value)
        return self.submit(job['text'],job['emotion'],requested_at=requested_at,prepared_job=job['id'])

    def start_audio(self):
        ready=self.ready
        if not ready:return
        if ready['generation']!=self.core.talk_gen:self.ready=None;self.metrics['late_results_dropped']+=1;return
        self.output.play(ready['result']['path'],sha256=ready['result']['sha256'])
        self.facials.begin(ready['result']['envelope']);self.phase='VOICE_STARTING'
        self.audio_waiting=ready;self.ready=None;self.record('audio_requested',generation=ready['generation'])
        self.observe_audio_start()

    def observe_audio_start(self):
        ready=self.audio_waiting
        if not ready or not getattr(self.output,'ready',True):return
        if ready['generation']!=self.core.talk_gen:self.audio_waiting=None;return
        self.phase='SPEAKING'
        self.turns.append({'text':ready['text'],'emotion':ready['emotion'],'action':ready['action'],
                           'generation':ready['generation'],'cache_hit':ready['result']['cache_hit'],
                           'request_to_audio_seconds':(getattr(self.output,'started_at',None) or self.clock())-ready['submitted'],
                           'duration_seconds':ready['result']['duration_seconds'],'audio_sha256':ready['result']['sha256']})
        self.turns=self.turns[-100:]
        self.record('audio_started',generation=ready['generation'],cache_hit=ready['result']['cache_hit']);self.audio_waiting=None

    def event(self,name):
        mapping={'person_enter':E.SCENE_PERSON_ENTER,'wake':E.AUDIO_KWS_DETECTED,
                 'listen':E.BOARD_KEY_PRESSED,'vad_end':E.AUDIO_VAD_END}
        if name=='reset':
            self.cancel();self.core.fsm.reset();self.core.reset_playback();self.reply='';self.phase='IDLE';return
        if name=='cancel':self.cancel();return
        if name not in mapping:raise ValueError('Unknown event')
        if name=='listen' and (self.pending or self.ready or self.output.active):self.cancel()
        self.send(mapping[name])

    def toggle_pause(self):
        if not self.output.active:return
        if self.pause_started is None:self.pause_started=self.clock();self.output.pause(True)
        else:self.resume_visual();self.output.pause(False)

    def begin_dialogue(self):
        self.cancel();self.last_error='';self.send(E.BOARD_KEY_PRESSED);self.send(E.AUDIO_VAD_END)
        generation=self.core.new_turn();self.phase='DIALOGUE_WAITING';return generation

    def accept_dialogue(self,generation,text,emotion='neutral',action='',requested_at=None):
        if generation!=self.core.talk_gen:
            self.metrics['late_results_dropped']+=1;return False
        self.submit(text,emotion,action,requested_at=requested_at);return True

    def tick(self):
        if self.pending:
            pending=self.pending;job=self.jobs.get(pending['id'])
            if pending['generation']!=self.core.talk_gen:
                self.pending=None;self.metrics['late_results_dropped']+=1
            elif job['status']=='COMPLETE':
                from pathlib import Path
                result=dict(job['result']);result['path']=str(Path(self.jobs.root)/'cache'/f"{result['key']}.wav")
                self.pending=None;self.ready=dict(pending,result=result)
                self.core.apply_response({'reply_text':pending['text'],'emotion':pending['emotion'],'avatar_action':pending['action']})
                self.record('response_applied',state=self.core.fsm.state.label)
                if self.core.fsm.state.label in {'ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'}:
                    self.phase='ACTION'
                    # PUZZLED is deliberately a loop in the shared asset policy.
                    # Give it a brief visible reaction; do not wait for a burst callback.
                    if self.core.fsm.state.label=='PUZZLED':self.ready['action_until']=self.now()+.9
                else:self.start_audio()
            elif job['status'] in {'FAILED','CANCELLED'}:
                self.pending=None;self.last_error=job.get('error','语音请求已取消');self.cancel()
        if self.ready and 'action_until' in self.ready and self.now()>=self.ready['action_until']:
            self.send(E.AUDIO_PLAYBACK_START,{'emotion':self.core.emotion});self.start_audio()
        self.observe_audio_start()
        audio_time=self.output.position()
        if self.output.finished():
            self.facials.stop(self.now());self.send(E.AUDIO_PLAYBACK_STOP);self.phase='IDLE';self.record('audio_finished')
        if not getattr(self,'render_requested',True):return self.last_meta
        gain,level=self.facials.values(audio_time,self.output.active and getattr(self.output,'ready',True),self.now());self.core.speech_gain=gain
        meta=self.core.display_frame(self.core.fsm.state.label,self.now())
        if self.core.take_burst_finished():
            completion=self.core.burst_completion(self.core.fsm.state.label,self.ready is not None or self.output.active,self.core.emotion)
            if completion:self.send(*completion)
            if self.ready:self.start_audio()
        if meta:self.last_meta=self.facials.apply(meta,self.now(),gain,level)
        return self.last_meta

    def public(self):
        meta=self.last_meta or {}
        return {'phase':self.phase,'state':self.core.fsm.state.label,'display_state':meta.get('display_state'),
                'asset':meta.get('asset'),'index':meta.get('index'),'transitioning':meta.get('transitioning',False),
                'reply':self.reply,'audio_time':self.output.position(),'duration':self.output.duration,
                'playing':self.output.active and getattr(self.output,'ready',True),'paused':self.pause_started is not None,'speech_gain':meta.get('speech_gain',0),
                'mouth_level':meta.get('mouth_level',0),'blink_active':meta.get('blink_active',False),
                'blink_phase':meta.get('blink_phase'),'visual_time':self.now(),'error':self.last_error,
                'generation':self.core.talk_gen,'rejected_count':self.core.fsm.rejected_count,
                'pending_job':self.pending['id'] if self.pending else None,'last_job':self.last_job,
                'audio_output_state':self.output.read().get('device_state') if hasattr(self.output,'read') else None,
                'log':self.log[-30:],'turns':self.turns[-20:],'metrics':dict(self.metrics)}
