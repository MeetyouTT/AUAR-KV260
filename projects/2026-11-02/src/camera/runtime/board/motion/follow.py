"""Pan centering from actual selected-track measurements, with latched stops.

Pulse units are microseconds, not measured shaft degrees. A fixed camera needs
measured pointing anchors; error integration is only for an axis-mounted camera.
No transport opening, FPGA loading, calibration adoption, or ARM happens here.
"""
from dataclasses import dataclass
import math
from common.motion_observation import MAX_AGE_MS, ObservationError, integer, number, validate
from .vsrv_driver import PhysicalReference, VSRVDriver


@dataclass(frozen=True)
class FollowConfig:
    rate_us_s: float = 40.0
    step_us: int = 4
    max_offset_us: int = 40
    filter_tau_ms: float = 100.0
    deadband_enter: float = .05
    deadband_exit: float = .025
    confirm_frames: int = 5
    min_score: float = .5
    min_box_width: float = 20.0
    submit_margin_ms: float = 20.0

    def __post_init__(self):
        if (not number(self.rate_us_s) or not 0 < self.rate_us_s <= 40
                or type(self.step_us) is not int or not 1 <= self.step_us <= 4
                or type(self.max_offset_us) is not int or not 1 <= self.max_offset_us <= 40
                or not number(self.filter_tau_ms) or not 0 < self.filter_tau_ms <= 1000
                or not number(self.deadband_exit) or not number(self.deadband_enter)
                or not 0 <= self.deadband_exit < self.deadband_enter <= .25
                or type(self.confirm_frames) is not int or not 2 <= self.confirm_frames <= 20
                or not number(self.min_score) or not .1 <= self.min_score <= 1
                or not number(self.min_box_width) or not 1 <= self.min_box_width <= 320
                or not number(self.submit_margin_ms) or not 1 <= self.submit_margin_ms <= 50):
            raise ValueError('Invalid bounded pan configuration')


@dataclass(frozen=True)
class FixedCameraAnchors:
    """Measured left / centre / right pulse anchors in normalized image x."""
    boot_id: str
    camera_epoch: str
    setup_id: str
    reference_us: int
    polarity: int
    left_x: float
    left_us: int
    right_x: float
    right_us: int
    evidence: str
    verified: bool

    def __post_init__(self):
        if (not all(isinstance(x, str) and x for x in
                    (self.boot_id, self.camera_epoch, self.setup_id, self.evidence))
                or self.verified is not True or type(self.polarity) is not int or self.polarity not in (-1, 1)
                or any(type(x) is not int or not 1400 <= x <= 1600
                       for x in (self.reference_us, self.left_us, self.right_us))
                or not number(self.left_x) or not number(self.right_x)
                or not -1 <= self.left_x < 0 < self.right_x <= 1
                or self.polarity*(self.left_us-self.reference_us) >= 0
                or self.polarity*(self.right_us-self.reference_us) <= 0):
            raise ValueError('Verified fixed-camera pointing anchors required')

    def pulse(self, error):
        if error < 0:
            return self.reference_us+(self.left_us-self.reference_us)*min(1., error/self.left_x)
        return self.reference_us+(self.right_us-self.reference_us)*min(1., error/self.right_x)


class ShadowDriver:
    """No IO; acknowledgements describe software commands, never hardware."""
    def __init__(self):
        self.submissions = []
        self.stops = 0

    def submit(self, pulse, source_time, freshness_s, margin_s):
        self.submissions.append((pulse, source_time))
        return {'outcome': 'ACCEPTED', 'scope': 'SOFTWARE_SHADOW'}

    def stop(self):
        self.stops += 1


