"""20ms trajectory ticks share an image's original finite authority, never its age."""
from collections import deque
import math,time
from continuous_face_control import FaceEdgeController
from common.motion_observation import validate,ObservationError

VISUAL_REASONS={'SOURCE_NO_TARGET','SOURCE_UNCONFIRMED','SOURCE_EXPIRED','SOURCE_MULTIPLE_FACES',
 'FACE_CONTEXT_CHANGED','SOURCE_GAP','SOURCE_FACE_ERROR','SOURCE_FACE_UNAVAILABLE',
 'SOURCE_INCONSISTENT_FACE_SOURCE','FACE_QUALITY','FACE_TOO_LARGE'}


class ContinuousSession:
    def __init__(self,device,boot,config,reference_factory,*,trajectory,clock=time.monotonic,allow_fixture=False):
        self.device,self.boot,self.config,self.factory=device,boot,config,reference_factory
        self.trajectory,self.clock,self.allow_fixture=trajectory,clock,allow_fixture
        self.started=self.last_tick=clock();self.active=self.fatal=False
        self.current=device.status();self.require_stopped(self.current)
        self.controller=self.fresh();self.pva=[float(self.current['width_us']),0.,0.]
        self.minimum=self.maximum=self.current['width_us'];self.segments=self.acks=0
        self.hold_renewals=self.motion_updates=self.trajectory_ticks=0
        self.events=deque(maxlen=48);self.command_trace=deque(maxlen=128)
        self.state,self.reason='MONITORING','WAITING_FOR_FACE'
        self.zone_holding=False;self.segment_start=None;self.authority=None;self.source_origin=None
        self.last_commit_source=None;self.lockout_side=0
        self.limit_side=0
        self.correction_origin=None;self.correction_side=0

    def fresh(self):return FaceEdgeController(self.boot,self.current['width_us'],config=self.config)
    def require_stopped(self,value):
        if value['flags'] or value['lease_left_ms'] or value['reason'] or not self.config.minimum_us<=value['width_us']<=self.config.maximum_us:
            raise RuntimeError('Stopped current command in finite range required')
    def note(self,reason,**fields):
        self.reason=reason;self.events.append(dict(reason=reason,mono_ms=round(self.clock()*1000),**fields))
    def status(self):
        control=self.controller.status()
        control.update(velocity_us_s=self.pva[1],acceleration_us_s2=self.pva[2],pulse_us=round(self.pva[0]),
                       position_filter='one_euro',outlier_gate='large_jump_requires_next_actual_image',
                       filter_cutoff_hz=self.controller.center_filter.cutoff_hz,jump_rejections=self.controller.jump_rejections)
        return dict(state=self.state,reason=self.reason,active=self.active,fatal=self.fatal,pulse_us=self.current['width_us'],
         target_us=self.current['target_us'],commands_accepted=self.acks,hold_renewals=self.hold_renewals,
         motion_target_changes=self.motion_updates,segments=self.segments,trajectory_ticks=self.trajectory_ticks,
         range_us=[self.minimum,self.maximum],authorized_range_us=[self.config.minimum_us,self.config.maximum_us],
         elapsed_s=round(self.clock()-self.started,3),heartbeat_mono_ms=round(self.clock()*1000),control=control,
         readback=self.current,events=list(self.events),command_trace=list(self.command_trace),
         correction_limit_us=self.config.maximum_correction_us,
         authority_deadline_mono_ms=self.authority[1]+250 if self.authority else None)
    def stop_segment(self,reason,*,normal=False):
        self.current=self.device.finish() if normal else self.device.stop();self.require_stopped(self.current)
        self.active=False;self.controller=self.fresh();self.pva=[float(self.current['width_us']),0.,0.]
        self.authority=self.source_origin=self.last_commit_source=None
        self.zone_holding=False;self.segment_start=None;self.state='MONITORING';self.note(reason)
    def fail(self,reason,evidence=None):
        self.stop_segment(reason);self.fatal=True;self.state='FAULT'
        if evidence is not None:self.events[-1]['rejected_readback']=evidence
        return self.status()
    def disconnected(self):
        if self.active:self.stop_segment('VISION_STREAM_INTERRUPTED')
        else:self.controller=self.fresh();self.state='WAITING_FOR_FACE';self.reason='VISION_STREAM_INTERRUPTED'
    def read_active(self):
        self.current=self.device.status();r=self.current
        same=(r['session']==self.device.session and r['epoch']==self.device.epoch
              and r['ack_seq']==self.device.ack_seq)
        if (r['reason']==0 and r['flags']&14==14 and same
                and r['target_us']==self.device.accepted_target_us):return True
        evidence=dict(r)
        if (r['flags']==64 and r['lease_left_ms']==0 and same
                and 0<self.device.ack_seq<0xffffffff and r['target_us']==self.device.accepted_target_us):
            self.stop_segment('SOURCE_LEASE_EXPIRED');self.events[-1]['rejected_readback']=evidence
        else:self.fail('HARDWARE_PERMISSION_LOST',evidence)
        return False

    def step(self,packet):
        if self.fatal:return self.status()
        now=self.clock();stamp=packet.get('source_mono_ms') if isinstance(packet,dict) else None
        if isinstance(packet,dict) and packet.get('target_kind')!='face':return self.fail('FACE_SOURCE_REQUIRED')
        if self.active and type(stamp) is int and stamp/1000.<=self.device.reference_time:
            # Old capture packets never grant output, but still have to pass
            # source/context checks: a NO_TARGET or wrong boot cannot bypass
            # STOP just by carrying a pre-ARM timestamp.
            try:checked=validate(packet,self.boot,int(now*1000),allow_fixture=self.allow_fixture)
            except ObservationError as error:
                reason=str(error)
                if reason in VISUAL_REASONS:self.stop_segment(reason);return self.status()
                return self.fail(reason)
            target=checked['target']
            context=(checked['service_epoch'],checked['camera_epoch'],target['track_id'],
                target['track_generation'],checked['frame_width'],checked['frame_height'])
            if context!=self.controller.context:self.stop_segment('FACE_CONTEXT_CHANGED')
            return self.status()
        value=self.controller.observe(packet,int(now*1000),allow_fixture=self.allow_fixture)
        if self.controller.stopped:
            reason=self.controller.reason
            if reason not in VISUAL_REASONS:return self.fail(reason)
            if self.active:self.stop_segment(reason)
            else:self.controller=self.fresh();self.reason=reason;self.state='WAITING_FOR_FACE'
            return self.status()
        if not value['new_source']:
            if self.active and self.controller.pending_safe_zone and self.read_active():
                # An uncertain jump may stop motion, never grant new motion
                # or refresh the old image's deadline.
                self.zone_holding=True;self.segment_start=None
                self.pva=[float(self.current['width_us']),0.,0.]
                self.state='HOLDING';self.reason='SAFE_ZONE_HOLD_PENDING_CONFIRMATION'
            return self.status()
        if not self.active:
            self.reason=value['reason']
            if value['confirmed_sources']<self.config.confirm_frames:return self.status()
            if value['reason']=='SAFE_ZONE_HOLD':
                self.correction_origin=None;self.correction_side=0
                self.state='MONITORING';self.reason='SAFE_ZONE_HOLD'
                return self.status()
            if not value['edge']:return self.status()
            if (self.correction_origin is not None and self.correction_side==value['edge']
                    and abs(self.current['width_us']-self.correction_origin)>=self.config.maximum_correction_us):
                self.state='HOLD_AT_LIMIT';self.reason='CORRECTION_STEP_COMPLETE'
                return self.status()
            # Initial in-zone faces do not repeatedly energize the servo.
            # Engage only once a confirmed face actually requests correction.
            self.current=self.device.status();self.require_stopped(self.current)
            reference=self.factory(self.current['width_us'])
            self.device.confirm_and_arm(reference,int(now*1e6)%0xffffffff or 1,self.current['epoch']+1,authorized=True)
            self.current=self.device.status();self.active=True;self.segments+=1
            self.controller=self.fresh().inherit_perception(self.controller)
            self.last_tick=self.clock();self.pva=[float(self.current['width_us']),0.,0.]
            self.authority=None;self.state='CONFIRMING';self.note('FACE_CONFIRMED_ARM_CURRENT_POSITION')
            if self.correction_origin is None or self.correction_side!=value['edge']:
                self.correction_origin=reference.reference_us;self.correction_side=value['edge']
            return self.status()
        if not self.read_active():return self.status()
        self.authority=self.controller.source;self.source_origin=self.current['target_us']
        if value['reason']=='SAFE_ZONE_HOLD':
            self.correction_origin=None;self.correction_side=0
            self.zone_holding=True;self.segment_start=None
            self.pva=[float(self.current['width_us']),0.,0.]
            self.controller.freeze_at(self.current['width_us'])
            self.state='HOLDING';self.reason='SAFE_ZONE_HOLD'
        else:
            self.zone_holding=False
            if value['edge'] and (self.correction_origin is None or self.correction_side!=value['edge']):
                self.correction_origin=self.current['width_us'];self.correction_side=value['edge']
            if value['edge'] and self.limit_side and value['edge']!=self.limit_side:self.limit_side=0
            if value['edge'] and self.segment_start is None:self.segment_start=now
            self.state='BRAKING' if value['reason']=='EDGE_BRAKING' else 'FOLLOWING'
            self.reason=value['reason']
        return self.status()

    def tick(self):
        now=self.clock();dt=now-self.last_tick
        if dt<.005 or self.fatal:return self.status()
        self.last_tick=now
        if not self.active:return self.status()
        if dt>.1:self.stop_segment('CONTROL_TICK_LATE');return self.status()
        if self.authority is None:
            if now-self.device.reference_time>=.25:self.stop_segment('POST_ARM_SOURCE_TIMEOUT')
            return self.status()
        fid,stamp=self.authority;age=now-stamp/1000.
        if age<0:return self.fail('INVALID_CLOCK')
        if age>=.227:self.stop_segment('SOURCE_HORIZON_ENDED');return self.status()
        if not self.read_active():return self.status()
        if self.segment_start is not None and now-self.segment_start>=10:
            self.stop_segment('MOTION_SEGMENT_TIME_LIMIT',normal=True);return self.status()
        if not self.zone_holding:
            desired=self.controller.requested_speed
            speed,acceleration=abs(self.pva[1]),abs(self.pva[2])
            brake_time=speed/self.config.maximum_acceleration_us_s2+self.config.maximum_acceleration_us_s2/self.config.maximum_jerk_us_s3+acceleration/self.config.maximum_jerk_us_s3
            brake_distance=speed*brake_time+.5*acceleration*brake_time*brake_time+1.
            to_limit=(self.config.maximum_us-self.pva[0] if desired>0 else self.pva[0]-self.config.minimum_us)
            if desired and self.limit_side and desired*self.limit_side>0:
                desired=0.;self.state='HOLD_AT_LIMIT';self.reason='SOFT_LIMIT_HOLD'
            elif desired and to_limit<=brake_distance:
                self.limit_side=1 if desired>0 else -1
                desired=0.;self.state='BRAKING';self.reason='SOFT_LIMIT_BRAKING'
            self.pva=self.trajectory.step(self.pva,desired,dt,self.config);self.trajectory_ticks+=1
            # Each actual image grants at most the existing 4us displacement.
            # Control ticks are not new images and cannot grow that budget.
            low=max(self.config.minimum_us,self.source_origin-self.config.maximum_step_us)
            high=min(self.config.maximum_us,self.source_origin+self.config.maximum_step_us)
            if self.correction_origin is not None:
                low=max(low,self.correction_origin-self.config.maximum_correction_us)
                high=min(high,self.correction_origin+self.config.maximum_correction_us)
            if not low<=self.pva[0]<=high:
                self.pva=[max(low,min(high,self.pva[0])),0.,0.]
                self.state='HOLDING';self.reason='CORRECTION_STEP_COMPLETE' if self.correction_origin is not None and abs(self.pva[0]-self.correction_origin)>=self.config.maximum_correction_us else 'SOURCE_DISPLACEMENT_BUDGET'
        target=round(self.pva[0]);old_target=self.current['target_us']
        if target==old_target and self.last_commit_source==self.authority:return self.status()
        if not self.config.minimum_us<=target<=self.config.maximum_us:return self.fail('TRAJECTORY_RANGE')
        if abs(target-old_target)>self.config.maximum_step_us:return self.fail('TRAJECTORY_STEP')
        ack=self.device.submit(target,stamp/1000.,freshness_s=.25,margin_s=.02)
        if ack['outcome']!='ACCEPTED':
            if ack['reason'] in ('STALE_SOURCE','SUBMISSION_TOO_LATE','SOURCE_LEASE_EXPIRED'):
                self.stop_segment('SOURCE_SUBMISSION_EXPIRED');return self.status()
            return self.fail('COMMAND_'+ack['reason'],ack.get('rejected_readback',ack.get('readback')))
        self.acks+=1;self.last_commit_source=self.authority;self.current=ack.get('readback') or self.device.status()
        if target==old_target:self.hold_renewals+=1
        else:self.motion_updates+=1
        self.minimum=min(self.minimum,self.current['width_us']);self.maximum=max(self.maximum,self.current['width_us'])
        self.command_trace.append(dict(mono_ms=round(now*1000),source_frame_id=fid,source_mono_ms=stamp,
            deadline_mono_ms=stamp+250,source_age_ms=round(age*1000),target_us=target,delta_us=target-old_target,
            velocity_us_s=round(self.pva[1],4),acceleration_us_s2=round(self.pva[2],4),lease_ms=ack.get('lease_ms'),state=self.state))
        return self.status()

    def close(self):
        if self.active:self.stop_segment('OPERATOR_STOP',normal=not bool(self.device.status()['reason']))
        else:self.current=self.device.stop()
        self.state='STOPPED';self.reason='OPERATOR_STOP';return self.status()
