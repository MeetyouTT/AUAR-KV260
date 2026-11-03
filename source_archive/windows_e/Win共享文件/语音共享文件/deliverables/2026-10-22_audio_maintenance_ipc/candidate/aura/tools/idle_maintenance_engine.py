"""Review-only engine seam. No production import, IPC, watcher or USB access.

Use before PersistentGstAudioEngine in an MRO. The application must hold an
independent producer/capture barrier for the entire maintenance transaction.
The idle arguments are assertions by that owner, not a substitute for a gate.
Native set_state/get_state can themselves block: deadlines here bound repeated
polls only. A separate process supervisor is required for native hangs.
"""
from collections import deque
import threading


class IdleMaintenanceEngine:
    def configure_idle_maintenance(self, factory):
        # Call before the recovered engine constructor, which can call release.
        self._maintenance_factory = factory
        self._maintenance_owner = threading.get_ident()
        self._maintenance_attempts = deque()
        self._maintenance_requests = {}
        self.maintenance_state = 'NOT_REQUESTED'
        self.maintenance_reason = ''
        self.maintenance_request_id = None
        self.pipeline_epoch = 0
        self._maintenance_deadline = None

    def _check_owner(self):
        if threading.get_ident() != self._maintenance_owner:
            raise RuntimeError('Audio maintenance must run on the engine owner')

    def _held(self, reason):
        self.maintenance_state = 'FAILED_HELD'
        self.maintenance_reason = reason
        self.references.clear()
        self.device_ready = False

    def _stop_recovery_and_hold(self, reason):
        # Retain the object for owner/supervisor cleanup. This requests NULL;
        # it does not claim asynchronous native release has completed.
        if self.pipeline is not None:
            try:
                self.pipeline.set_state(self.gst.State.NULL)
            except Exception:
                pass
        self._held(reason)

    def request_idle_maintenance(self, *, request_id, expected_token, new_token,
                                 controller_idle, capture_idle, reference_idle,
                                 commands_pending=False):
        self._check_owner()
        if (type(request_id) is not str or not request_id or len(request_id) > 64
                or not all(c.isascii() and (c.isalnum() or c in '-_') for c in request_id)):
            return False
        signature = (expected_token, new_token, controller_idle, capture_idle,
                     reference_idle, commands_pending)
        if request_id in self._maintenance_requests:
            # Admission is idempotent; it never repeats native state changes.
            # Only the current transaction may be acknowledged again. Changed
            # content or an older transaction cannot replay a recovery.
            return (request_id == self.maintenance_request_id
                    and signature == self._maintenance_requests[request_id]
                    and all(type(a) is type(b) for a,b in
                            zip(signature,self._maintenance_requests[request_id])))
        if len(self._maintenance_requests) >= 32:
            return False
        if self.maintenance_state not in ('NOT_REQUESTED', 'READY_UNVERIFIED'):
            return False
        if (type(expected_token) is not int or type(new_token) is not int
                or expected_token != self.token or new_token != expected_token + 1):
            return False
        if (controller_idle is not True or capture_idle is not True
                or reference_idle is not True or commands_pending is not False
                or self.active or self.paused or self.audible or self.queue
                or self.intervals or self.pipeline is None or self.error):
            return False
        now = self.clock()
        while self._maintenance_attempts and now - self._maintenance_attempts[0] >= 600:
            self._maintenance_attempts.popleft()
        if (len(self._maintenance_attempts) >= 2 or (self._maintenance_attempts
                and now - self._maintenance_attempts[-1] < 60)):
            return False
        self._maintenance_attempts.append(now)
        self._maintenance_requests[request_id] = signature
        self.maintenance_request_id = request_id
        self.maintenance_state = 'CLOSING'
        self.maintenance_reason = ''
        self._maintenance_deadline = now + 2
        self.pipeline_epoch += 1
        self.references.clear()
        self._reset(new_token)
        self.device_ready = False
        try:
            if self.pipeline.set_state(self.gst.State.NULL) == self.gst.StateChangeReturn.FAILURE:
                self._held('NULL_STATE_FAILED')
        except Exception:
            self._held('NULL_STATE_EXCEPTION')
        return True  # Accepted is not successful; observe state and request_id.

    def _poll_closing(self):
        if self.clock() >= self._maintenance_deadline:
            self._held('NULL_STATE_TIMEOUT')
            return
        try:
            result, current, pending = self.pipeline.get_state(0)
        except Exception:
            self._held('NULL_QUERY_EXCEPTION')
            return
        if result == self.gst.StateChangeReturn.FAILURE:
            self._held('NULL_QUERY_FAILED')
            return
        if (result != self.gst.StateChangeReturn.SUCCESS
                or current != self.gst.State.NULL
                or pending != self.gst.State.VOID_PENDING):
            return
        # Only this observed NULL transition permits creating a second object.
        self.pipeline = self.source = self.sink = self.bus = None
        self.next_pts = 0
        try:
            self.pipeline, self.source, self.sink = self._maintenance_factory(self.gst, self.device)
            self.bus = self.pipeline.get_bus()
            self.maintenance_state = 'WARMING'
            self._maintenance_deadline = self.clock() + 8
            if self.pipeline.set_state(self.gst.State.PLAYING) == self.gst.StateChangeReturn.FAILURE:
                raise RuntimeError('Cannot start recovered pipeline')
        except Exception:
            # Keep a returned pipeline reachable for supervisor/close cleanup.
            # No retry creates another owner after a failed or uncertain start.
            if self.pipeline is not None:
                try:
                    self.pipeline.set_state(self.gst.State.NULL)
                except Exception:
                    pass
            self._held('REBUILD_FAILED')

    def poll(self):
        self._check_owner()
        state = self.maintenance_state
        if state == 'CLOSING':
            self._poll_closing()
            return self.snapshot()
        if state in ('FAILED_HELD', 'CLOSE_REQUESTED'):
            return self.snapshot()
        if state == 'WARMING' and self.clock() >= self._maintenance_deadline:
            # Do not resume on late readiness, including after a native stall.
            self._stop_recovery_and_hold('WARMUP_TIMEOUT')
            return self.snapshot()
        try:
            super().poll()
        except Exception:
            if state != 'WARMING':
                raise
            self._stop_recovery_and_hold('WARMUP_POLL_EXCEPTION')
            return self.snapshot()
        if state == 'WARMING':
            if self.clock() >= self._maintenance_deadline:
                self._stop_recovery_and_hold('WARMUP_TIMEOUT')
            elif self.error:
                self._held('WARMUP_DEVICE_ERROR')
            elif self.device_ready:
                self.maintenance_state = 'READY_UNVERIFIED'
        return self.snapshot()

    def command(self, message):
        self._check_owner()
        kind = message.get('type')
        maintaining = self.maintenance_state in ('CLOSING', 'WARMING', 'FAILED_HELD', 'CLOSE_REQUESTED')
        if maintaining and kind not in ('stop', 'close'):
            return False
        accepted = super().command(message)
        if accepted and kind == 'close':
            self.references.clear()
            self.maintenance_state = 'CLOSE_REQUESTED'
        elif accepted and kind == 'stop' and maintaining:
            # Stop still does not recreate/release a pipeline. Supersede this
            # request so that a late completion cannot reopen admission.
            self._held('STOP_DURING_MAINTENANCE')
        return accepted

    def take_references(self):
        if self.maintenance_state in ('CLOSING', 'WARMING', 'FAILED_HELD', 'CLOSE_REQUESTED'):
            self.references.clear()
            return []
        return [dict(frame, pipeline_epoch=self.pipeline_epoch)
                for frame in super().take_references()]

    def snapshot(self):
        result = super().snapshot()
        result.update(maintenance_state=self.maintenance_state,
                      maintenance_reason=self.maintenance_reason,
                      maintenance_request_id=self.maintenance_request_id,
                      pipeline_epoch=self.pipeline_epoch,
                      maintenance_admission_held=self.maintenance_state in
                          ('CLOSING', 'WARMING', 'FAILED_HELD', 'CLOSE_REQUESTED'),
                      usb_playback_health='UNVERIFIED')
        if self.maintenance_state in ('CLOSING', 'WARMING'):
            result['device_state'] = 'RECOVERING'
        elif self.maintenance_state == 'FAILED_HELD':
            result['device_state'] = 'MAINTENANCE_FAILED'
        return result
