"""Software model of source-deadline semantics, with no hardware IO."""
import uuid
from collections import OrderedDict
from common.contracts import integer


class SimulationGuard:
    scope = "SOFTWARE_SIMULATION"
    physical_actuation = False

    def __init__(self, clock_domain, enabled=True):
        self.clock_domain, self.enabled = clock_domain, enabled
        self.session_id = uuid.uuid4().hex
        self.recovery_generation = 1
        self.seq = 0
        self.active = False
        self.target_key = None
        self.camera_epoch = None
        self._recovery_floor = None
        self.deadline_ms = None
        self.reason = "STARTUP"
        self._last_source = None
        self._last_source_deadline = None
        self._source_deadlines = OrderedDict()
        self._last_now = None
        self.requested_axis = 0.0

    def recover(self, camera_epoch):
        if not isinstance(camera_epoch, str) or not camera_epoch:
            raise ValueError("Camera epoch required for recovery")
        self.stop("RECOVERY")
        self.recovery_generation += 1
        self.seq = 0
        self.camera_epoch = camera_epoch
        self.target_key = None
        self._recovery_floor = self._last_source[:3] if self._last_source else None

    def select_target(self, target_key):
        if target_key != self.target_key:
            self.stop("TARGET_CHANGED")
            self.target_key = target_key

    def stop(self, reason="STOP"):
        self.active = False
        self.deadline_ms = None
        self.reason = reason

    def poll(self, now_ms):
        if not integer(now_ms) or (self._last_now is not None and now_ms < self._last_now):
            self.stop("INVALID_CLOCK")
            raise ValueError("Guard clock reversed/invalid")
        self._last_now = now_ms
        if self.active and now_ms >= self.deadline_ms:
            self.stop("SOURCE_EXPIRED")
        return self.snapshot()

    def submit(self, command, now_ms):
        self.poll(now_ms)
        e = command.evidence
        source = e.track.observation_key
        reason = None
        if not self.enabled:
            reason = "MOTION_DISABLED"
        elif (command.session_id, command.recovery_generation) != (self.session_id, self.recovery_generation):
            reason = "CONTEXT_MISMATCH"
        elif e.track.frame.camera_epoch != self.camera_epoch or e.track.target_key != self.target_key:
            reason = "CAMERA_OR_TARGET_GENERATION_MISMATCH"
        elif command.seq != self.seq + 1:
            reason = "REPLAY_OR_SEQUENCE"
        elif not e.usable(now_ms, self.clock_domain):
            reason = "INVALID_OR_EXPIRED_SOURCE"
        elif not -1 <= command.requested_axis <= 1:
            reason = "AXIS_RANGE"
        elif (self._recovery_floor is not None and source[:2] == self._recovery_floor[:2]
              and source[2] <= self._recovery_floor[2]):
            reason = "NEW_OBSERVATION_REQUIRED_AFTER_RECOVERY"
        elif source in self._source_deadlines and e.deadline_ms > self._source_deadlines[source]:
            reason = "SOURCE_DEADLINE_EXTENSION"
        elif (self._last_source is not None and source[:2] == self._last_source[:2]
              and source[2] < self._last_source[2]):
            reason = "OLD_SOURCE"
        if reason:
            return {"accepted": False, "reason": reason, "scope": self.scope,
                    "physical_actuation": False, "ack_seq": self.seq}
        self._source_deadlines = OrderedDict((k, v) for k, v in self._source_deadlines.items() if v > now_ms)
        if source not in self._source_deadlines and len(self._source_deadlines) >= 256:
            return {"accepted": False, "reason": "SOURCE_LEDGER_FULL", "scope": self.scope,
                    "physical_actuation": False, "ack_seq": self.seq}
        self._source_deadlines[source] = e.deadline_ms
        self.seq = command.seq
        self.target_key = e.track.target_key
        self.deadline_ms = e.deadline_ms
        self._last_source, self._last_source_deadline = source, e.deadline_ms
        self.active, self.reason = True, "ACCEPTED"
        self.requested_axis = command.requested_axis
        return {"accepted": True, "reason": self.reason, "ack_seq": self.seq,
                "deadline_ms": self.deadline_ms, "scope": self.scope, "physical_actuation": False}

    def snapshot(self):
        return {"scope": self.scope, "physical_actuation": False, "active": self.active,
                "reason": self.reason, "ack_seq": self.seq, "deadline_ms": self.deadline_ms,
                "requested_axis": self.requested_axis}
