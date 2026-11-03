"""Face-only edge following math. This module has no actuator or IO imports."""
from dataclasses import dataclass
from collections import deque
import math
from statistics import median
from common.motion_observation import MAX_AGE_MS, ObservationError, validate


@dataclass(frozen=True)
class EdgeConfig:
    left_ratio: float = 0.
    right_ratio: float = .8064720153808593
    filter_tau_ms: float = 80.
    gain_us_s: float = 320.
    maximum_speed_us_s: float = 60.
    minimum_speed_us_s: float = 8.
    base_speed_us_s: float = 24.
    median_window: int = 3
    velocity_filter_tau_ms: float = 100.
    velocity_gain_us: float = 120.
    face_velocity_clip_ratio_s: float = 1.
    maximum_acceleration_us_s2: float = 120.
    maximum_step_us: float = 4.
    confirm_frames: int = 3
    edge_confirm_frames: int = 2
    minimum_score: float = .9
    minimum_face_pixels: float = 48.
    maximum_face_width_ratio: float = .7
    minimum_us: int = 1425
    maximum_us: int = 1505

    def __post_init__(self):
        values = (self.left_ratio, self.right_ratio, self.filter_tau_ms, self.gain_us_s,
                  self.maximum_speed_us_s, self.minimum_speed_us_s,
                  self.base_speed_us_s,self.velocity_filter_tau_ms,self.velocity_gain_us,self.face_velocity_clip_ratio_s,
                  self.maximum_acceleration_us_s2, self.maximum_step_us,
                  self.minimum_score, self.minimum_face_pixels, self.maximum_face_width_ratio)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError('Finite face control parameters required')
        if not (0 <= self.left_ratio < self.right_ratio <= 1 and self.right_ratio-self.left_ratio >= .2
                and 30 <= self.filter_tau_ms <= 500 and 1 <= self.gain_us_s <= 400
                and 0 < self.minimum_speed_us_s <= self.base_speed_us_s <= self.maximum_speed_us_s <= 60
                and type(self.median_window) is int and self.median_window in (1,3,5)
                and 30<=self.velocity_filter_tau_ms<=300 and 0<=self.velocity_gain_us<=200
                and .1<=self.face_velocity_clip_ratio_s<=2
                and 1 <= self.maximum_acceleration_us_s2 <= 120
                and 0 < self.maximum_step_us <= 4
                and type(self.confirm_frames) is int and 2 <= self.confirm_frames <= 10
                and type(self.edge_confirm_frames) is int and 2 <= self.edge_confirm_frames <= 5
                and .9 <= self.minimum_score <= 1 and self.minimum_face_pixels >= 24
                and .2 <= self.maximum_face_width_ratio <= .7
                and type(self.minimum_us) is int and type(self.maximum_us) is int
                and 1425 <= self.minimum_us < self.maximum_us <= 1505):
            raise ValueError('Invalid finite face-zone control parameters')


