"""Latched visual-center episode driven by the existing PL frame slew.

The target register is an endpoint, not the emitted pulse width. Existing
VSRV/2 RTL advances width by at most 4us at each 20ms boundary. New actual
face images alone renew the lease, under their original 250/500ms deadlines.
This mode intentionally replaces the old 4us-per-image PS trajectory budget
with the existing hardware frame-rate bound; it does not widen travel limits.
"""
from collections import deque
from continuous_session import ContinuousSession


class HardwareSlewSession(ContinuousSession):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if not self.config.hardware_slew_recenter:
            raise ValueError('Explicit hardware-slew profile required')
        self.latched_endpoint=None;self.last_ramp_source=None
        self.visual_center_completions=0;self.hardware_ramp_commits=0
        self.hardware_width_trace=deque(maxlen=16)

    def status(self):
        value=super().status();control=value['control']
        side=self.controller.edge*self.polarity
        control.update(position_filter='OneEuro for face admission; not a pulse-position trajectory',
            trajectory='FPGA_FRAME_SLEW',nominal_pwm_slew_us_s=200 if side else 0,
            requested_velocity_us_s=side*200 if self.active else 0,
            velocity_us_s=None,acceleration_us_s2=None)
        value.update(motion_mode='LATCHED_VISUAL_CENTER_HARDWARE_SLEW',
            latched_endpoint_us=getattr(self,'latched_endpoint',None),
            visual_center_completions=getattr(self,'visual_center_completions',0),
            hardware_ramp_commits=getattr(self,'hardware_ramp_commits',0),
            emitted_pulse_step_us=4,pwm_frame_ms=20,
            hardware_width_trace=list(getattr(self,'hardware_width_trace',())),
            width_trace_scope='register readbacks, not an external pin waveform or shaft measurement',
            source_displacement_bound='hardware 4us/frame inside original image/anchor lease; not the old 4us/image budget',
            mechanical_velocity_measured=False)
        return value

    def read_active(self):
        active=super().read_active()
        if active:
            self.hardware_width_trace.append(dict(mono_ms=round(self.clock()*1000),
                width_us=self.current['width_us'],target_us=self.current['target_us'],
                lease_left_ms=self.current['lease_left_ms']))
        return active

    def stop_segment(self,reason,*,normal=False):
        super().stop_segment(reason,normal=normal)
        self.latched_endpoint=self.last_ramp_source=None

    def finish_visual_center(self):
        previous=self.controller
        self.stop_segment('VISUAL_CENTER_COMPLETE',normal=True)
        # Keep perception of a completed goal, never the old source authority,
        # ARM, lease or actuator velocity. A new episode still needs a new ARM
        # and a genuinely captured post-ARM frame before output.
        self.controller=previous;self.controller.freeze_at(self.current['width_us'])
        self.controller.recenter_active=False;self.controller.recenter_completed=True
        self.controller.recenter_phase='COMPLETE'
        self.visual_center_completions+=1
        self.state='HOLDING';self.reason='SAFE_ZONE_HOLD'

    def submit_target(self,target,kind):
        c=self.controller
        if (self.active and self.epoch_output_started and
                (self.zone_holding or not c.recenter_active and c.reason=='SAFE_ZONE_HOLD')):
            self.finish_visual_center();return False
        if (not self.active or self.authority is None or self.authority!=c.source
                or not c.new_source or not c.edge):
            return False
        if self.last_ramp_source==self.authority:return False
        side=c.edge*self.polarity
        endpoint=self.config.maximum_us if side>0 else self.config.minimum_us
        if self.epoch_output_started and self.latched_endpoint!=endpoint:
            self.stop_segment('HARDWARE_RAMP_DIRECTION_CHANGED',normal=True)
            return False
        if not self.epoch_output_started and self.current['width_us']==endpoint:
            self.state='HOLD_AT_LIMIT';self.reason='SOFT_LIMIT_HOLD'
            return False
        # No initial unchanged-width energizing pulse, no predicted face,
        # no timer-based old-image renewal. The pinned driver retains all
        # build, owner, sequence, source-time and minimum-first-lease checks.
        self.latched_endpoint=endpoint
        accepted=super().submit_target(endpoint,'NEW_FACE_HARDWARE_SLEW_ENDPOINT')
        if accepted:
            self.last_ramp_source=self.authority;self.hardware_ramp_commits+=1
        return accepted

    def step(self,packet):
        super().step(packet)
        if not self.active or self.fatal:return self.status()
        c=self.controller
        if self.brief_face_gap:
            # This mode has no PS braking trajectory during missing pixels.
            self.stop_segment('SOURCE_UNCONFIRMED',normal=True)
        elif self.epoch_output_started and c.pending_safe_zone:
            self.stop_segment('MEASUREMENT_JUMP_PENDING',normal=True)
        elif self.epoch_output_started and not c.recenter_active and c.reason=='SAFE_ZONE_HOLD':
            self.finish_visual_center()
        elif c.new_source and self.authority==c.source and c.edge:
            self.submit_target(self.current['target_us'],'NEW_FACE_HARDWARE_SLEW_ENDPOINT')
        return self.status()

    def tick(self):
        now=self.clock();dt=now-self.last_tick
        if dt<.005 or self.fatal:return self.status()
        self.last_tick=now
        if not self.active:return self.status()
        if dt>.1:self.stop_segment('CONTROL_TICK_LATE',normal=True);return self.status()
        if self.authority is None:
            if now-self.device.reference_time>=.25:self.stop_segment('POST_ARM_SOURCE_TIMEOUT',normal=True)
            return self.status()
        deadline=self.controller.authority_deadline_ms
        if deadline is None:return self.fail('MISSING_AUTHORITY_DEADLINE')
        if now>=deadline/1000.-.023:
            self.stop_segment('SOURCE_HORIZON_ENDED',normal=True);return self.status()
        if not self.read_active():return self.status()
        if self.segment_start is not None and now-self.segment_start>=10:
            self.stop_segment('MOTION_SEGMENT_TIME_LIMIT',normal=True);return self.status()
        if not self.epoch_output_started:return self.status()
        if self.current['width_us']==self.latched_endpoint:
            self.state='HOLD_AT_LIMIT';self.reason='SOFT_LIMIT_HOLD'
        else:
            self.state='FOLLOWING';self.reason='HARDWARE_CONTINUOUS_SLEW'
        # Hardware advances emitted PWM independently. No COMMIT is issued
        # by this tick, even if a new software target could be calculated.
        return self.status()
