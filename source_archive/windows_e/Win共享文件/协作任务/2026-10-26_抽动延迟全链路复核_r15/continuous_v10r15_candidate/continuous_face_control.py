"""Face-only edge following math. This module has no actuator or IO imports."""
from dataclasses import dataclass
from collections import deque
import math
from statistics import median
from one_euro import OneEuroFilter
from common.motion_observation import MAX_AGE_MS, ObservationError, validate


@dataclass(frozen=True)
class EdgeConfig:
    left_ratio: float = 0.
    right_ratio: float = .8064720153808593
    filter_tau_ms: float = 80.
    gain_us_s: float = 160.
    maximum_speed_us_s: float = 10.
    minimum_speed_us_s: float = 0.
    minimum_edge_speed_us_s: float = 2.
    base_speed_us_s: float = 0.
    median_window: int = 3
    velocity_filter_tau_ms: float = 100.
    one_euro_min_cutoff_hz: float = 1.
    one_euro_beta: float = 6.
    one_euro_derivative_cutoff_hz: float = 1.
    one_euro_width_beta: float = 2.
    velocity_gain_us: float = 0.
    face_velocity_clip_ratio_s: float = 1.
    maximum_acceleration_us_s2: float = 100.
    maximum_jerk_us_s3: float = 800.
    maximum_correction_us: int = 3  # None explicitly enables continuous correction
    prearm_confirmed_face: bool = False
    boundary_ramp_ratio: float = .04
    maximum_step_us: float = 4.
    confirm_frames: int = 3
    edge_confirm_frames: int = 1
    minimum_score: float = .9
    minimum_face_pixels: float = 48.
    maximum_face_width_ratio: float = .7
    minimum_us: int = 1400
    maximum_us: int = 1600

    def __post_init__(self):
        for name,low,high in (('one_euro_min_cutoff_hz',.1,30.),('one_euro_beta',0.,30.),
                              ('one_euro_derivative_cutoff_hz',.1,30.),('one_euro_width_beta',0.,30.)):
            value=getattr(self,name)
            if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
                raise ValueError('Invalid effective OneEuro parameter: '+name)
        if type(self.prearm_confirmed_face) is not bool:
            raise ValueError('Prearm selection must be an explicit bool')
        if self.maximum_correction_us is not None and (type(self.maximum_correction_us) is not int or not 1<=self.maximum_correction_us<=200):
            raise ValueError('Correction budget must be None or 1..200us')
        values = (self.left_ratio, self.right_ratio, self.filter_tau_ms, self.gain_us_s,
                  self.maximum_speed_us_s, self.minimum_speed_us_s,self.minimum_edge_speed_us_s,
                  self.base_speed_us_s,self.velocity_filter_tau_ms,self.velocity_gain_us,self.face_velocity_clip_ratio_s,
                  self.maximum_acceleration_us_s2, self.maximum_step_us,
                  self.minimum_score, self.minimum_face_pixels, self.maximum_face_width_ratio)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError('Finite face control parameters required')
        if not (0 <= self.left_ratio < self.right_ratio <= 1 and self.right_ratio-self.left_ratio >= .2
                and 30 <= self.filter_tau_ms <= 500 and 1 <= self.gain_us_s <= 400
                and 0 <= self.minimum_speed_us_s <= self.base_speed_us_s <= self.maximum_speed_us_s <= 60
                and 0<=self.minimum_edge_speed_us_s<=self.maximum_speed_us_s
                and type(self.median_window) is int and self.median_window in (1,3,5)
                and 30<=self.velocity_filter_tau_ms<=300 and 0<=self.velocity_gain_us<=200
                and .1<=self.face_velocity_clip_ratio_s<=2
                and 1 <= self.maximum_acceleration_us_s2 <= 120
                and 0 < self.maximum_step_us <= 4
                and type(self.confirm_frames) is int and 2 <= self.confirm_frames <= 10
                and type(self.edge_confirm_frames) is int and 1 <= self.edge_confirm_frames <= 5
                and 0 < self.maximum_jerk_us_s3 <= 800 and .01 <= self.boundary_ramp_ratio <= .1
                and .9 <= self.minimum_score <= 1 and self.minimum_face_pixels >= 24
                and .2 <= self.maximum_face_width_ratio <= .7
                and type(self.minimum_us) is int and type(self.maximum_us) is int
                and 1400 <= self.minimum_us < self.maximum_us <= 1600):
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
        self.authority_deadline_ms=None;self.anchor_stamp=None
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
        c=self.config
        self.center_filter=OneEuroFilter(c.one_euro_min_cutoff_hz,c.one_euro_beta,c.one_euro_derivative_cutoff_hz)
        self.width_filter=OneEuroFilter(c.one_euro_min_cutoff_hz,c.one_euro_width_beta,c.one_euro_derivative_cutoff_hz)
        self.jump_pending=None;self.jump_rejections=0
        self.pending_safe_zone=False

    def status(self):
        return {'state': 'DISARMED' if self.stopped else 'EDGE_FOLLOW' if self.edge else
                'DECELERATING' if abs(self.velocity) > .001 else 'HOLD',
                'reason': self.reason, 'pulse_us': self.pulse_us,
                'velocity_us_s': self.velocity, 'edge': self.edge,
                'filtered_center_ratio': self.filtered_center,
                'filtered_width_ratio': self.filtered_width,
                'raw_center_ratio':self.raw_center,'median_center_ratio':self.median_center,
                'median_window':self.config.median_window,'face_image_velocity_ratio_s':self.face_velocity,
                'median_used_for_control':False,'legacy_filter_tau_parameters_active':False,
                'effective_filter':dict(min_cutoff_hz=self.center_filter.min_cutoff_hz,
                    beta=self.center_filter.beta,derivative_cutoff_hz=self.center_filter.derivative_cutoff_hz,
                    width_beta=self.width_filter.beta,current_cutoff_hz=self.center_filter.cutoff_hz),
                'face_image_velocity_px_s':self.face_velocity*self.frame_width,
                'requested_velocity_us_s':self.requested_speed,'step_velocity_us_s':self.step_speed,
                'source_mono_ms': self.source[1] if self.source else None,
                'authority_deadline_mono_ms':self.authority_deadline_ms,
                'new_source': self.new_source, 'confirmed_sources': self.warmup,
                'proposals': self.proposals, 'limits_us': [self.config.minimum_us, self.config.maximum_us]}

    def inherit_perception(self, previous):
        """Carry face history across ARM, never a source/command/actuator state."""
        if (previous.stopped or previous.boot!=self.boot or previous.config!=self.config
                or previous.context is None or previous.source is None or previous.warmup<self.config.confirm_frames):
            raise ValueError('Confirmed live face perception required')
        self.context=previous.context;self.warmup=previous.warmup
        self.raw_center=previous.raw_center;self.median_center=previous.median_center
        self.filtered_center=previous.filtered_center;self.filtered_width=previous.filtered_width
        self.face_velocity=previous.face_velocity;self.frame_width=previous.frame_width
        self.centers.extend(previous.centers);self.widths.extend(previous.widths)
        self.center_filter=previous.center_filter;self.width_filter=previous.width_filter
        self.edge_candidate=previous.edge;self.edge_count=self.config.edge_confirm_frames-1
        self.reason='AWAITING_POST_ARM_FRAME'
        # self.source/payload remain None; velocity stays zero and position is
        # the current hardware reference. The session rejects pre-ARM frames.
        return self

    def stop(self, reason):
        self.stopped, self.reason, self.velocity, self.edge = True, reason, 0., 0
        self.requested_speed=self.step_speed=0.
        return self.status()

    def freeze_at(self, pulse):
        if type(pulse) is not int or not self.config.minimum_us<=pulse<=self.config.maximum_us:
            raise ValueError('Bounded current pulse required')
        self.position=float(pulse);self.pulse_us=pulse
        self.velocity=self.requested_speed=self.step_speed=0.
        self.edge=self.edge_count=self.edge_candidate=0

    def observe(self, value, now_ms, *, allow_fixture=False):
        self.new_source = False
        self.pending_safe_zone=False
        if self.stopped:
            return self.status()
        if type(now_ms) is not int or (self.last_now is not None and now_ms < self.last_now):
            return self.stop('INVALID_CLOCK')
        self.last_now = now_ms
        try:
            packet = validate(value, self.boot, now_ms, allow_fixture=allow_fixture)
        except ObservationError as exc:
            if self.authority_deadline_ms is not None and now_ms>=self.authority_deadline_ms:
                return self.stop('SOURCE_EXPIRED')
            if (str(exc)=='SOURCE_UNCONFIRMED' and self.context is not None
                    and isinstance(value,dict)
                    and ((value.get('service_epoch'),value.get('camera_epoch'))!=self.context[:2]
                         or (value.get('frame_width'),value.get('frame_height'))!=self.context[4:]
                         or value.get('mirror_horizontal') is not True)):
                return self.stop('FACE_CONTEXT_CHANGED')
            if (str(exc)=='SOURCE_EXPIRED' and self.context is not None and isinstance(value,dict)
                    and value.get('state')=='EXPIRED' and value.get('target') is None
                    and value.get('source_frame_id') is None and value.get('source_mono_ms') is None
                    and value.get('deadline_mono_ms') is None
                    and value.get('target_kind')=='face' and value.get('mirror_horizontal') is True
                    and (value.get('service_epoch'),value.get('camera_epoch'))==self.context[:2]
                    and all(type(value.get(k)) is int for k in ('frame_width','frame_height'))
                    and (value.get('frame_width'),value.get('frame_height'))==self.context[4:]
                    and isinstance(value.get('face_tracking'),dict)
                    and type(value['face_tracking'].get('version')) is int
                    and value['face_tracking'].get('version')==11
                    and value['face_tracking'].get('error')==''
                    and value['face_tracking'].get('reason') in
                        ('FACE_TEMPLATE_VISIBLE_CLIP','FACE_TEMPLATE_PARTIAL_FIXED_ANCHOR','FACE_FIXED_ANCHOR_LK_AFFINE')):
                # This canonical v11 packet grants NO observation or command
                # budget. If a previously admitted image exists, the original
                # source-expiry check above already wins. With no post-ARM
                # image the session cannot output at all and its existing
                # 250ms confirmation timeout still applies.
                self.reason='WAITING_FOR_POST_ARM_FACE' if self.source is None else 'WAITING_WITH_ORIGINAL_FACE_DEADLINE'
                return self.status()
            if str(exc)=='SOURCE_UNCONFIRMED' and self.source is None:
                self.reason='WAITING_FOR_POST_ARM_FACE'
                return self.status()
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
        anchor=packet.get('face_detection_mono_ms')
        if anchor is not None:
            if type(anchor) is not int or anchor<0 or anchor>source[1]:
                return self.stop('INVALID_FACE_ANCHOR')
            # READY was evaluated by the camera before transport/queue delay.
            # A genuinely old anchor is a normal visual timeout, not malformed
            # provenance. Stop and require fresh confirmation; never extend it.
            if now_ms-anchor>=500:return self.stop('SOURCE_EXPIRED')
        elif packet.get('source_kind')=='actual':return self.stop('INVALID_FACE_ANCHOR')
        deadline=min(source[1]+MAX_AGE_MS,anchor+500) if anchor is not None else source[1]+MAX_AGE_MS
        payload = (context, tuple(t['box']), t['score'],anchor)
        if self.source == source:
            if self.authority_deadline_ms is not None and now_ms>=self.authority_deadline_ms:
                return self.stop('SOURCE_EXPIRED')
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
        gate_dt=dt if dt is not None else (source[1]/1000.-self.center_filter.timestamp_s if self.center_filter.timestamp_s is not None else None)
        if gate_dt is not None and self.raw_center is not None:
            delta=center-self.raw_center
            if abs(delta)>.08 and abs(delta)/gate_dt>1.5:
                pending=self.jump_pending
                confirmed=(pending is not None and source[1]>pending[1]
                    and (abs(center-pending[0])<.05 or delta*(center-pending[0])>0))
                if not confirmed:
                    self.jump_pending=(center,source[1]);self.jump_rejections+=1
                    self.requested_speed=0.;self.reason='MEASUREMENT_JUMP_PENDING'
                    self.pending_safe_zone=(x/width>(self.config.left_ratio or 2./width)
                                            and center<=self.config.right_ratio)
                    return self.status()
        self.jump_pending=None
        self.raw_center=center;self.frame_width=width;self.centers.append(center);self.widths.append(span)
        self.median_center=float(median(self.centers));median_width=float(median(self.widths))
        self.filtered_center=self.center_filter.filter(center,source[1]/1000.)
        self.filtered_width=self.width_filter.filter(span,source[1]/1000.)
        clip=self.config.face_velocity_clip_ratio_s
        self.face_velocity=max(-clip,min(clip,self.center_filter.derivative_ratio_s))
        self.context, self.source, self.payload = context, source, payload
        self.authority_deadline_ms=deadline;self.anchor_stamp=anchor
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
            distance=max(0.,distance)
            u=min(1.,distance/self.config.boundary_ramp_ratio)
            envelope=u*u*(3.-2.*u)
            # This is measured IMAGE velocity, including the camera's own
            # corrective motion. Outward motion speeds up the response;
            # returning motion slows it. Never predict a future face position.
            feedback=self.config.velocity_gain_us*self.edge*self.face_velocity*envelope
            # Clipped left boxes have x==0: pure proportional distance would
            # remain below 0.5us/s and delay the first integer-us correction
            # for over a second. A confirmed edge gets a small 2us/s floor,
            # still subject to Ruckig startup and the 3us episode budget.
            speed=max(self.config.minimum_edge_speed_us_s,min(self.config.maximum_speed_us_s,self.config.gain_us_s*distance+feedback))
            returning=-self.edge*self.face_velocity
            if returning>.02:
                time_to_boundary=distance/returning
                speed=min(speed,.5*self.config.maximum_acceleration_us_s2*time_to_boundary)
            desired = self.edge*self.polarity*speed
        self.requested_speed=desired
        # This layer admits actual images and requests a velocity. The session
        # samples a finite source-bound Ruckig trajectory on its own 20ms clock.
        self.proposals += 1
        self.reason = 'EDGE_BRAKING' if self.edge and returning>.02 else 'EDGE_FOLLOW' if self.edge else 'CONFIRMING_EDGE'
        return self.status()