class FaceEdgeController:
    def __init__(self, boot, reference_us, *, polarity=1, config=None):
        self.config = config or EdgeConfig()
        if (not isinstance(boot, str) or not boot or type(reference_us) is not int
                or not self.config.minimum_us <= reference_us <= self.config.maximum_us
                or type(polarity) is not int or polarity not in (-1, 1)):
            raise ValueError('Current stopped command and observed polarity required')
        self.boot, self.polarity = boot, polarity
        self.position, self.pulse_us = float(reference_us), reference_us
        self.velocity = 0.
        self.context = self.source = self.payload = self.last_now = None
        self.filtered_center = self.filtered_width = None
        self.centers=deque(maxlen=self.config.median_window);self.widths=deque(maxlen=self.config.median_window)
        self.raw_center=self.median_center=None;self.face_velocity=0.
        self.requested_speed=self.step_speed=0.;self.frame_width=640
        self.warmup = self.edge_count = 0
        self.edge_candidate = self.edge = 0
        self.stopped = False
        self.reason = 'WAITING_FOR_FACE'
        self.new_source = False
        self.proposals = 0

    def status(self):
        return {'state': 'DISARMED' if self.stopped else 'EDGE_FOLLOW' if self.edge else
                'DECELERATING' if abs(self.velocity) > .001 else 'HOLD',
                'reason': self.reason, 'pulse_us': self.pulse_us,
                'velocity_us_s': self.velocity, 'edge': self.edge,
                'filtered_center_ratio': self.filtered_center,
                'filtered_width_ratio': self.filtered_width,
                'raw_center_ratio':self.raw_center,'median_center_ratio':self.median_center,
                'median_window':self.config.median_window,'face_image_velocity_ratio_s':self.face_velocity,
                'face_image_velocity_px_s':self.face_velocity*self.frame_width,
                'requested_velocity_us_s':self.requested_speed,'step_velocity_us_s':self.step_speed,
                'source_mono_ms': self.source[1] if self.source else None,
                'new_source': self.new_source, 'confirmed_sources': self.warmup,
                'proposals': self.proposals, 'limits_us': [self.config.minimum_us, self.config.maximum_us]}

    def stop(self, reason):
        self.stopped, self.reason, self.velocity, self.edge = True, reason, 0., 0
        self.requested_speed=self.step_speed=0.
        return self.status()

    def observe(self, value, now_ms, *, allow_fixture=False):
        self.new_source = False
        if self.stopped:
            return self.status()
        if type(now_ms) is not int or (self.last_now is not None and now_ms < self.last_now):
            return self.stop('INVALID_CLOCK')
        self.last_now = now_ms
        if self.source is not None and now_ms-self.source[1] >= MAX_AGE_MS:
            return self.stop('SOURCE_EXPIRED')
        try:
            packet = validate(value, self.boot, now_ms, allow_fixture=allow_fixture)
        except ObservationError as exc:
            if str(exc) == 'SOURCE_UNCONFIRMED' and self.source is not None:
                # No new pixels: keep the last command only inside its ORIGINAL
                # source deadline. No proposal, no lease renewal, no extrapolation.
                self.reason = 'WAITING_FOR_CONFIRMED_FRAME'
                return self.status()
            if self.context is None and str(exc) in ('SOURCE_NO_TARGET', 'SOURCE_EXPIRED', 'SOURCE_MULTIPLE_FACES', 'SOURCE_UNCONFIRMED'):
                self.reason = str(exc)
                return self.status()
            return self.stop(str(exc))
        if packet.get('target_kind') != 'face':
            return self.stop('FACE_SOURCE_REQUIRED')
        t = packet['target']
        if packet['frame_width']!=640 or packet['frame_height']!=480:
            return self.stop('FACE_GEOMETRY_CHANGED')
        context = (packet['service_epoch'], packet['camera_epoch'], t['track_id'],
                   t['track_generation'], packet['frame_width'], packet['frame_height'])
        if self.context is not None and self.context != context:
            return self.stop('FACE_CONTEXT_CHANGED')
        source = (packet['source_frame_id'], packet['source_mono_ms'])
        payload = (context, tuple(t['box']), t['score'])
        if self.source == source:
            if self.payload != payload:
                return self.stop('SOURCE_MUTATED')
            self.reason = 'NO_NEW_SOURCE'
            return self.status()
        if self.source is not None and (source[0] <= self.source[0] or source[1] <= self.source[1]):
            return self.stop('SOURCE_REORDERED')
        x, y, w, h = t['box']
        width = packet['frame_width']
        if t['score'] < self.config.minimum_score or min(w, h) < self.config.minimum_face_pixels:
            return self.stop('FACE_QUALITY')
        if w/width > self.config.maximum_face_width_ratio:
            return self.stop('FACE_TOO_LARGE')
        center, span = (x+w/2)/width, w/width
        dt = None if self.source is None else (source[1]-self.source[1])/1000.
        if dt is not None and not 0 < dt < MAX_AGE_MS/1000.:
            return self.stop('SOURCE_GAP')
        alpha = 1. if dt is None else 1-math.exp(-dt*1000/self.config.filter_tau_ms)
        previous_median=self.median_center
        self.raw_center=center;self.frame_width=width;self.centers.append(center);self.widths.append(span)
        self.median_center=float(median(self.centers));median_width=float(median(self.widths))
        if dt is not None and previous_median is not None:
            measured_velocity=(self.median_center-previous_median)/dt
            clip=self.config.face_velocity_clip_ratio_s
            measured_velocity=max(-clip,min(clip,measured_velocity))
            beta=1-math.exp(-dt*1000/self.config.velocity_filter_tau_ms)
            self.face_velocity+=beta*(measured_velocity-self.face_velocity)
        self.filtered_center = self.median_center if self.filtered_center is None else self.filtered_center+alpha*(self.median_center-self.filtered_center)
        self.filtered_width = median_width if self.filtered_width is None else self.filtered_width+alpha*(median_width-self.filtered_width)
        self.context, self.source, self.payload = context, source, payload
        self.new_source = True
        self.warmup += 1
        if self.warmup < self.config.confirm_frames:
            self.reason = 'CONFIRMING_FACE'
            return self.status()
        # Stop as soon as the measured face center returns inside. Filtering
        # affects acceleration, never moves the user's boundary or adds drift.
        # The user's left limit is the image edge. A face CENTER cannot reach
        # zero while its box is visible, so that side uses a 2px box-edge touch.
        left_boundary = self.config.left_ratio or 2./width
        left_outside = x/width <= left_boundary
        inside = not left_outside and center <= self.config.right_ratio
        if inside:
            self.edge = self.edge_count = self.edge_candidate = 0
            self.velocity = 0.
            self.requested_speed=self.step_speed=0.
            self.reason = 'SAFE_ZONE_HOLD'
            return self.status()
        candidate = -1 if left_outside else 1
        if self.edge == 0:
            self.edge_count = self.edge_count+1 if candidate and candidate == self.edge_candidate else 1 if candidate else 0
            self.edge_candidate = candidate
            if candidate and self.edge_count >= self.config.edge_confirm_frames:
                self.edge = candidate
        elif candidate != self.edge:
            self.edge = self.edge_count = self.edge_candidate = 0
        desired = 0.
        if self.edge:
            left = self.filtered_center-self.filtered_width/2
            distance = (left_boundary-left if self.edge == -1
                        else self.filtered_center-self.config.right_ratio)
            base=max(self.config.base_speed_us_s,self.config.gain_us_s*max(0.,distance))
            # This is measured IMAGE velocity, including the camera's own
            # corrective motion. Outward motion speeds up the response;
            # returning motion slows it. Never predict a future face position.
            feedback=self.config.velocity_gain_us*self.edge*self.face_velocity
            speed = max(self.config.minimum_speed_us_s,
                        min(self.config.maximum_speed_us_s,base+feedback))
            desired = self.edge*self.polarity*speed
        self.requested_speed=desired
        dt = dt or 0.
        dv = self.config.maximum_acceleration_us_s2*dt
        self.velocity += max(-dv, min(dv, desired-self.velocity))
        delta = max(-self.config.maximum_step_us, min(self.config.maximum_step_us, self.velocity*dt))
        position = max(self.config.minimum_us, min(self.config.maximum_us, self.position+delta))
        if (position == self.config.minimum_us and self.velocity < 0 or
                position == self.config.maximum_us and self.velocity > 0):
            self.velocity = 0.
        self.step_speed=(position-self.position)/dt if dt else 0.
        self.position, self.pulse_us = position, round(position)
        self.proposals += 1
        self.reason = 'AT_LIMIT' if self.edge and self.pulse_us in (self.config.minimum_us, self.config.maximum_us) else 'EDGE_FOLLOW' if self.edge else 'CONFIRMING_EDGE' if candidate else 'SAFE_ZONE_HOLD'
        return self.status()
