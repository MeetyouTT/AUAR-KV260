"""Continuous face monitor, bounded motion segments and source-bound leases."""
from collections import deque
import time
from continuous_face_control import FaceEdgeController

VISUAL_REASONS={'SOURCE_NO_TARGET','SOURCE_UNCONFIRMED','SOURCE_EXPIRED','SOURCE_EXPIRED',
 'SOURCE_MULTIPLE_FACES','FACE_CONTEXT_CHANGED','SOURCE_GAP','SOURCE_FACE_ERROR',
 'SOURCE_FACE_UNAVAILABLE','SOURCE_INCONSISTENT_FACE_SOURCE','FACE_QUALITY','FACE_TOO_LARGE'}


class ContinuousSession:
    def __init__(self,device,boot,config,reference_factory,*,clock=time.monotonic,allow_fixture=False):
        self.device,self.boot,self.config,self.factory=device,boot,config,reference_factory
        self.clock,self.allow_fixture=clock,allow_fixture
        self.started=clock();self.active=False;self.fatal=False;self.lockout_side=0
        self.segments=self.acks=0;self.events=deque(maxlen=48);self.segment_start=None
        self.hold_renewals=self.motion_updates=0;self.zone_holding=False
        self.state,self.reason='MONITORING','WAITING_FOR_FACE'
        self.current=device.status();self.require_stopped(self.current)
        self.minimum=self.maximum=self.current['width_us'];self.controller=self.fresh()
    def require_stopped(self,value):
        if value['flags'] or value['lease_left_ms'] or value['reason'] or not self.config.minimum_us<=value['width_us']<=self.config.maximum_us:
            raise RuntimeError('Stopped current command and authorized finite range required')
    def fresh(self):
        return FaceEdgeController(self.boot,self.current['width_us'],polarity=1,config=self.config)
    def note(self,reason,**fields):
        self.reason=reason;self.events.append(dict(reason=reason,mono_ms=round(self.clock()*1000),**fields))
    def status(self):
        value=self.controller.status()
        return dict(state=self.state,reason=self.reason,active=self.active,fatal=self.fatal,
          pulse_us=self.current['width_us'],target_us=value['pulse_us'],commands_accepted=self.acks,
          hold_renewals=self.hold_renewals,motion_target_changes=self.motion_updates,
          segments=self.segments,range_us=[self.minimum,self.maximum],authorized_range_us=[self.config.minimum_us,self.config.maximum_us],
          elapsed_s=round(self.clock()-self.started,3),heartbeat_mono_ms=round(self.clock()*1000),
          control=value,readback=self.current,events=list(self.events))
    def stop_segment(self,reason,*,normal=False,lockout=0):
        self.current=self.device.finish() if normal else self.device.stop()
        self.require_stopped(self.current);self.active=False;self.lockout_side=lockout
        self.minimum=min(self.minimum,self.current['width_us']);self.maximum=max(self.maximum,self.current['width_us'])
        self.controller=self.fresh();self.state='HOLD_AT_LIMIT' if lockout else 'MONITORING'
        self.zone_holding=False
        self.note(reason)
    def fail(self,reason):
        self.stop_segment(reason);self.fatal=True;self.state='FAULT';return self.status()
    def disconnected(self):
        if self.active:self.stop_segment('VISION_STREAM_INTERRUPTED')
        else:self.controller=self.fresh();self.state='WAITING_FOR_FACE';self.reason='VISION_STREAM_INTERRUPTED'
    def step(self,packet):
        if self.fatal:return self.status()
        now=self.clock();previous=self.controller.source
        stamp=packet.get('source_mono_ms')
        if self.active and type(stamp) is int and stamp/1000.<=self.device.reference_time:return self.status()
        value=self.controller.observe(packet,int(now*1000),allow_fixture=self.allow_fixture)
        if self.controller.stopped:
            reason=self.controller.reason
            if reason not in VISUAL_REASONS:return self.fail(reason)
            if self.active:self.stop_segment(reason)
            else:self.controller=self.fresh();self.state='WAITING_FOR_FACE';self.reason=reason
            return self.status()
        if not self.active:
            self.reason=value['reason']
            if value['reason']=='SAFE_ZONE_HOLD':
                self.lockout_side=0;self.state='MONITORING';return self.status()
            if not value['new_source'] or not value['edge']:return self.status()
            side=value['edge']
            self.current=self.device.status();self.require_stopped(self.current)
            if (self.lockout_side==side or side<0 and self.current['width_us']<=self.config.minimum_us
                    or side>0 and self.current['width_us']>=self.config.maximum_us):
                self.lockout_side=side;self.state='HOLD_AT_LIMIT';self.reason='FINITE_RANGE_REACHED';return self.status()
            reference=self.factory(self.current['width_us'])
            self.device.confirm_and_arm(reference,int(now*1e6)%0xffffffff or 1,self.current['epoch']+1,authorized=True)
            self.current=self.device.status();self.active=True;self.segment_start=now;self.segments+=1
            self.controller=FaceEdgeController(self.boot,reference.reference_us,polarity=1,config=self.config).inherit_perception(self.controller)
            self.state='CONFIRMING';self.note('FACE_EDGE_CONFIRMED_ARM_NO_PWM',edge=side)
            return self.status()
        self.current=self.device.status()
        if self.current['reason'] or not self.current['armed']:
            if (self.current['flags']==4<<4 and self.current['lease_left_ms']==0
                    and previous is not None and now-previous[1]/1000.>=.2
                    and self.current['session']==self.device.session and self.current['epoch']==self.device.epoch
                    and self.current['ack_seq']==self.device.ack_seq and self.device.ack_seq>0
                    and self.current['target_us']==self.device.accepted_target_us):
                self.stop_segment('SOURCE_LEASE_EXPIRED');return self.status()
            return self.fail('HARDWARE_PERMISSION_LOST')
        if self.segment_start is not None and now-self.segment_start>=10 and not self.zone_holding:
            self.stop_segment('MOTION_SEGMENT_TIME_LIMIT',normal=True,lockout=value['edge']);return self.status()
        if not value['new_source']:return self.status()
        stamp=packet.get('source_mono_ms')
        if type(stamp) is not int or stamp/1000.<=self.device.reference_time:return self.status()
        if value['reason']=='SAFE_ZONE_HOLD':
            if not self.current['flags']&1:
                self.stop_segment('SAFE_ZONE_REACHED_BEFORE_OUTPUT',normal=True);return self.status()
            # Hold the CURRENT angle with an unchanged PWM target. Switching
            # PWM off every time the face re-enters the zone causes repeated
            # loss/reacquisition of servo holding torque and visible kicks.
            self.controller.freeze_at(self.current['width_us'])
            value=self.controller.status();self.zone_holding=True;self.segment_start=None
            self.state='HOLDING';self.reason='SAFE_ZONE_HOLD';self.lockout_side=0
        else:
            if value['edge']:
                if self.zone_holding:self.segment_start=now
                self.zone_holding=False
            self.state='FOLLOWING' if value['edge'] else 'CONFIRMING';self.reason=value['reason']
        if not self.device.commit_attempts and value['pulse_us']==self.current['width_us']:return self.status()
        # Every renewal still requires a distinct fresh image; duplicate
        # observations never refresh the old source's hardware deadline.
        if not value['edge'] and not self.zone_holding and value['pulse_us']==self.current['width_us']:return self.status()
        old_target=self.current['target_us']
        ack=self.device.submit(value['pulse_us'],stamp/1000.,freshness_s=.25,margin_s=.02)
        if ack['outcome']!='ACCEPTED':
            if ack['reason'] in ('STALE_SOURCE','SUBMISSION_TOO_LATE','SOURCE_LEASE_EXPIRED'):
                self.stop_segment(ack['reason'] if ack['reason']=='SOURCE_LEASE_EXPIRED' else 'SOURCE_SUBMISSION_EXPIRED')
                if ack.get('rejected_readback') is not None:
                    self.events[-1]['rejected_readback']=ack['rejected_readback']
                return self.status()
            return self.fail('COMMAND_'+ack['reason'])
        self.acks+=1;self.current=ack.get('readback') or self.device.status()
        if value['pulse_us']!=old_target:self.motion_updates+=1
        else:self.hold_renewals+=1
        self.minimum=min(self.minimum,self.current['width_us']);self.maximum=max(self.maximum,self.current['width_us'])
        if value['reason']=='AT_LIMIT':self.stop_segment('FINITE_RANGE_REACHED',normal=True,lockout=value['edge'])
        return self.status()
    def close(self):
        if self.active:
            current=self.device.status()
            self.stop_segment('OPERATOR_STOP',normal=not bool(current['reason']))
        else:self.current=self.device.stop()
        self.state='STOPPED';self.reason='OPERATOR_STOP';return self.status()
