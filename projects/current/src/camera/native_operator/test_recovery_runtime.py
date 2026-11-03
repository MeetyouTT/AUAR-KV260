import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import identity_recovery as m

class RuntimeTests(unittest.TestCase):
    def test_realtime_scopes_current_thread_and_restores_after_success_and_error(self):
        for fail in (False,True):
            calls=[]
            def work(*args):
                calls.append(('C',args))
                if fail:raise ValueError('native exception')
                return 17
            with patch.object(m.os,'sched_getscheduler',return_value=0),patch.object(m.os,'sched_getparam',return_value='prior'),patch.object(m.os,'sched_setscheduler',side_effect=lambda *a:calls.append(a)):
                if fail:
                    with self.assertRaises(ValueError):m.RealtimeCall(work)(3,4)
                else:self.assertEqual(m.RealtimeCall(work)(3,4),17)
            self.assertEqual(calls[0][:2],(0,m.os.SCHED_FIFO));self.assertEqual(calls[0][2].sched_priority,10)
            self.assertEqual(calls[1],('C',(3,4)));self.assertEqual(calls[-1],(0,0,'prior'))
    def test_permission_failure_never_invokes_model(self):
        touched=[]
        with patch.object(m.os,'sched_getscheduler',return_value=0),patch.object(m.os,'sched_getparam'),patch.object(m.os,'sched_setscheduler',side_effect=PermissionError):
            with self.assertRaises(PermissionError):m.RealtimeCall(lambda:touched.append(True))()
        self.assertEqual(touched,[])
    def test_audit_atomic_replacement_does_not_leave_partial_files(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'audit.json';m.atomic(p,{'counter':3});m.atomic(p,{'counter':4})
            self.assertEqual(m.json.loads(p.read_text()),{'counter':4});self.assertEqual(list(Path(t).iterdir()),[p])

if __name__=='__main__':unittest.main()
