"""Review-only recovery seam for the recovered persistent GStreamer engine.

No watcher, process restart, USB operation, or production import uses this module.
The owner must suspend turn creation/capture until recovery warmup completes.
USB health requires independent endpoint-specific evidence: a moving sink clock
does not establish successful USB playback.
"""
from collections import deque


class IdlePipelineRecovery:
    """Mix in before PersistentGstAudioEngine; call on the worker thread only.

    The caller atomically advances its content token before calling this method.
    All queued work carrying the old token is then rejected by the base engine.
    Automatic recovery and IPC/UI integration are intentionally absent.
    """

    def configure_idle_recovery(self, pipeline_factory):
        self._recovery_factory = pipeline_factory
        self._recovery_attempts = deque()
        self.pipeline_epoch = 0
        self.recovery_state = 'NOT_REQUESTED'
        self.recovery_detail = ''

    def recover_idle(self, *, expected_token, new_token, controller_idle, capture_idle,
                     commands_pending=False):
        # These checks precede every mutation, including releasing the device.
        if type(expected_token) is not int or type(new_token) is not int:
            return False
        if expected_token != self.token or new_token != expected_token + 1:
            return False
        if (controller_idle is not True or capture_idle is not True or
                commands_pending is not False or self.active or self.paused or
                self.audible or self.queue or self.intervals):
            return False
        if self.recovery_state == 'WARMING':
            return False
        now = self.clock()
        # Initial engineering limits; field tuning has not been accepted.
        while self._recovery_attempts and now - self._recovery_attempts[0] >= 600:
            self._recovery_attempts.popleft()
        if (len(self._recovery_attempts) >= 2 or
                (self._recovery_attempts and now - self._recovery_attempts[-1] < 60)):
            return False
        self._recovery_attempts.append(now)
        self.recovery_state = 'WARMING'
        self.recovery_detail = ''
        self.pipeline_epoch += 1
        self.references.clear()
        self.bus = None
        self.release()
        self.next_pts = 0
        self._reset(new_token)
        self.error = ''
        try:
            self.pipeline, self.source, self.sink = self._recovery_factory(self.gst, self.device)
            self.bus = self.pipeline.get_bus()
            if self.pipeline.set_state(self.gst.State.PLAYING) == self.gst.StateChangeReturn.FAILURE:
                raise RuntimeError('Persistent ALSA recovery start failed')
        except Exception as exc:
            self.fail(type(exc).__name__ + ': ' + str(exc))
            self.bus = None
            self.recovery_state = 'ERROR'
            self.recovery_detail = self.error
        return True  # Accepted request; inspect state/error, not this bool, for success.

    def release(self):
        references = getattr(self, 'references', None)
        if references is not None:
            references.clear()
        self.bus = None
        return super().release()

    def command(self, message):
        if self.recovery_state == 'WARMING' and message.get('type') in ('play', 'stream'):
            return False  # Owner must wait for readiness before creating another turn.
        accepted = super().command(message)
        if accepted and message.get('type') == 'close':
            self.recovery_state = 'CLOSED'
        return accepted

    def poll(self):
        # The existing worker calls poll every 10ms; no blocking warmup here.
        super().poll()
        if self.recovery_state == 'WARMING':
            if self.error:
                self.recovery_state = 'ERROR'
                self.recovery_detail = self.error
            elif self.device_ready:
                self.recovery_state = 'READY_UNVERIFIED'
            elif self.clock() - self._recovery_attempts[-1] >= 8:
                self.fail('Persistent ALSA recovery warmup timed out')
                self.bus = None
                self.recovery_state = 'ERROR'
                self.recovery_detail = self.error
        return self.snapshot()

    def take_references(self):
        # Do not reset reference_sequence: consumers must also reset AEC state
        # on pipeline_epoch changes before resuming capture.
        return [dict(frame, pipeline_epoch=self.pipeline_epoch)
                for frame in super().take_references()]

    def snapshot(self):
        result = super().snapshot()
        result.update(pipeline_epoch=self.pipeline_epoch,
                      recovery_state=self.recovery_state,
                      recovery_detail=self.recovery_detail,
                      usb_playback_health='UNVERIFIED')
        if self.recovery_state == 'WARMING':
            result['device_state'] = 'RECOVERING'
        return result
