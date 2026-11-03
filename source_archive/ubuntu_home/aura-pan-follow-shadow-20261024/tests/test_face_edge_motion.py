"""Driver integration of safe-zone silence, source-bound output and STOP."""
from pathlib import Path
import sys,unittest
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'motion_v2'));sys.path.insert(0,str(ROOT))
from face_edge_control import FaceEdgeController
from face_motion import run_session
from test_face_edge_control import packet


class Device:
    def __init__(self,clock):
        self.clock=clock;self.reference=self.reference_time=None
        self.pulse=1435;self.armed=False;self.acks=[];self.arms=0;self.finishes=0
    def status(self):
        return dict(flags=14 if self.armed else 0,lease_left_ms=0,width_us=self.pulse,
                    armed=self.armed,reason=0)
    def confirm_and_arm(self,reference,*args,**kwargs):
        self.reference=reference;self.reference_time=self.clock();self.armed=True;self.arms+=1
    def submit(self,pulse,stamp,**kwargs):
        assert self.armed and 0<=self.clock()-stamp<.23 and kwargs['freshness_s']==.25
        self.pulse=pulse;self.acks.append((pulse,stamp))
        return dict(outcome='ACCEPTED',target_us=pulse)
    def finish(self):
        self.finishes+=1
        return self.stop()
    def stop(self):
        self.armed=False;self.reference=None
        return self.status()


class MotionTests(unittest.TestCase):
    def evaluate(self,xs,tail=None):
        now=[1.];clock=lambda:now[0];device=Device(clock)
        controller=FaceEdgeController('boot',1435)
        def packets():
            for fid,x in enumerate(xs,1):
                now[0]=1+fid*.1+.02
                p=packet(fid,1000+fid*100,x);p['source_kind']='actual';yield p
            if tail:
                now[0]+=.05;yield tail
        result=run_session(device,SimpleNamespace(reference_us=1435),controller,packets(),1,1,clock=clock)
        self.assertEqual(result['stopped']['flags'],0)
        self.assertEqual(device.arms,1)
        return result,device
    def test_safe_zone_never_commits_pwm(self):
        r,d=self.evaluate([150.,280.,400.]*3)
        self.assertEqual(d.acks,[]);self.assertEqual(r['commands_accepted'],0)
    def test_edge_turns_then_quiesces_after_safe_margin(self):
        r,d=self.evaluate([550.]*8+[280.]*10)
        self.assertGreater(len(d.acks),0);self.assertEqual(r['reason'],'SAFE_ZONE_REACHED')
        self.assertEqual(d.finishes,1)
        pulses=[1435]+[p for p,t in d.acks]
        self.assertTrue(all(1425<=p<=1445 for p in pulses))
        self.assertTrue(all(abs(a-b)<=2 for a,b in zip(pulses,pulses[1:])))
    def test_lost_face_stops_without_automatic_rearm(self):
        p=packet(9,1900,280.,state='NO_TARGET',target=None);p['source_kind']='actual'
        r,d=self.evaluate([550.]*8,p)
        self.assertEqual(r['reason'],'SOURCE_NO_TARGET');self.assertEqual(d.finishes,0)

    def test_idle_face_loss_can_reconfirm_before_first_pwm_without_rearming(self):
        now=[1.];d=Device(lambda:now[0]);c=FaceEdgeController('boot',1435)
        def frames():
            for fid in range(1,14):
                now[0]=1+fid*.1+.02
                q=packet(fid,1000+fid*100,280. if fid<5 else 550.);q['source_kind']='actual'
                if fid==5:q.update(state='NO_TARGET',target=None)
                yield q
        r=run_session(d,SimpleNamespace(reference_us=1435),c,frames(),1,1,clock=lambda:now[0])
        self.assertTrue(any(x.get('waiting_without_output') for x in r['events']))
        self.assertEqual(d.arms,1);self.assertGreater(r['commands_accepted'],0)
        self.assertTrue(all(stamp>=2. for pulse,stamp in d.acks))
    def test_expired_face_stops_without_renewing_from_duplicate(self):
        p=packet(8,1800,550.);p['source_kind']='actual'
        # An expired packet is delivered after an additional 250ms pause.
        now=[1.];d=Device(lambda:now[0]);c=FaceEdgeController('boot',1435)
        def frames():
            for fid in range(1,9):
                now[0]=1+fid*.1+.02
                q=packet(fid,1000+fid*100,550.);q['source_kind']='actual';yield q
            now[0]=2.051;yield p
        r=run_session(d,SimpleNamespace(reference_us=1435),c,frames(),1,1,clock=lambda:now[0])
        self.assertEqual(r['reason'],'SOURCE_EXPIRED');self.assertEqual(d.arms,1)
        self.assertEqual(r['stopped']['flags'],0)


if __name__=='__main__':unittest.main()
