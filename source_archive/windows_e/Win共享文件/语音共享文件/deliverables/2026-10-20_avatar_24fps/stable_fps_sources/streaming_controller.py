"""Existing avatar assets driven by persistent sink time and verified PCM."""
import math
import wave
import numpy as np
from board.runtime.events import EventType as E
from tools.realtime_controller import RealtimeController


class StreamEnvelope:
    def __init__(self):
        self.envelope={'hop_seconds':.01,'gains':[],'levels':[]}
        self.remainder=b'';self.gain=0.;self.level=0.

    def append(self,pcm,*,finish=False):
        self.remainder+=pcm
        while len(self.remainder)>=480 or (finish and self.remainder):
            part,self.remainder=self.remainder[:480],self.remainder[480:]
            data=np.frombuffer(part,dtype='<i2').astype(np.float64)/32768
            rms=float(np.sqrt(np.mean(data*data)))
            self.gain=min(1.,self.gain+1/3) if rms>=.008 else max(0.,self.gain-.125)
            target=min(1.,(rms/.1)**.65)
            self.level+=(.45 if target>self.level else .26)*(target-self.level)
            self.envelope['gains'].append(self.gain*self.gain*(3-2*self.gain))
            self.envelope['levels'].append(self.level)


class StreamingController(RealtimeController):
    def __init__(self,*args,**kwargs):
        self.stream=None;self.completed_streams=[]
        super().__init__(*args,**kwargs)

    def cancel(self):
        self.stream=None
        super().cancel()

    def channel_event(self,header,pcm,owner,feedback_assets,requested_at):
        kind=header['kind']
        if kind=='start':
            generation=self.begin_dialogue()
            self.stream={'owner':owner,'generation':generation,'envelope':StreamEnvelope(),
                         'thinking_mode':header.get('thinking_mode','chat'),
                         'answer_received':False,'hint':False,'network':None,'audio_done':False,
                         'requested_at':requested_at,'response_applied':False,'controls':[]}
            self.reply='';self.output.begin_stream();self.phase='THINKING'
            self.facials.begin(self.stream['envelope'].envelope)
            return
        stream=self.stream
        if not stream or stream['owner']!=owner or stream['generation']!=self.core.talk_gen:return
        if kind=='text':self.reply+=header['text']
        elif kind=='thinking' and not stream['answer_received'] and not stream['hint']:
            value=feedback_assets[header['feedback_id']]
            with wave.open(value['path'],'rb') as audio:raw=audio.readframes(audio.getnframes())
            self.output.feedback(value);stream['envelope'].append(raw)
            stream['hint']=True;stream['hint_text']=value['reply_text']
            self.record('thinking_feedback_queued',request_id=owner['request_id'])
        elif kind=='audio':
            stream['answer_received']=True
            self.output.append_pcm(pcm,header['start_sample']);stream['envelope'].append(pcm)
        elif kind=='control':stream['controls'].append(header)
        elif kind=='end':
            stream['server_metrics']={key:header[key] for key in ('first_pcm_ms','first_text_ms','timing','clauses',
                'tts_total_ms','tts_cache_hits','thinking_characters','total_ms') if key in header}
            stream['envelope'].append(b'',finish=True);self.output.end_stream()

    def channel_complete(self,owner,result):
        if self.stream and self.stream['owner']==owner:self.stream['network']=result

    def take_completion(self):return self.completed_streams.pop(0) if self.completed_streams else None

    def tick(self):
        stream=self.stream
        if stream is None:return super().tick()
        snapshot=self.output.read()
        if snapshot.get('error'):
            self.last_error=snapshot['error'];self.cancel();return super().tick()
        position=self.output.position()
        if snapshot.get('audible'):
            if not stream['response_applied']:
                self.core.apply_response({'reply_text':self.reply or stream.get('hint_text',''),
                                          'emotion':'neutral','avatar_action':''})
                stream['response_applied']=True
            self.phase='THINKING_FEEDBACK' if snapshot.get('track')=='feedback' else 'SPEAKING'
        else:
            self.phase='THINKING'
            if stream['hint'] and stream['response_applied'] and snapshot.get('answer_started_at') is None:
                self.send(E.AUDIO_PLAYBACK_STOP);self.send(E.BOARD_KEY_PRESSED);self.send(E.AUDIO_VAD_END)
                stream['response_applied']=False
        for control in list(stream['controls']):
            if snapshot.get('answer_clock',0)*24000>=control['at_sample']:
                self.core.emotion=control['emotion'];stream['controls'].remove(control)
        if self.output.finished():stream['audio_done']=True
        if stream['audio_done'] and stream['network']:
            self.completed_streams.append((stream['owner'],stream['network']))
            self.turns.append({'text':self.reply,'generation':stream['generation'],
                              'thinking_mode':stream['thinking_mode'],
                              'thinking_feedback':stream['hint'],'audio_complete':True,
                              'server_metrics':stream.get('server_metrics',{}),
                              'request_to_feedback_or_audio_seconds':(snapshot.get('started_at') or self.clock())-stream['requested_at'],
                              'request_to_answer_seconds':(snapshot.get('answer_started_at') or self.clock())-stream['requested_at']})
            self.turns=self.turns[-100:]
            self.facials.stop(self.now());self.send(E.AUDIO_PLAYBACK_STOP);self.phase='IDLE';self.stream=None
        if not getattr(self,'render_requested',True):return self.last_meta
        gain,level=self.facials.values(position,bool(snapshot.get('audible') and not self.output.paused),self.now())
        self.core.speech_gain=gain
        meta=self.core.display_frame(self.core.fsm.state.label,self.now())
        if self.core.take_burst_finished():
            completion=self.core.burst_completion(self.core.fsm.state.label,self.output.active,self.core.emotion)
            if completion:self.send(*completion)
        if meta:self.last_meta=self.facials.apply(meta,self.now(),gain,level)
        return self.last_meta

    def public(self):
        state=super().public()
        state['streaming_reply']=self.stream is not None
        if self.stream:state['thinking_feedback']=self.stream['hint']
        return state
