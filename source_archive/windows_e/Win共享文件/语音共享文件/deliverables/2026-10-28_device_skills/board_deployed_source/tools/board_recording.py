"""Serialize local capture and cached playback on the avatar controller owner."""
import time
from board.runtime.audio.capture import Mcp01Capture, CapturedAudio


class RecordingController:
    def __init__(self, controller, *, capture_factory=Mcp01Capture, transcriber=None,
                 auto_capture_factory=None, audio_frontend=None,clock=time.monotonic):
        from common.frontend_wire import configuration
        self.audio_frontend=configuration(audio_frontend)
        self.controller, self.capture_factory = controller, capture_factory
        self.capture = self.utterance = None
        self.recording_state = 'IDLE'
        self.recording_error = ''
        self.closed = False
        self.transcriber = transcriber
        self.transcription = self._empty_transcription('IDLE' if transcriber and transcriber.enabled() else 'DISABLED')
        self.auto_capture_factory, self.clock = auto_capture_factory, clock
        self.capture_kind = None
        self.auto_enabled = False; self.auto_state = 'STOPPED'; self.auto_error = ''
        self.auto_turns = 0; self.rearm_at = self.ack_deadline = None

    def _capture_for(self, automatic):
        kind = 'automatic' if automatic else 'manual'
        if self.capture_kind != kind:
            if self.capture is not None: self.capture.close()
            factory = self.capture_factory
            if automatic:
                if self.auto_capture_factory is None:
                    from board.runtime.audio.automatic_capture import AutomaticMcp01Capture
                    factory = lambda *a,**kw:AutomaticMcp01Capture(*a,audio_frontend=self.audio_frontend,**kw)
                else: factory = self.auto_capture_factory
            self.capture = factory(self._playback_active, max_seconds=20)
            self.capture_kind = kind
        return self.capture

    def _listen(self):
        if self._playback_active(): raise ValueError('请先结束当前播放')
        if self.transcriber.public().get('pending'): raise ValueError('上一轮仍在处理')
        self.transcriber.cancel()
        capture_id = self._capture_for(True).start()
        if hasattr(self.transcriber,'capture_started'):self.transcriber.capture_started(capture_id)
        self.utterance = None
        self.recording_state, self.recording_error = 'RECORDING', ''
        self.transcription = self._empty_transcription('IDLE')
        self.auto_state = 'LISTENING'; self.rearm_at = self.ack_deadline = None
        return capture_id

    def conversation_start(self):
        self._collect()
        if self.closed or self.auto_enabled: raise ValueError('对话已开启或已关闭')
        if (self.transcriber is None or not self.transcriber.enabled()
                or getattr(self.transcriber,'feedback_assets',None) is None
                or not self.transcriber.public().get('feedback_ready')):
            raise ValueError('语音服务尚未就绪')
        if self._recording() or self._playback_active(): raise ValueError('请先结束当前录音或播放')
        self.auto_error = ''; self.last_error = ''; self.auto_turns = 0
        try: capture_id = self._listen()
        except Exception as exc:
            self._auto_fail(str(exc)); raise
        self.auto_enabled = True
        return {'enabled':True,'state':'LISTENING','capture_id':capture_id}

    def conversation_stop(self):
        self.cancel()
        return {'enabled':False,'state':'STOPPED'}

    def _auto_fail(self, error):
        self.auto_enabled = False; self.auto_state = 'ERROR'; self.auto_error = error
        if self.capture is not None: self.capture.cancel()
        if self.transcriber:
            self.transcriber.cancel()
            if hasattr(self.transcriber,'reset_enrollment'):self.transcriber.reset_enrollment()
        self.controller.cancel()

    def _auto_tick(self):
        if not self.auto_enabled: return
        if self.recording_state == 'ERROR' or self.transcription['state'] == 'ERROR' or self.last_error:
            self._auto_fail(self.recording_error or self.transcription['error'] or self.last_error); return
        if self._recording():
            self.auto_state = 'LISTENING'; return
        if self.transcription['state'] == 'ANSWERED':
            self.auto_state = 'WAITING_ACK'
            ack = self.transcriber.public().get('last_playback_ack') or {}
            if ack.get('request_id') == self.transcription['request_id']:
                if not ack.get('committed'):
                    self._auto_fail('回答已播放，但记忆确认失败，请重新开始对话'); return
                self.auto_state = 'SETTLING'
                if (self.clock() >= self.rearm_at and not self._playback_active()
                        and not self.transcriber.public().get('pending')):
                    try: self._listen()
                    except Exception as exc: self._auto_fail(str(exc))
            elif self.clock() >= self.ack_deadline:
                self._auto_fail('回答已播放，但记忆确认超时，请重新开始对话')
        else:
            self.auto_state = 'SPEAKING' if self.controller.public().get('playing') else 'PROCESSING'

    @staticmethod
    def _empty_transcription(state):
        return {'state':state,'capture_id':None,'request_id':None,'text':'','error':'',
                'recognition_ms':None,'model_id':None}

    def _queue_transcription(self):
        self.transcription = self._empty_transcription('DISABLED')
        if self.utterance is None:return
        self.transcription['capture_id'] = self.utterance.capture_id
        if self.transcriber is None or not self.transcriber.enabled():return
        try:
            self.requested_at=time.monotonic()
            request = self.transcriber.submit(self.utterance)
            self.transcription.update(state='TRANSCRIBING',request_id=request['request_id'])
        except Exception as exc:
            self.transcription.update(state='ERROR',error=str(exc))

    def _poll_transcription(self):
        if self.transcriber is None:return
        if getattr(self.transcriber,'feedback_assets',None) is not None:
            # A model emits PCM in a burst. Drain enough to stay ahead of
            # playback, but return to rendering/commands between batches.
            # Preserve order and the existing producer backpressure; no drop.
            deadline=time.monotonic()+.006
            for index in range(8):
                if index and time.monotonic()>=deadline:return
                result=self.transcriber.poll()
                if not result:return
                owner=result.get('context',{})
                if (owner.get('request_id')!=self.transcription['request_id'] or owner.get('capture_id')!=self.transcription['capture_id']):continue
                if result.get('wake_detected') and hasattr(self,'_wake_detected'):
                    self._wake_detected(wake_only=bool(result.get('wake_only')));continue
                if result.get('entry_rejected') and hasattr(self,'_entry_rejected'):
                    self._entry_rejected();continue
                if result.get('error'):
                    self.controller.cancel();self.transcription.update(state='ERROR',error=result['error'])
                    continue
                if result.get('channel_event'):
                    event=result['channel_event']
                    self.controller.channel_event(event,result.get('pcm',b''),owner,self.transcriber.feedback_assets,self.requested_at)
                    if event['kind']=='start':self.transcription['state']='GENERATING'
                    elif event['kind']=='transcript':self.transcription.update(text=event['text'],state='GENERATING')
                    elif event['kind']=='end':self.transcription['state']='PLAYING'
                elif result.get('network_complete'):
                    self.controller.channel_complete(owner,result['network_complete'])
            return
        result = self.transcriber.poll()
        if not result:return
        owner = result.get('context',{})
        if (owner.get('request_id') != self.transcription['request_id']
                or owner.get('capture_id') != self.transcription['capture_id']):return
        if result.get('error'):
            self.transcription.update(state='ERROR',error=result['error'],text='')
        else:
            self.transcription.update(state='READY' if result.get('text') else 'EMPTY',
                text=result.get('text',''),error='',recognition_ms=result.get('recognition_ms'),model_id=result.get('model_id'))
            if result.get('voice_reply'):
                try:
                    self.controller.submit_generated(result['voice_reply'],requested_at=self.requested_at)
                    self.transcription['voice_reply']={key:value for key,value in result['voice_reply'].items() if key!='path'}
                except Exception as exc:
                    self.transcription.update(state='ERROR',error='Voice playback rejected: '+str(exc))

    def configure_transcription(self,values):
        if self.auto_enabled: raise ValueError('请先结束连续对话')
        if self.transcriber is None:raise ValueError('Transcription adapter is unavailable')
        self.transcriber.configure(values)
        self._queue_transcription()
        return {'enabled':self.transcriber.enabled()}

    def __getattr__(self, name):
        return getattr(self.controller, name)

    @property
    def last_error(self):
        return self.controller.last_error

    @last_error.setter
    def last_error(self, value):
        self.controller.last_error = value

    def _playback_active(self):
        state = self.controller.public()
        return (state['phase'] != 'IDLE' or state['playing'] or state['paused']
                or state.get('pending_job') is not None
                or state.get('audio_output_state') not in ('NULL', 'EOS', 'IDLE_READY'))

    def _recording(self):
        return self.capture is not None and self.capture.snapshot()['state'] == 'RECORDING'

    def _collect(self, *, poll=True):
        if self.capture is None:
            if poll:self._poll_transcription()
            return
        snapshot = self.capture.snapshot()
        if snapshot['state'] == 'READY':
            self.utterance = self.capture.take()
            self.recording_state, self.recording_error = 'READY', ''
            self._queue_transcription()
        elif snapshot['state'] == 'ERROR':
            self.utterance = None
            self.recording_state, self.recording_error = 'ERROR', snapshot['error']
        elif snapshot['state'] == 'RECORDING':
            self.recording_state = 'RECORDING'
        if poll:self._poll_transcription()

    def record_start(self):
        if self.closed:
            raise ValueError('录音已关闭')
        if self.auto_enabled: raise ValueError('请先结束连续对话')
        self._collect()
        if getattr(self.transcriber,'feedback_assets',None) is not None and self._playback_active():self.cancel()
        if self._recording() or self._playback_active():
            raise ValueError('请先结束当前录音或播放')
        capture_id = self._capture_for(False).start()
        if hasattr(self.transcriber,'capture_started'):self.transcriber.capture_started(capture_id)
        if self.transcriber:self.transcriber.cancel()
        self.transcription = self._empty_transcription('IDLE')
        self.utterance = None
        self.recording_state, self.recording_error = 'RECORDING', ''
        self.last_error = ''
        return {'capture_id':capture_id, 'state':'RECORDING'}

    def record_stop(self):
        if self.auto_enabled: raise ValueError('连续对话会在停顿后自动提交，请使用结束对话')
        self._collect()
        if self._recording():
            self.capture.stop()
            self._collect()
        if self.utterance is None:
            raise ValueError(self.recording_error or '当前没有录音')
        return self.utterance.metadata()

    def take_recording(self, capture_id):
        self._collect()
        if self.utterance is None or self.utterance.capture_id != capture_id or self._recording():
            raise ValueError('录音已取消、替换或尚未完成')
        result, self.utterance = self.utterance, None
        self.recording_state = 'IDLE'
        return result

    def submit(self, *args, **kwargs):
        if self.auto_enabled: raise ValueError('请先结束连续对话')
        self._collect()
        if self._recording():
            raise ValueError('请先停止录音')
        return self.controller.submit(*args, **kwargs)

    def toggle_pause(self):
        if self._recording():
            raise ValueError('录音期间没有可暂停的播放')
        return self.controller.toggle_pause()

    def cancel(self):
        self.auto_enabled = False; self.auto_state = 'STOPPED'; self.auto_error = ''
        self.rearm_at = self.ack_deadline = None
        if self.capture is not None:
            self.capture.cancel()
        self.utterance = None
        self.recording_state, self.recording_error = 'CANCELLED', ''
        if self.transcriber:
            self.transcriber.cancel()
            if hasattr(self.transcriber,'reset_enrollment'):self.transcriber.reset_enrollment()
        self.transcription = self._empty_transcription('CANCELLED')
        return self.controller.cancel()

    def event(self, name):
        if name in ('cancel', 'reset'):
            self.cancel()
        elif self._recording():
            raise ValueError('请先停止录音')
        elif self.auto_enabled:
            raise ValueError('请先结束连续对话')
        return self.controller.event(name)

    def tick(self):
        self._collect()
        result=self.controller.tick()
        if hasattr(self.controller,'take_completion'):
            while True:
                complete=self.controller.take_completion()
                if complete is None:break
                owner,value=complete
                if (owner.get('request_id') != self.transcription['request_id']
                        or owner.get('capture_id') != self.transcription['capture_id']): continue
                self.transcriber.acknowledge(owner,value)
                self.transcription['state']='ANSWERED'
                if self.auto_enabled:
                    self.auto_turns += 1
                    self.rearm_at = self.clock()+.5
                    self.ack_deadline = self.clock()+7
        self._auto_tick()
        return result

    def public(self):
        # Status reads may report capture completion, but never pump another
        # PCM burst after the tick's bounded batch or mutate visual playback.
        RecordingController._collect(self,poll=False)
        state = self.controller.public()
        snapshot = self.capture.snapshot() if self.capture is not None else {}
        recording = self._recording()
        # CapturedAudio/AudioRef are frozen and PCM is immutable bytes.
        # Keep only one completed utterance; a new object invalidates the cache.
        utterance=self.utterance
        if isinstance(utterance,CapturedAudio) and isinstance(utterance.pcm,bytes):
            if getattr(self,'_public_utterance',None) is not utterance:
                self._public_utterance=utterance;self._public_metadata=utterance.metadata()
            metadata=dict(self._public_metadata,format=dict(self._public_metadata['format']))
        else:
            self._public_utterance=None
            metadata=utterance.metadata() if utterance is not None else None
        service=self.transcriber.public() if self.transcriber else {'enabled':False,'pending':False}
        playback_active=(state['phase']!='IDLE' or state['playing'] or state['paused']
                         or state.get('pending_job') is not None
                         or state.get('audio_output_state') not in ('NULL','EOS','IDLE_READY'))
        state['audio_frontend']={'enabled':self.audio_frontend['enabled'],
            'current':snapshot.get('audio_frontend',{})}
        state['local_recording'] = {'state':self.recording_state,
            'sample_count':snapshot.get('sample_count',0),
            'duration_seconds':snapshot.get('sample_count',0)/16000,
            'error':self.recording_error,'result':metadata,
            'can_start':not self.closed and not recording and not playback_active,
            'can_stop':recording,'max_seconds':20}
        state['local_transcription'] = dict(self.transcription,
            service=service)
        state['automatic_conversation'] = {'enabled':self.auto_enabled,'state':self.auto_state,
            'error':self.auto_error,'completed_turns':self.auto_turns,
            'speech_active':recording and snapshot.get('speech_active',False),
            'can_start':not self.closed and not self.auto_enabled and not recording and not playback_active
                and bool(self.transcriber and self.transcriber.enabled()
                         and service.get('streaming')
                         and service.get('feedback_ready')
                         and not service.get('pending')),
            'can_stop':self.auto_enabled}
        return state

    def close(self):
        self.cancel()
        if self.capture is not None:
            self.capture.close()
        if self.transcriber:self.transcriber.close()
        self.closed = True
