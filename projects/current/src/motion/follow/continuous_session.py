"""20ms trajectory ticks share an image's original finite authority, never its age."""
from collections import deque
import math,time
from continuous_face_control import FaceEdgeController
from common.motion_observation import validate,ObservationError
from boundary_rearm import BoundaryRearm
from pwm_budget import (INITIAL_PWM_MINIMUM_LEASE_MS, SUBMISSION_MARGIN_MS,
                        COMMIT_PREFLIGHT_RESERVE_MS)

VISUAL_REASONS={'SOURCE_NO_TARGET','SOURCE_UNCONFIRMED','SOURCE_EXPIRED','SOURCE_MULTIPLE_FACES',
 'FACE_CONTEXT_CHANGED','SOURCE_GAP','SOURCE_FACE_ERROR','SOURCE_FACE_UNAVAILABLE',
 'SOURCE_INCONSISTENT_FACE_SOURCE','FACE_QUALITY','FACE_TOO_LARGE'}
RECENTER_INTENT_HOLD_MS=2000
RECENTER_RESUMABLE_REASONS={'SOURCE_NO_TARGET','SOURCE_UNCONFIRMED','SOURCE_EXPIRED','SOURCE_GAP',
 'SOURCE_HORIZON_ENDED','SOURCE_LEASE_EXPIRED','SOURCE_SUBMISSION_EXPIRED',
 'VISION_STREAM_INTERRUPTED','POST_ARM_SOURCE_TIMEOUT','CONTROL_TICK_LATE','MOTION_SEGMENT_TIME_LIMIT'}
BRIEF_FACE_GAP_REASONS={'UNCONFIRMED_DETECTION','FACE_MEASUREMENT_REJECTED'}
FRESH_SOURCE_RENEWAL_RESERVE_MS=100


