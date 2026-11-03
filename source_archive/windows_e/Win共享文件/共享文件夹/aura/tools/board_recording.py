"""Serialize local capture and cached playback on the avatar controller owner."""
import time
from board.runtime.audio.capture import Mcp01Capture


class RecordingController:
    def __init__(self, controller, *, capture_factory=Mcp01Capture, transcriber=None):
        self.controller, self.capture_factory = controller, capture_factory
        self.capture = self.utterance = None
        self.recording_state = 'IDLE'
        self.recording_error = ''
        self.closed = False
        self.transcriber = transcriber
        self.transcription = self._empty_transcription('IDLE' if transcriber and transcriber.enabled() else 'DISABLED')

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
                or state.get('audio_output_state') not in ('NULL', 'EOS'))

    def _recording(self):
        return self.capture is not None and self.capture.snapshot()['state'] == 'RECORDING'

    def _collect(self):
        if self.capture is None:
            self._poll_transcription()
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
        self._poll_transcription()

    def record_start(self):
        if self.closed:
            raise ValueError('录音已关闭')
        self._collect()
        if self._recording() or self._playback_active():
            raise ValueError('请先结束当前录音或播放')
        if self.capture is None:
            self.capture = self.capture_factory(self._playback_active, max_seconds=20)
        capture_id = self.capture.start()
        if self.transcriber:self.transcriber.cancel()
        self.transcription = self._empty_transcription('IDLE')
        self.utterance = None
        self.recording_state, self.recording_error = 'RECORDING', ''
        self.last_error = ''
        return {'capture_id':capture_id, 'state':'RECORDING'}

    def record_stop(self):
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
        self._collect()
        if self._recording():
            raise ValueError('请先停止录音')
        return self.controller.submit(*args, **kwargs)

    def toggle_pause(self):
        if self._recording():
            raise ValueError('录音期间没有可暂停的播放')
        return self.controller.toggle_pause()

    def cancel(self):
        if self.capture is not None:
            self.capture.cancel()
        self.utterance = None
        self.recording_state, self.recording_error = 'CANCELLED', ''
        if self.transcriber:self.transcriber.cancel()
        self.transcription = self._empty_transcription('CANCELLED')
        return self.controller.cancel()

    def event(self, name):
        if name in ('cancel', 'reset'):
            self.cancel()
        elif self._recording():
            raise ValueError('请先停止录音')
        return self.controller.event(name)

    def tick(self):
        self._collect()
        return self.controller.tick()

    def public(self):
        self._collect()
        state = self.controller.public()
        snapshot = self.capture.snapshot() if self.capture is not None else {}
        recording = self._recording()
        metadata = self.utterance.metadata() if self.utterance is not None else None
        state['local_recording'] = {'state':self.recording_state,
            'sample_count':snapshot.get('sample_count',0),
            'duration_seconds':snapshot.get('sample_count',0)/16000,
            'error':self.recording_error,'result':metadata,
            'can_start':not self.closed and not recording and not self._playback_active(),
            'can_stop':recording,'max_seconds':20}
        state['local_transcription'] = dict(self.transcription,
            service=self.transcriber.public() if self.transcriber else {'enabled':False,'pending':False})
        return state

    def close(self):
        self.cancel()
        if self.capture is not None:
            self.capture.close()
        if self.transcriber:self.transcriber.close()
        self.closed = True
