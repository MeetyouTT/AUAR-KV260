"""Serialize local capture and cached playback on the avatar controller owner."""
from board.runtime.audio.capture import Mcp01Capture


class RecordingController:
    def __init__(self, controller, *, capture_factory=Mcp01Capture):
        self.controller, self.capture_factory = controller, capture_factory
        self.capture = self.utterance = None
        self.recording_state = 'IDLE'
        self.recording_error = ''
        self.closed = False

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
            return
        snapshot = self.capture.snapshot()
        if snapshot['state'] == 'READY':
            self.utterance = self.capture.take()
            self.recording_state, self.recording_error = 'READY', ''
        elif snapshot['state'] == 'ERROR':
            self.utterance = None
            self.recording_state, self.recording_error = 'ERROR', snapshot['error']
        elif snapshot['state'] == 'RECORDING':
            self.recording_state = 'RECORDING'

    def record_start(self):
        if self.closed:
            raise ValueError('录音已关闭')
        self._collect()
        if self._recording() or self._playback_active():
            raise ValueError('请先结束当前录音或播放')
        if self.capture is None:
            self.capture = self.capture_factory(self._playback_active, max_seconds=20)
        capture_id = self.capture.start()
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
        return state

    def close(self):
        self.cancel()
        if self.capture is not None:
            self.capture.close()
        self.closed = True
