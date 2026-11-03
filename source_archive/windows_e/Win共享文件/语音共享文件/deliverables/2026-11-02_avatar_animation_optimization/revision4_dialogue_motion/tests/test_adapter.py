import ctypes as C
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

HERE=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
new=module('r4_native',HERE/'candidate/runtime/tools/native_yuki.py')
old=module('r3_native',HERE/'baseline/runtime/tools/native_yuki.py')

class Output:
    active=False;paused=False
    def __init__(self):self.snapshot={'track':'none','ready':False,'audible':False,'done':False}
    def read(self):return dict(self.snapshot)

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.time=10.;self.output=Output();self.core=NS(talk_gen=1,emotion='neutral',fsm=NS(state=NS(label='IDLE')))
        self.new=new.LocalPortrait(self.output,clock=lambda:self.time,fps=16)
        self.old=old.LocalPortrait(self.output,clock=lambda:self.time,fps=16)
        self.new.ready=self.old.ready=True
    def offer(self,state='IDLE',*,waiting=False):
        self.core.fsm.state.label=state
        a=self.new.offer(self.core,self.time,.8,.7,round(self.time*24000),self.output.snapshot['track'],waiting_for_answer=waiting)
        b=self.old.offer(self.core,self.time,.8,.7,round(self.time*24000),self.output.snapshot['track'],waiting_for_answer=waiting)
        control=self.new.consume();before=self.old.consume()
        self.assertEqual(bytes(control.audio),bytes(before),'Original audio/eye/owner control changed')
        for key in ('mouth_level','speech_gain','eye_policy','answer_audible'):self.assertEqual(a[key],b[key])
        self.time+=.0625
        return a,control
    def test_layout(self):
        self.assertEqual([C.sizeof(x) for x in (new.Control,new.Stats,new.DialogueControl,new.MotionStats)],[64,96,88,80])
    def test_all_states_keep_audio_contract(self):
        for state in ('IDLE','PRESENT','AWAKE','LISTENING','THINKING','SPEAKING','SPEAKING_NEUTRAL','SPEAKING_LOW',
                      'ACK_NOD','DENY_SHAKE','PUZZLED','CAMERA_LOST','NETWORK_LOST','CANCELLED','ERROR','UNKNOWN'):
            meta,c=self.offer(state)
            self.assertIn(meta['motion_state'],new.MOTION_STATES)
        self.offer('THINKING',waiting=True)
    def test_real_answer_and_gap_posture(self):
        self.output.active=True;self.output.snapshot.update(track='answer',ready=True,audible=True,answer_started_at=9.)
        for emotion,name in [('neutral','SPEAKING_NEUTRAL'),('friendly','SPEAKING_NEUTRAL'),('happy','SPEAKING'),('sad','SPEAKING_LOW')]:
            self.core.emotion=emotion
            meta,c=self.offer('SPEAKING',waiting=True)
            self.assertEqual(meta['motion_state'],name);self.assertTrue(c.audio.playing)
        self.output.snapshot['audible']=False
        meta,c=self.offer('SPEAKING',waiting=True)
        self.assertEqual(meta['motion_state'],'SPEAKING_LOW');self.assertEqual(c.audio.playing,0);self.assertEqual(c.audio.gain,0)
    def test_feedback_never_answer_motion_or_mouth(self):
        self.output.active=True;self.output.snapshot.update(track='feedback',ready=True,audible=True)
        meta,c=self.offer('SPEAKING',waiting=True)
        self.assertEqual(meta['motion_state'],'THINKING');self.assertFalse(c.audio.playing);self.assertEqual(c.audio.level,0)
    def test_one_shot_not_restarted_by_latest_mailbox(self):
        meta,c=self.offer('ACK_NOD');token=c.action_token
        for _ in range(8):
            meta,c=self.offer('ACK_NOD');self.assertEqual(c.action_token,token);self.assertFalse(meta['_portrait_burst'])
        self.new.latest_stats={'motion_generation':1,'motion_completed_token':token}
        meta,c=self.offer('ACK_NOD');self.assertTrue(meta['_portrait_burst'])
        meta,c=self.offer('ACK_NOD');self.assertFalse(meta['_portrait_burst'])
    def test_hidden_reaction_keeps_business_fallback(self):
        self.offer('AWAKE');self.time+=.81
        meta,c=self.offer('AWAKE');self.assertTrue(meta['_portrait_burst'])
    def test_pause_cancel_generation_and_old_offer(self):
        self.offer('DENY_SHAKE');self.output.paused=True
        meta,c=self.offer('DENY_SHAKE');self.assertEqual(c.action,0);self.assertEqual(meta['motion_state'],'PAUSED')
        self.output.paused=False;self.core.talk_gen=2
        meta,c=self.offer('LISTENING');self.assertEqual(c.action_token,0)
        self.new.invalidate();self.old.invalidate()
        self.assertEqual(self.new.consume().state,new.MOTION_STATE['CANCELLED']);self.old.consume()
        self.core.talk_gen=1
        self.new.offer(self.core,self.time,0,0,0,'none')
        self.core.talk_gen=0
        self.assertIsNone(self.new.offer(self.core,self.time,0,0,0,'none'))

if __name__=='__main__':unittest.main(verbosity=2)
