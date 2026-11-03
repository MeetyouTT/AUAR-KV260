import unittest
from direction_bench import DirectionBench
def view(fid,t,x=280,epoch='cam',tid=1):
 face={'epoch':epoch,'frame_id':fid,'observed_time':t,'track_id':tid,'generation':1,'visible':True,'confirmed':True,'consecutive':8,'box':[x,100,80,80],'score':.99}
 return {'boot_id':'boot','epoch':epoch,'mirror_horizontal':True,'capture_size':[640,480],'error':None,'stopped':False,'snapshot':{'epoch':epoch,'frame_id':fid,'observed_time':t,'target_id':tid,'tracks':[face]}}
class BenchTests(unittest.TestCase):
 def exercise(self,x):
  c=DirectionBench('boot','cam');r=None
  for fid in range(1,101):
   t=1+fid*.1;r=c.observe(view(fid,t,x),t+.02)
   self.assertEqual(r['kind'],'COMMAND');self.assertLessEqual(abs(r['target_us']-c.accepted),4);c.accept(r['target_us'])
  return c,r
 def test_left_increases_right_decreases_and_stays_bounded(self):
  for x,pulse,direction in [(120,1520,'COUNTERCLOCKWISE'),(440,1480,'CLOCKWISE'),(280,1500,'CENTER')]:
   c,r=self.exercise(x);self.assertEqual(c.accepted,pulse);self.assertEqual(r['desired_direction'],direction)
 def test_no_accumulation_for_stationary_independent_camera(self):
  c,r=self.exercise(360);self.assertEqual(c.accepted,1490)
 def test_stale_duplicate_loss_and_context(self):
  c=DirectionBench('boot','cam');r=c.observe(view(1,1),1.02);c.accept(r['target_us'])
  self.assertEqual(c.observe(view(1,1),1.04)['reason'],'NO_NEW_FRAME')
  self.assertEqual(c.observe(view(2,1),1.05)['reason'],'FROZEN_SOURCE_TIME')
  self.assertEqual(c.observe(view(2,1.1),1.4)['kind'],'STOP')
  self.assertEqual(c.observe(view(2,1.1,epoch='other'),1.12)['kind'],'STOP')
  s=view(2,1.1);s['snapshot']['tracks']=[];self.assertEqual(c.observe(s,1.12)['kind'],'STOP')
 def test_target_switch_stops(self):
  c=DirectionBench('boot','cam');c.observe(view(1,1),1.02)
  self.assertEqual(c.observe(view(2,1.1,tid=2),1.12)['reason'],'TARGET_CHANGED')
if __name__=='__main__':unittest.main()
