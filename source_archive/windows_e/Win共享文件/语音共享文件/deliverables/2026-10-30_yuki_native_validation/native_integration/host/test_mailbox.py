"""Meaningful cancellation/ownership tests; no board, GL, model or audio needed."""
import unittest
from types import SimpleNamespace as S
from native_yuki import LocalPortrait

class MailboxTest(unittest.TestCase):
    def setUp(self):
        self.at=10.;self.output=S(active=True,ready=True,paused=False)
        self.core=S(talk_gen=1,emotion='neutral',fsm=S(state=S(label='SPEAKING')))
        self.box=LocalPortrait(self.output,clock=lambda:self.at);self.box.ready=True
    def offer(self,sample=100,track='answer',level=.8):return self.box.offer(self.core,1.,1.,level,sample,track)
    def test_latest_one_not_unbounded_queue(self):
        for i in range(1000):self.offer(i)
        self.assertEqual(self.box.consume().audio_sample,999);self.assertIsNone(self.box.consume())
        self.assertEqual(self.box.dropped,999)
    def test_cancel_supersedes_pending_audio(self):
        self.offer();previous=self.box.owner;self.box.invalidate();value=self.box.consume()
        self.assertGreater(value.owner,previous);self.assertEqual(value.playing,0);self.assertEqual(value.level,0)
    def test_late_old_turn_does_not_replace_new_turn(self):
        self.core.talk_gen=2;self.offer(20);owner=self.box.owner
        self.core.talk_gen=1;self.assertIsNone(self.offer(500))
        value=self.box.consume();self.assertEqual(value.audio_sample,20);self.assertEqual(value.owner,owner)
    def test_pause_and_resume_use_existing_output_clock(self):
        self.output.paused=True;self.offer(200);value=self.box.consume()
        self.assertEqual(value.audio_sample,200);self.assertFalse(value.playing);self.assertTrue(value.paused)
        self.output.paused=False;self.offer(200);self.assertTrue(self.box.consume().playing)
    def test_track_change_opens_new_sample_owner(self):
        self.offer(10000,'feedback');old=self.box.owner;self.offer(0,'answer')
        self.assertGreater(self.box.owner,old);self.assertEqual(self.box.consume().audio_sample,0)
    def test_model_failure_falls_back_without_io(self):
        self.offer();self.box.fail('GPU context lost');self.assertIsNone(self.offer())
        self.assertEqual(self.box.status()['mode'],'local')
    def test_six_faces_and_two_poses(self):
        for index,name in enumerate(self.box.FACE):
            self.box.set_expression(name);self.offer();self.assertEqual(self.box.consume().expression,index)
        self.box.set_pose(1);self.offer();self.assertEqual(self.box.consume().pose,1)
    def test_invalid_clock_is_not_forwarded(self):
        with self.assertRaises(ValueError):self.offer(-1)
        with self.assertRaises(ValueError):self.offer(level=float('nan'))

if __name__=='__main__':unittest.main()