class PanFollowController:
    def __init__(self, driver, boot_id, *, reference_us=1500, polarity=-1,
                 camera_moves_with_axis=True, anchors=None, config=None, physical=False):
        if (not isinstance(boot_id, str) or not boot_id or type(reference_us) is not int
                or not 1400 <= reference_us <= 1600 or type(polarity) is not int or polarity not in (-1, 1)
                or type(camera_moves_with_axis) is not bool or type(physical) is not bool):
            raise ValueError('Explicit pan setup required')
        if physical:
            ref = getattr(driver, 'reference', None)
            if (not isinstance(driver, VSRVDriver) or not isinstance(ref, PhysicalReference)
                    or (driver.boot_id, ref.boot_id, ref.reference_us, ref.polarity, ref.camera_moves_with_axis)
                    != (boot_id, boot_id, reference_us, polarity, camera_moves_with_axis)):
                raise ValueError('Already-armed verified VSRV driver and matching physical reference required')
        elif not isinstance(driver, ShadowDriver):
            raise ValueError('Shadow mode only accepts the no-IO shadow driver')
        if camera_moves_with_axis:
            if anchors is not None:
                raise ValueError('Fixed-camera mapping cannot control an axis-mounted camera')
        elif (not isinstance(anchors, FixedCameraAnchors)
              or (anchors.boot_id, anchors.reference_us, anchors.polarity) != (boot_id, reference_us, polarity)):
            raise ValueError('A stationary camera requires measured anchors, never integrated image error')
        if physical and anchors is not None and anchors.setup_id != driver.reference.setup_id:
            raise ValueError('Anchor setup does not match physical reference')
        self.driver, self.boot, self.physical = driver, boot_id, physical
        self.reference, self.polarity, self.anchors = reference_us, polarity, anchors
        self.config = config or FollowConfig()
        self.low = max(1400, reference_us-self.config.max_offset_us)
        self.high = min(1600, reference_us+self.config.max_offset_us)
        self.context = self.target = self.last_source = self.last_payload = None
        self.last_now = self.filtered = None
        self.warmup = self.accepted = 0
        self.engaged = False
        self.position = float(reference_us)
        self.pulse_us = reference_us
        self.stopped = False
        self.reason = 'WAITING_FOR_TARGET'
        self.stop_confirmed = None
        self.last_result = None

    def status(self):
        return {'state': 'DISARMED' if self.stopped else 'FOLLOWING' if self.accepted else 'WAITING',
                'reason': self.reason, 'scope': 'PHYSICAL_VSRV' if self.physical else 'SOFTWARE_SHADOW',
                'physical_actuation': self.physical, 'accepted_commands': self.accepted,
                'target': self.target, 'warmup_frames': self.warmup,
                'pulse_us': self.pulse_us, 'pulse_limits_us': [self.low, self.high],
                'filtered_error': self.filtered, 'source_mono_ms': None if self.last_source is None else self.last_source[1],
                'stop_confirmed': self.stop_confirmed, 'mechanical_angle_measured': False}

    def stop(self, reason='STOP'):
        self.stopped, self.reason = True, reason
        try:
            self.driver.stop()
            self.stop_confirmed = True
        except Exception:
            self.stop_confirmed = False
            raise
        return self.status()

    def poll(self, now_ms):
        if self.stopped:
            return self.status()
        if not integer(now_ms) or self.last_now is not None and now_ms < self.last_now:
            return self.stop('INVALID_CLOCK')
        self.last_now = now_ms
        if self.last_source is not None and now_ms-self.last_source[1] >= MAX_AGE_MS:
            return self.stop('SOURCE_EXPIRED')
        return self.status()

    def observe(self, value, now_ms, *, allow_fixture=False):
        self.poll(now_ms)
        if self.stopped:
            return self.status()
        try:
            packet = validate(value, self.boot, now_ms, allow_fixture=allow_fixture and not self.physical)
        except ObservationError as exc:
            if self.context is None and str(exc) in ('SOURCE_NO_TARGET', 'SOURCE_EXPIRED'):
                self.reason = str(exc)
                return self.status()
            return self.stop(str(exc))
        context = (packet['service_epoch'], packet['camera_epoch'], packet['frame_width'], packet['frame_height'])
        target = packet['target']
        key = (target['track_id'], target['track_generation'])
        if self.context is not None and context != self.context:
            return self.stop('CAMERA_CONTEXT_CHANGED')
        if self.target is not None and key != self.target:
            return self.stop('TARGET_CHANGED')
        if self.anchors is not None and packet['camera_epoch'] != self.anchors.camera_epoch:
            return self.stop('ANCHOR_CAMERA_CHANGED')
        source = (packet['source_frame_id'], packet['source_mono_ms'])
        payload = (context, key, tuple(target['box']), target['score'])
        if self.last_source is not None:
            if source == self.last_source:
                if payload != self.last_payload:
                    return self.stop('SOURCE_MUTATED')
                self.reason = 'NO_NEW_SOURCE'
                return self.status()
            if source[0] <= self.last_source[0] or source[1] <= self.last_source[1]:
                return self.stop('SOURCE_REORDERED')
        x, y, w, h = target['box']
        if target['score'] < self.config.min_score or w < self.config.min_box_width:
            return self.stop('TARGET_QUALITY')
        if x < 1 or x+w > packet['frame_width']-1:
            return self.stop('HORIZONTAL_BORDER')
        error = (x+w/2)/(packet['frame_width']/2)-1
        dt = None if self.last_source is None else source[1]-self.last_source[1]
        if dt is not None and not 0 < dt < MAX_AGE_MS:
            return self.stop('SOURCE_GAP')
        self.context, self.target = context, key
        self.last_source, self.last_payload = source, payload
        self.filtered = error if self.filtered is None else self.filtered+(1-math.exp(-dt/self.config.filter_tau_ms))*(error-self.filtered)
        self.warmup += 1
        if self.warmup < self.config.confirm_frames:
            self.reason = 'CONFIRMING_TARGET'
            return self.status()
        if abs(self.filtered) <= self.config.deadband_exit:
            self.engaged = False
        elif abs(self.filtered) >= self.config.deadband_enter:
            self.engaged = True
        error = self.filtered if self.engaged else 0.
        limit = min(self.config.step_us, self.config.rate_us_s*dt/1000)
        if self.anchors is not None:
            goal = self.anchors.pulse(error)
            delta = max(-limit, min(limit, goal-self.position))
        else:
            delta = max(-limit, min(limit, self.polarity*self.config.rate_us_s*error*dt/1000))
        candidate = max(self.low, min(self.high, self.position+delta))
        pulse = round(candidate)
        try:
            result = self.driver.submit(pulse, source[1]/1000., MAX_AGE_MS/1000., self.config.submit_margin_ms/1000.)
        except Exception:
            self.stop('TRANSPORT_ERROR')
            raise
        self.last_result = result
        if result.get('outcome') != 'ACCEPTED':
            return self.stop(str(result.get('reason', 'ACK_NOT_ACCEPTED')))
        self.position, self.pulse_us = candidate, pulse
        self.accepted += 1
        self.reason = 'AT_LIMIT' if pulse in (self.low, self.high) else 'CENTERED' if not self.engaged else 'FOLLOWING'
        return self.status()
