"""Candidate uncertainty model; calibration is not a physical safety proof."""
from collections import OrderedDict
import math
from common.contracts import PositionEvidence


class FreshnessPolicy:
    def __init__(self, config):
        self.config = config
        self._deadlines = OrderedDict()

    def evidence(self, track):
        lifetime_ms = self.config["fixed_ms"]
        if self.config["policy"] == "variable":
            p = self.config["calibration"]
            budget = p["allowed_error_px"] - p["u0_px"]
            velocity = abs(track.velocity_x_px_s) + p["delta_v_px_s"]
            acceleration = p["acceleration_px_s2"]
            if budget <= 0:
                seconds = 0.0
            elif acceleration > 0:
                seconds = 2 * budget / (velocity + math.sqrt(velocity * velocity + 2 * acceleration * budget))
            else:
                seconds = budget / velocity if velocity > 0 else p["cap_ms"] / 1000.0
            lifetime_ms = max(0, min(p["cap_ms"], math.floor(seconds * 1000)))
        deadline = track.frame.captured_at_ms + lifetime_ms
        key = track.observation_key
        # Re-evaluating the same source, including after a policy change, cannot renew it.
        deadline = min(deadline, self._deadlines.get(key, deadline))
        self._deadlines[key] = deadline
        self._deadlines.move_to_end(key)
        while len(self._deadlines) > 256:
            self._deadlines.popitem(last=False)
        return PositionEvidence(track, deadline, self.config["policy"])
