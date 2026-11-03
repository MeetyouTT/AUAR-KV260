"""Fake-clock boundedness checks, not USB/GStreamer native health evidence."""
import sys,unittest
from pathlib import Path

MATCHED_TREE=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
sys.path.insert(0,str(MATCHED_TREE))
import tests.framework.test_persistent_audio as audio_fixtures


class AudioReviewTests(unittest.TestCase):
    def setUp(self):
        self.fx=audio_fixtures.PersistentTests();self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)

    def test_idle_python_queues_stay_bounded_during_a_minute(self):
        f=self.fx;f.advance(60)
        self.assertFalse(f.engine.active)
        self.assertFalse(f.engine.queue);self.assertFalse(f.engine.intervals)
        self.assertLessEqual(len(f.engine.references),16)
        self.assertEqual(f.engine.snapshot()['device_state'],'IDLE_READY')
        self.assertEqual(f.opens,1)

    def test_large_idle_clock_step_has_bounded_catchup_and_monotonic_pts(self):
        f=self.fx;before=len(f.pushes);last_pts=f.pushes[-1].pts
        f.now+=24*3600*1_000_000_000;f.sink_time=f.now;f.engine.poll()
        added=f.pushes[before:]
        self.assertGreater(len(added),0);self.assertLessEqual(len(added),8)
        self.assertGreater(added[0].pts,last_pts)
        self.assertTrue(all(p.duration==20_000_000 for p in added))
        self.assertGreater(f.engine.next_pts,2**32)
        self.assertFalse(f.engine.queue);self.assertFalse(f.engine.intervals)

    def test_sink_stall_without_error_is_not_an_external_usb_health_check(self):
        f=self.fx;before=len(f.pushes);sink=f.sink_time
        for _ in range(100):
            f.now+=10_000_000;f.sink_time=sink;f.engine.poll()
        self.assertGreater(len(f.pushes),before)
        self.assertEqual(f.engine.snapshot()['device_state'],'IDLE_READY')
        self.assertEqual(f.engine.error,'')
        # This verifies an existing reporting limitation, not a cause of HC
        # memory-access errors or proof that a real sink has stalled.


if __name__=='__main__':unittest.main()
