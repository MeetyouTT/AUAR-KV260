import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_face_zone import packet
from face_edge_control import FaceEdgeController
from face_motion import run_session

class Device:
    def __init__(self,clock):
        self.clock=clock;self.reference=self.reference_time=None;self.pulse=1445
        self.armed=False;self.arms=0;self.commands=[]
    def status(self):return dict(flags=14 if self.armed else 0,lease_left_ms=0,width_us=self.pulse,armed=self.armed,reason=0)
    def confirm_and_arm(self,ref,*args,**kwargs):
        self.reference=ref;self.reference_time=self.clock();self.armed=True;self.arms+=1
    def submit(self,pulse,stamp,**kwargs):
        assert self.armed and 0<=self.clock()-stamp<.23
        self.commands.append(pulse);self.pulse=pulse;return dict(outcome='ACCEPTED')
    def stop(self):self.armed=False;self.reference=None;return self.status()
    def finish(self):return self.stop()

class SessionTests(unittest.TestCase):
    def run_case(self,centers,lose=False):
        now=[1.];d=Device(lambda:now[0]);c=FaceEdgeController('boot',1445)
        def frames():
            for fid,center in enumerate(centers,1):
                q=packet(fid,center);q['source_kind']='actual'
                now[0]=q['source_mono_ms']/1000+.02;yield q
            if lose:
                q=packet(len(centers)+1,.9);q.update(source_kind='actual',state='NO_TARGET',target=None)
                now[0]=q['source_mono_ms']/1000+.02;yield q
        r=run_session(d,SimpleNamespace(reference_us=1445),c,frames(),1,1,clock=lambda:now[0])
        self.assertEqual(r['stopped']['flags'],0);self.assertEqual(d.arms,1)
        return r,d
    def test_inside_emits_no_pwm(self):
        r,d=self.run_case([.2,.5,.8]*8);self.assertEqual(d.commands,[])
    def test_right_crossing_then_inside_stops_without_extra_command(self):
        r,d=self.run_case([.9]*12+[.805]*5)
        self.assertEqual(r['reason'],'SAFE_ZONE_REACHED');self.assertGreater(len(d.commands),0)
        self.assertGreater(d.pulse,1445);self.assertLess(d.pulse,1505)
    def test_limit_finishes_instead_of_renewing_indefinitely(self):
        r,d=self.run_case([.94]*80)
        self.assertEqual(r['reason'],'FINITE_RANGE_REACHED');self.assertEqual(d.pulse,1505)
    def test_lost_face_during_motion_stops_without_rearm(self):
        r,d=self.run_case([.9]*10,lose=True)
        self.assertEqual(r['reason'],'SOURCE_NO_TARGET');self.assertGreater(len(d.commands),0)

if __name__=='__main__':unittest.main()
