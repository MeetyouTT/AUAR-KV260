"""The only command writer for the framework's virtual axis."""
from common.contracts import MotionCommand


class MotionService:
    def __init__(self, guard):
        self.guard = guard
        self.target_key = None

    def update(self, evidence, now_ms):
        if evidence is None or not evidence.usable(now_ms, self.guard.clock_domain):
            self.guard.stop("NO_FRESH_TARGET")
            return {"accepted": False, "reason": "NO_FRESH_TARGET", "physical_actuation": False}
        track = evidence.track
        if self.target_key != track.target_key:
            self.target_key = track.target_key
        self.guard.select_target(track.target_key)
        axis = ((track.box[0] + track.box[2] / 2) - track.frame.width / 2) / (track.frame.width / 2)
        command = MotionCommand(self.guard.session_id, self.guard.recovery_generation,
                                self.guard.seq + 1, evidence, max(-1.0, min(1.0, axis)))
        return self.guard.submit(command, now_ms)
