"""Runtime contracts. Times are integer milliseconds in one clock domain."""
from dataclasses import asdict, dataclass
import math
from typing import Tuple


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class FrameRef:
    clock_domain: str
    camera_epoch: str
    frame_id: int
    captured_at_ms: int
    width: int
    height: int
    timestamp_semantics: str = "synthetic"

    def __post_init__(self):
        if (not self.clock_domain or not self.camera_epoch or not self.timestamp_semantics
                or not integer(self.frame_id, 1) or not integer(self.captured_at_ms)
                or not integer(self.width, 1) or not integer(self.height, 1)):
            raise ValueError("Invalid frame reference")

    @property
    def key(self):
        return (self.clock_domain, self.camera_epoch, self.frame_id)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Detection:
    box: Tuple[float, float, float, float]  # original-image x, y, width, height
    score: float
    label: str = "person"

    def __post_init__(self):
        if (len(self.box) != 4 or not all(finite(v) for v in self.box)
                or min(self.box[2:]) <= 0 or not finite(self.score)
                or not 0 <= self.score <= 1 or not self.label):
            raise ValueError("Invalid detection")


@dataclass(frozen=True)
class TrackObservation:
    frame: FrameRef
    track_id: int
    generation: int
    box: Tuple[float, float, float, float]
    score: float
    velocity_x_px_s: float
    visible: bool
    confirmed: bool

    def __post_init__(self):
        Detection(self.box, self.score)
        if (not integer(self.track_id, 1) or not integer(self.generation, 1)
                or not finite(self.velocity_x_px_s)
                or type(self.visible) is not bool or type(self.confirmed) is not bool):
            raise ValueError("Invalid observed track")

    @property
    def target_key(self):
        return (self.frame.camera_epoch, self.track_id, self.generation)

    @property
    def observation_key(self):
        return self.frame.key + (self.track_id, self.generation)


@dataclass(frozen=True)
class PositionEvidence:
    track: TrackObservation
    deadline_ms: int
    policy: str

    def __post_init__(self):
        if not integer(self.deadline_ms) or self.deadline_ms < self.track.frame.captured_at_ms:
            raise ValueError("Invalid source deadline")

    def usable(self, now_ms, clock_domain):
        return (integer(now_ms) and self.track.frame.clock_domain == clock_domain
                and self.track.visible and self.track.confirmed
                and self.track.frame.captured_at_ms <= now_ms < self.deadline_ms)


@dataclass(frozen=True)
class MotionCommand:
    session_id: str
    recovery_generation: int
    seq: int
    evidence: PositionEvidence
    requested_axis: float  # normalized virtual axis; never a calibrated angle/PWM

    def __post_init__(self):
        if (not self.session_id or not integer(self.recovery_generation, 1)
                or not integer(self.seq, 1) or not finite(self.requested_axis)):
            raise ValueError("Invalid motion command")
