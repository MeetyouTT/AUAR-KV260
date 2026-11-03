"""Software frame-boundary plant model: no hardware, inertia or mechanical claims."""
import math


class PWMDevice:
    def __init__(self,clock,reference_us=1469):
        self.clock=clock;self.pulse=self.accepted_target_us=reference_us
        self.armed=self.active=False;self.reason=0;self.epoch=80;self.session=1;self.ack_seq=0
        self.reference_time=None;self.reference_us=reference_us
        self.deadline=self.next_frame=None;self.commands=[];self.pulses=[]
        self.arms=self.finishes=0
    def advance(self):
        now=self.clock()
        if self.active:
            while self.next_frame<=now and self.next_frame<self.deadline:
                self.pulse+=max(-4,min(4,self.accepted_target_us-self.pulse))
                self.pulses.append(dict(now=self.next_frame,pulse=self.pulse))
                self.next_frame+=.02
            if now>=self.deadline:self.active=self.armed=False;self.reason=4
    def status(self):
        self.advance();flags=(15 if self.active else 14 if self.armed else 0)|(self.reason<<4)
        return dict(flags=flags,width_us=self.pulse,target_us=self.accepted_target_us,
            lease_left_ms=max(0,int((self.deadline-self.clock())*1000)) if self.active else 0,
            session=self.session,epoch=self.epoch,ack_seq=self.ack_seq,reference_us=self.reference_us,
            reason=self.reason,armed=self.armed)
    def confirm_and_arm(self,reference,session,epoch,**kwargs):
        assert not self.active and not self.armed
        self.reference_us=self.pulse=self.accepted_target_us=reference.reference_us
        self.armed=True;self.active=False;self.reason=0;self.session=session;self.epoch=epoch
        self.ack_seq=0;self.reference_time=self.clock();self.arms+=1
    def submit(self,target,stamp,**kwargs):
        self.advance();assert self.armed and self.reference_time<stamp<=self.clock()
        freshness=kwargs.get('freshness_s',.25);margin=kwargs.get('margin_s',.02)
        budget=math.floor((stamp+freshness-self.clock()-margin)*1000);assert budget>=3
        if not self.active:
            self.next_frame=self.clock()+.02
            # First PWM pulse uses the confirmed current width, as RTL.
            self.pulses.append(dict(now=self.clock(),pulse=self.pulse))
        self.accepted_target_us=target;self.ack_seq+=1;self.active=True
        self.deadline=self.clock()+budget/1000.
        self.commands.append(dict(now=self.clock(),stamp=stamp,target=target,deadline=self.deadline))
        return dict(outcome='ACCEPTED',lease_ms=budget,readback=self.status())
    def stop(self):
        self.advance();self.armed=self.active=False;self.reason=0;return self.status()
    def finish(self):self.finishes+=1;return self.stop()