class ContinuousSession:
    def __init__(self,device,boot,config,reference_factory,*,trajectory,clock=time.monotonic,allow_fixture=False,polarity=1):
        if type(polarity) is not int or polarity not in (-1,1):
            raise ValueError('Observed polarity must be -1 or 1')
        self.polarity=polarity
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
        self.epoch_output_started=False;self.full_pulse_visual_stops=0
        self.rearm=BoundaryRearm();self.correction_releases=0
        self.fresh_image_lease_renewals=0
        self.initial_pwm_budget_waits=0
        self.recenter_intent=None
        self.rearm_stability_gate=None
        self.rearm_stability_waits=self.rearm_stability_passes=0
        self.brief_face_gap=False;self.brief_face_gaps=0;self.brief_face_recoveries=0
        self.center_settling=False;self.center_settles=0
        self.lease_expiry_lower_bound=None;self.proactive_source_renewals=0

    def fresh(self):return FaceEdgeController(self.boot,self.current['width_us'],config=self.config,polarity=self.polarity)
    def require_stopped(self,value):
        if value['flags'] or value['lease_left_ms'] or value['reason'] or not self.config.minimum_us<=value['width_us']<=self.config.maximum_us:
            raise RuntimeError('Stopped current command in finite range required')
    def note(self,reason,**fields):
        self.reason=reason;self.events.append(dict(reason=reason,mono_ms=round(self.clock()*1000),**fields))
    def retain_recenter_intent(self,reason):
        intent=self.recenter_intent
        if (not self.config.recenter_on_edge or reason not in RECENTER_RESUMABLE_REASONS
                or intent is None or round(self.clock()*1000)>=intent['expires_ms']):
            self.recenter_intent=None
    def cache_recenter_intent(self):
        c=self.controller
        if not self.config.recenter_on_edge:return
        if not c.recenter_active:
            self.recenter_intent=None;return
        # Semantic goal only. No filter, velocity, reference, source authority
        # or hardware lease is carried through a stopped interval.
        self.recenter_intent=dict(context=c.context,source=c.source,
                                  expires_ms=c.source[1]+RECENTER_INTENT_HOLD_MS,
                                  original_side=c.recenter_direction,phase=c.recenter_phase,
                                  trigger_side=c.recenter_trigger_side,target_center_ratio=c.recenter_target_center_ratio)
    def restore_recenter_intent(self,packet,now_ms):
        intent=self.recenter_intent
        if not self.config.recenter_on_edge or self.active or intent is None:return True
        if now_ms>=intent['expires_ms']:
            self.recenter_intent=None;self.controller.recenter_active=False;self.controller.reset_recenter_target();return True
        if (not isinstance(packet,dict) or packet.get('board_boot_id')!=self.boot
                or (packet.get('service_epoch'),packet.get('camera_epoch'))!=intent['context'][:2]
                or packet.get('state')=='MULTIPLE_FACES'):
            self.recenter_intent=None;self.controller.recenter_active=False;self.controller.reset_recenter_target();return True
        try:value=validate(packet,self.boot,now_ms,allow_fixture=self.allow_fixture)
        except ObservationError:return True
        target=value['target'];context=(value['service_epoch'],value['camera_epoch'],target['track_id'],
            target['track_generation'],value['frame_width'],value['frame_height'])
        if context!=intent['context']:
            self.recenter_intent=None;self.controller.recenter_active=False;self.controller.reset_recenter_target();return True
        source=(value['source_frame_id'],value['source_mono_ms'])
        if source[0]<=intent['source'][0] or source[1]<=intent['source'][1]:return False
        # observe() must still validate anchor/quality and reconfirm actual
        # frames; the post-ARM frame rule remains unchanged.
        self.controller.recenter_active=True;self.controller.recenter_completed=False
        self.controller.recenter_trigger_side=intent.get('trigger_side',0)
        self.controller.recenter_target_center_ratio=intent.get('target_center_ratio',self.config.target_center_ratio)
        if self.config.single_pass_recenter:
            self.controller.recenter_direction=intent.get('original_side',0)
            self.controller.recenter_phase=intent.get('phase','CRUISE')
        return True
    def reset_rearm_stability_progress(self):
        gate=self.rearm_stability_gate
        if gate is not None:
            gate.update(context=None,last_source=None,first_source_ms=None,first_received_ms=None,
                        distinct_sources=0,new_detection_seen=False,stable_source_ms=0,stable_wall_ms=0)

    def rearm_stability_ready(self,now_ms):
        gate=self.rearm_stability_gate
        if gate is None:return True
        c=self.controller
        # Only observe()'s newly admitted actual images count. This gate has
        # no source authority, hardware reference, lease or actuator state.
        if c.source is None or not c.new_source:return False
        if gate['context']!=c.context:
            self.reset_rearm_stability_progress();gate['context']=c.context
        source=c.source
        if gate['last_source'] is not None and (source[0]<=gate['last_source'][0] or source[1]<=gate['last_source'][1]):
            return False
        if gate['first_source_ms'] is None:
            gate['first_source_ms']=source[1];gate['first_received_ms']=now_ms
        gate['last_source']=source;gate['distinct_sources']+=1
        gate['stable_source_ms']=source[1]-gate['first_source_ms']
        gate['stable_wall_ms']=now_ms-gate['first_received_ms']
        gate['new_detection_seen']=(gate['new_detection_seen'] or
            type(c.anchor_stamp) is int and c.anchor_stamp>gate['interrupted_anchor_ms'])
        if (gate['distinct_sources']>=3 and gate['stable_source_ms']>=self.config.rearm_stability_ms
                and gate['stable_wall_ms']>=self.config.rearm_stability_ms and gate['new_detection_seen']):
            self.rearm_stability_passes+=1;self.rearm_stability_gate=None
            return True
        self.rearm_stability_waits+=1
        self.state='CONFIRMING';self.reason='WAITING_FOR_STABLE_REARM'
        return False

    def status(self):
        control=self.controller.status()
        control.update(velocity_us_s=self.pva[1],acceleration_us_s2=self.pva[2],pulse_us=round(self.pva[0]),
                       position_filter='one_euro',outlier_gate='large_jump_requires_next_actual_image',
                       filter_cutoff_hz=self.controller.center_filter.cutoff_hz,jump_rejections=self.controller.jump_rejections)
        remaining=None if self.config.maximum_correction_us is None or self.correction_origin is None else max(0.,self.config.maximum_correction_us-abs(self.current['width_us']-self.correction_origin))
        return dict(state=self.state,reason=self.reason,active=self.active,fatal=self.fatal,pulse_us=self.current['width_us'],
         target_us=self.current['target_us'],commands_accepted=self.acks,hold_renewals=self.hold_renewals,
         motion_target_changes=self.motion_updates,segments=self.segments,trajectory_ticks=self.trajectory_ticks,
         range_us=[self.minimum,self.maximum],authorized_range_us=[self.config.minimum_us,self.config.maximum_us],
         elapsed_s=round(self.clock()-self.started,3),heartbeat_mono_ms=round(self.clock()*1000),control=control,
         readback=self.current,events=list(self.events),command_trace=list(self.command_trace),
         correction_limit_us=self.config.maximum_correction_us,
         motion_mode='CONTINUOUS_FACE_FOLLOW' if self.config.maximum_correction_us is None else 'BOUNDED_DIAGNOSTIC',correction_remaining_us=remaining,
         full_pulse_visual_stops=self.full_pulse_visual_stops,
         correction_rearm=self.rearm.status(),correction_budget_releases=self.correction_releases,
         fresh_image_lease_renewals=self.fresh_image_lease_renewals,control_polarity=self.polarity,
         initial_pwm_budget_waits=self.initial_pwm_budget_waits,
         recenter_active=self.controller.recenter_active,
         recenter_state=control['recenter_state'],target_center_ratio=self.controller.recenter_target_center_ratio,
         recenter_intent_pending=bool(self.recenter_intent and round(self.clock()*1000)<self.recenter_intent['expires_ms']),
         pwm_output_started=self.epoch_output_started,
         rearm_stability_ms=self.config.rearm_stability_ms,rearm_stability_gate=(dict(self.rearm_stability_gate) if self.rearm_stability_gate is not None else None),
         rearm_stability_waits=self.rearm_stability_waits,rearm_stability_passes=self.rearm_stability_passes,
         brief_face_gap=self.brief_face_gap,brief_face_gaps=self.brief_face_gaps,
         brief_face_recoveries=self.brief_face_recoveries,
         center_settling=self.center_settling,center_settles=self.center_settles,
         renewal_reserve_ms=FRESH_SOURCE_RENEWAL_RESERVE_MS,
         proactive_source_renewals=self.proactive_source_renewals,
         authority_deadline_mono_ms=self.controller.authority_deadline_ms if self.authority else None)
    def stop_segment(self,reason,*,normal=False):
        previous=self.controller;had_output=self.epoch_output_started
        stop_details=dict(trigger_side=previous.recenter_trigger_side,
            target_center_ratio=previous.recenter_target_center_ratio,
            endpoint_us=self.current.get('target_us'),had_output=had_output,
            original_authority_deadline_ms=previous.authority_deadline_ms)
        if (self.config.hardware_slew_recenter and self.config.rearm_stability_ms
                and self.active and reason in RECENTER_RESUMABLE_REASONS):
            self.rearm_stability_gate=dict(reason=reason,interrupted_mono_ms=round(self.clock()*1000),
                interrupted_anchor_ms=previous.anchor_stamp if type(previous.anchor_stamp) is int else -1)
            self.reset_rearm_stability_progress()
        self.retain_recenter_intent(reason)
        if self.active and not normal and reason in VISUAL_REASONS|{'SOURCE_HORIZON_ENDED','VISION_STREAM_INTERRUPTED','CONTROL_TICK_LATE'}:
            readback=self.device.status()
            if (readback['reason']==0 and readback['flags']&14==14
                    and readback['session']==self.device.session and readback['epoch']==self.device.epoch
                    and readback['ack_seq']==self.device.ack_seq and readback['target_us']==self.device.accepted_target_us):
                # QUIESCE never starts another PWM pulse, completes at most
                # the current <=1.6ms pulse, and still obeys hardware expiry.
                # Unknown protocol/hardware faults retain immediate STOP.
                normal=True;self.full_pulse_visual_stops+=1
        self.current=self.device.finish() if normal else self.device.stop();self.require_stopped(self.current)
        self.active=False;self.controller=self.fresh();self.pva=[float(self.current['width_us']),0.,0.]
        self.authority=self.source_origin=self.last_commit_source=None
        self.zone_holding=False;self.segment_start=None;self.state='MONITORING';self.note(reason,emitted_width_us=self.current['width_us'],**stop_details)
        self.epoch_output_started=False
        self.brief_face_gap=self.center_settling=False
        self.lease_expiry_lower_bound=None
        self.rearm.reset()
    def fail(self,reason,evidence=None):
        self.stop_segment(reason);self.fatal=True;self.state='FAULT'
        if evidence is not None:self.events[-1]['rejected_readback']=evidence
        return self.status()
    def disconnected(self):
        self.reset_rearm_stability_progress()
        self.rearm.reset()
        if self.active:self.stop_segment('VISION_STREAM_INTERRUPTED')
        else:
            self.retain_recenter_intent('VISION_STREAM_INTERRUPTED')
            self.controller=self.fresh();self.state='WAITING_FOR_FACE';self.reason='VISION_STREAM_INTERRUPTED'
    def read_active(self):
        began=self.clock();self.current=self.device.status();r=self.current
        # Starting before the read gives a conservative expiry estimate even
        # when Python resumes long after this remaining-lease snapshot.
        self.lease_expiry_lower_bound=began+max(0,r['lease_left_ms'])/1000.
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

    def brake_brief_face_gap(self,packet,now):
        """A transient packet supplies no authority, displacement or renewal.

        Only a canonical same-camera pending/rejected measurement can use
        the last admitted image's unmodified finite authority to decelerate.
        Explicit continuity loss, expiry, stream faults or malformed messages
        still stop immediately. An initial ARM never gets a missing-frame grace.
        """
        c=self.controller;tracking=packet.get('face_tracking') or {}
        if not (self.config.recenter_on_edge and self.active and self.epoch_output_started
                and self.authority is not None and self.authority==c.source and c.context is not None
                and packet.get('state')=='UNCONFIRMED'
                and (packet.get('service_epoch'),packet.get('camera_epoch'))==c.context[:2]
                and (packet.get('frame_width'),packet.get('frame_height'))==c.context[4:]
                and packet.get('mirror_horizontal') is True
                and all(packet.get(k) is None for k in
                        ('target','source_frame_id','source_mono_ms','deadline_mono_ms'))
                and isinstance(tracking,dict) and type(tracking.get('version')) is int
                and tracking.get('version')==11 and tracking.get('error')==''
                and tracking.get('reason') in BRIEF_FACE_GAP_REASONS
                and c.authority_deadline_ms is not None
                and now<c.authority_deadline_ms/1000.-.023):
            return False
        if not self.brief_face_gap:
            self.brief_face_gaps+=1;self.note('BRIEF_FACE_GAP_BRAKING')
        self.brief_face_gap=True;c.requested_speed=0.
        self.state='BRAKING';self.reason='BRIEF_FACE_GAP_BRAKING'
        return True

    def step(self,packet):
        if self.fatal:return self.status()
        now=self.clock();stamp=packet.get('source_mono_ms') if isinstance(packet,dict) else None
        if isinstance(packet,dict) and packet.get('target_kind')!='face':return self.fail('FACE_SOURCE_REQUIRED')
        if self.restore_recenter_intent(packet,round(now*1000)) is False:return self.status()
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
            self.reset_rearm_stability_progress()
            reason=self.controller.reason
            if reason not in VISUAL_REASONS:return self.fail(reason)
            if self.active:self.stop_segment(reason)
            else:
                self.retain_recenter_intent(reason)
                self.controller=self.fresh();self.rearm.reset();self.reason=reason;self.state='WAITING_FOR_FACE'
            return self.status()
        if not value['new_source']:
            if isinstance(packet,dict) and packet.get('state')!='READY':self.reset_rearm_stability_progress()
            if (self.config.recenter_on_edge and self.active and isinstance(packet,dict)
                    and packet.get('state') in ('UNCONFIRMED','EXPIRED')):
                if self.brake_brief_face_gap(packet,now):return self.status()
                self.stop_segment('SOURCE_'+packet['state']);return self.status()
            if (isinstance(packet,dict) and packet.get('state')!='READY'
                    or self.controller.reason=='MEASUREMENT_JUMP_PENDING'):self.rearm.reset()
            if self.active and self.controller.pending_safe_zone and self.read_active():
                # An uncertain jump may stop motion, never grant new motion
                # or refresh the old image's deadline.
                self.zone_holding=True;self.segment_start=None
                self.pva=[float(self.current['width_us']),0.,0.]
                self.state='HOLDING';self.reason='SAFE_ZONE_HOLD_PENDING_CONFIRMATION'
            return self.status()
        if self.brief_face_gap:
            self.brief_face_gap=False;self.brief_face_recoveries+=1
            self.note('BRIEF_FACE_GAP_RECOVERED')
        self.cache_recenter_intent()
        if self.rearm.observe(self.controller.source,value['reason']=='SAFE_ZONE_HOLD'):
            if self.correction_origin is not None:self.correction_releases+=1
            self.correction_origin=None;self.correction_side=0
        if not self.active:
            self.reason=value['reason']
            if value['confirmed_sources']<self.config.confirm_frames:return self.status()
            near_trigger=(not self.config.recenter_on_edge or self.controller.raw_center>=self.config.right_ratio-.05
                          or self.controller.raw_left_ratio<=(self.config.left_ratio or 2./640)+.05)
            prearm=(value['reason']=='SAFE_ZONE_HOLD' and self.config.prearm_confirmed_face and near_trigger)
            if value['reason']=='SAFE_ZONE_HOLD' and not prearm:
                self.state='MONITORING';self.reason='SAFE_ZONE_HOLD'
                return self.status()
            if not value['edge'] and not prearm:return self.status()
            if not self.rearm_stability_ready(round(now*1000)):return self.status()
            if (self.config.maximum_correction_us is not None and self.correction_origin is not None and self.correction_side==value['edge']
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
            self.authority=None;self.state='CONFIRMING'
            self.note('FACE_CONFIRMED_PREARM_NO_PWM' if prearm else 'FACE_CONFIRMED_ARM_CURRENT_POSITION')
            self.epoch_output_started=False
            if value['edge'] and (self.correction_origin is None or self.correction_side!=value['edge']):
                self.correction_origin=reference.reference_us;self.correction_side=value['edge']
            return self.status()
        if not self.read_active():return self.status()
        self.authority=self.controller.source;self.source_origin=self.current['target_us']
        if value['reason']=='SAFE_ZONE_HOLD':
            moving=abs(self.pva[1])>1e-6 or abs(self.pva[2])>1e-6
            if (self.config.recenter_on_edge and self.config.smooth_recenter_stop
                    and self.epoch_output_started and moving):
                if not self.center_settling:self.center_settles+=1
                self.center_settling=True;self.zone_holding=False
                self.controller.requested_speed=0.
                self.state='BRAKING';self.reason='CENTER_SETTLING'
            else:
                self.center_settling=False;self.zone_holding=True;self.segment_start=None
                self.pva=[float(self.current['target_us']),0.,0.]
                self.controller.freeze_at(self.current['target_us'])
                self.state='HOLDING';self.reason='SAFE_ZONE_HOLD'
        else:
            self.center_settling=False
            self.zone_holding=False
            if value['edge'] and (self.correction_origin is None or self.correction_side!=value['edge']):
                self.correction_origin=self.current['width_us'];self.correction_side=value['edge']
            if value['edge'] and self.limit_side and value['edge']*self.polarity!=self.limit_side:self.limit_side=0
            if value['edge'] and self.segment_start is None:self.segment_start=now
            self.state='BRAKING' if value['reason']=='EDGE_BRAKING' else 'FOLLOWING'
            self.reason=value['reason']
        remaining_ms=((self.lease_expiry_lower_bound-self.clock())*1000.
                      if self.lease_expiry_lower_bound is not None else 0.)
        if self.epoch_output_started and remaining_ms<=FRESH_SOURCE_RENEWAL_RESERVE_MS:
            # A genuinely new admitted image may arrive only a few ms before
            # the old lease expires. Waiting for the next 20ms trajectory
            # tick would needlessly lose ARM. Renew the unchanged angle now,
            # using ONLY this new image and its actual bounded deadline.
            deadline=self.controller.authority_deadline_ms
            if deadline is None:return self.fail('MISSING_AUTHORITY_DEADLINE')
            if self.clock()>=deadline/1000.-.023:
                self.stop_segment('SOURCE_HORIZON_ENDED');return self.status()
            if self.submit_target(self.current['target_us'],'FRESH_IMAGE_SAME_TARGET_RENEWAL'):
                self.fresh_image_lease_renewals+=1
                if remaining_ms>40:self.proactive_source_renewals+=1
        return self.status()

    def initial_pwm_budget_ready(self):
        if self.epoch_output_started:return True
        deadline=self.controller.authority_deadline_ms
        required_ms=(SUBMISSION_MARGIN_MS+INITIAL_PWM_MINIMUM_LEASE_MS+COMMIT_PREFLIGHT_RESERVE_MS)
        if (deadline/1000.-self.clock())*1000.>required_ms:return True
        # No pulse has started. Do not briefly replay the old width for a
        # lease too short to output the requested next frame. While waiting,
        # do not bank a trajectory position or velocity the motor never ran.
        # The original authority is unchanged; only a genuinely new image or
        # anchor can supply a later deadline.
        self.initial_pwm_budget_waits+=1
        self.pva=[float(self.current['width_us']),0.,0.]
        self.state='CONFIRMING';self.reason='WAITING_FOR_INITIAL_PWM_BUDGET'
        return False

    def submit_target(self,target,kind):
        fid,stamp=self.authority;deadline=self.controller.authority_deadline_ms
        now=self.clock();old_target=self.current['target_us']
        if not self.initial_pwm_budget_ready():return False
        minimum_lease_ms=0 if self.epoch_output_started else INITIAL_PWM_MINIMUM_LEASE_MS
        freshness_s=(deadline-stamp)/1000.
        options=dict(freshness_s=freshness_s,margin_s=.02)
        if minimum_lease_ms:options['minimum_lease_ms']=minimum_lease_ms
        ack=self.device.submit(target,stamp/1000.,**options)
        if ack['outcome']!='ACCEPTED':
            if ack['reason'] in ('STALE_SOURCE','SUBMISSION_TOO_LATE','SOURCE_LEASE_EXPIRED'):
                self.stop_segment('SOURCE_SUBMISSION_EXPIRED');return False
            self.fail('COMMAND_'+ack['reason'],ack.get('rejected_readback',ack.get('readback')))
            return False
        self.acks+=1;self.epoch_output_started=True;self.last_commit_source=self.authority
        self.current=ack.get('readback') or self.device.status()
        self.lease_expiry_lower_bound=now+max(0,self.current['lease_left_ms'])/1000.
        if target==old_target:self.hold_renewals+=1
        else:self.motion_updates+=1
        self.minimum=min(self.minimum,self.current['width_us']);self.maximum=max(self.maximum,self.current['width_us'])
        self.command_trace.append(dict(mono_ms=round(now*1000),source_frame_id=fid,source_mono_ms=stamp,
            deadline_mono_ms=deadline,image_deadline_mono_ms=stamp+250,
            face_anchor_mono_ms=self.controller.anchor_stamp,source_age_ms=round(now*1000-stamp),
            target_us=target,delta_us=target-old_target,velocity_us_s=round(self.pva[1],4),
            acceleration_us_s2=round(self.pva[2],4),lease_ms=ack.get('lease_ms'),state=self.state,command_kind=kind))
        return True

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
        deadline=self.controller.authority_deadline_ms
        if deadline is None:return self.fail('MISSING_AUTHORITY_DEADLINE')
        if now>=deadline/1000.-.023:self.stop_segment('SOURCE_HORIZON_ENDED');return self.status()
        if not self.read_active():return self.status()
        if self.segment_start is not None and now-self.segment_start>=10:
            self.stop_segment('MOTION_SEGMENT_TIME_LIMIT',normal=True);return self.status()
        if not self.zone_holding:
            if not self.initial_pwm_budget_ready():return self.status()
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
            if self.config.maximum_correction_us is not None and self.correction_origin is not None:
                low=max(low,self.correction_origin-self.config.maximum_correction_us)
                high=min(high,self.correction_origin+self.config.maximum_correction_us)
            if not low<=self.pva[0]<=high:
                self.pva=[max(low,min(high,self.pva[0])),0.,0.]
                self.state='HOLDING';self.reason='CORRECTION_STEP_COMPLETE' if self.config.maximum_correction_us is not None and self.correction_origin is not None and abs(self.pva[0]-self.correction_origin)>=self.config.maximum_correction_us else 'SOURCE_DISPLACEMENT_BUDGET'
        target=round(self.pva[0]);old_target=self.current['target_us']
        if not self.epoch_output_started and target==old_target:
            # ARM is not PWM. Do not energize a resting servo just to send
            # the identical initial width during a boundary false start.
            return self.status()
        if target==old_target and self.last_commit_source==self.authority:
            self.finish_center_settle()
            return self.status()
        if not self.config.minimum_us<=target<=self.config.maximum_us:return self.fail('TRAJECTORY_RANGE')
        if abs(target-old_target)>self.config.maximum_step_us:return self.fail('TRAJECTORY_STEP')
        self.submit_target(target,'TRAJECTORY_TICK')
        self.finish_center_settle()
        return self.status()

    def finish_center_settle(self):
        if (self.active and self.center_settling
                and abs(self.pva[1])<=1e-6 and abs(self.pva[2])<=1e-6):
            self.center_settling=False;self.zone_holding=True;self.segment_start=None
            # The accepted target can lead width by one hardware frame. Do
            # not withdraw that target and introduce an artificial reverse step.
            pulse=self.current['target_us'];self.pva=[float(pulse),0.,0.]
            self.controller.freeze_at(pulse)
            self.state='HOLDING';self.reason='SAFE_ZONE_HOLD'

    def close(self):
        self.recenter_intent=None
        if self.active:self.stop_segment('OPERATOR_STOP',normal=not bool(self.device.status()['reason']))
        else:self.current=self.device.stop()
        self.state='STOPPED';self.reason='OPERATOR_STOP';return self.status()
