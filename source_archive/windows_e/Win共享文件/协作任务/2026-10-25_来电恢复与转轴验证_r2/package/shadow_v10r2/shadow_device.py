"""In-memory command acknowledgements only. This module has no actuator IO."""
import math,time


class ShadowDevice:
    def __init__(self,reference_us,*,clock=time.monotonic):
        if type(reference_us) is not int or not 1400<=reference_us<=1600:raise ValueError('Finite virtual reference required')
        self.clock=clock;self.pulse=self.accepted_target_us=reference_us
        self.session=self.epoch=self.ack_seq=0;self.reference_time=self.deadline=None
        self.armed=self.active=False;self.reason=0;self.reference_us=reference_us
        self.arms=self.commits=self.finishes=self.stops=0;self.commands=[]
    def status(self):
        if self.active and self.clock()>=self.deadline:self.active=self.armed=False;self.reason=4
        return dict(flags=(15 if self.active else 14 if self.armed else 0)|(self.reason<<4),
            width_us=self.pulse,target_us=self.pulse,reference_us=self.reference_us,
            session=self.session,epoch=self.epoch,ack_seq=self.ack_seq,reason=self.reason,armed=self.armed,
            lease_left_ms=max(0,math.floor((self.deadline-self.clock())*1000)) if self.active else 0)
    def confirm_and_arm(self,reference,session,epoch,**options):
        if options.get('authorized') is not True:raise ValueError('Explicit virtual session required')
        if not 1400<=reference.reference_us<=1600:raise ValueError('Virtual reference outside finite bounds')
        self.pulse=self.accepted_target_us=self.reference_us=reference.reference_us
        self.session,self.epoch,self.ack_seq=session,epoch,0
        self.reference_time=self.clock();self.armed=True;self.active=False;self.reason=0;self.arms+=1
    def submit(self,target,stamp,freshness_s=.25,margin_s=.02):
        self.status();now=self.clock()
        if not self.armed or self.reason:raise RuntimeError('Virtual permission lost')
        if (type(target) is not int or not 1400<=target<=1600 or abs(target-self.accepted_target_us)>4
                or stamp<=self.reference_time or stamp>now or not 0<margin_s<freshness_s<=.25):
            raise ValueError('Invalid virtual command or actual source contract')
        lease=math.floor((stamp+freshness_s-now-margin_s)*1000)
        if lease<3:
            self.stop();return dict(outcome='REJECTED',reason='STALE_SOURCE')
        previous=self.accepted_target_us
        self.pulse=self.accepted_target_us=target;self.ack_seq+=1;self.commits+=1
        self.active=True;self.deadline=now+lease/1000.
        self.commands.append(dict(mono_ms=round(now*1000),source_mono_ms=round(stamp*1000),
            target_us=target,delta_us=target-previous,deadline_mono_ms=math.floor(self.deadline*1000),
            effective_source_deadline_mono_ms=math.floor((stamp+freshness_s)*1000)))
        return dict(outcome='ACCEPTED',lease_ms=lease,readback=self.status(),scope='SOFTWARE_SHADOW_ONLY')
    def stop(self):self.armed=self.active=False;self.reason=0;self.stops+=1;return self.status()
    def finish(self):self.finishes+=1;return self.stop()
