import importlib.util,sys,time,types,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
HERE=Path(__file__).resolve().parent

class RateTests(unittest.TestCase):
 def test_audio_completion_is_processed_without_visual_render(self):
  sys.path.insert(0,str(HERE.parents[1]/'aura'))
  spec=importlib.util.spec_from_file_location('tools.stable_realtime',HERE/'stable_fps_sources/realtime_controller.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  ctrl=m.RealtimeController.__new__(m.RealtimeController);ctrl.pending=ctrl.ready=None;ctrl.render_requested=False;ctrl.last_meta={'sentinel':True};ctrl.phase='SPEAKING';events=[]
  ctrl.output=types.SimpleNamespace(position=lambda:1.,finished=lambda:True)
  ctrl.facials=types.SimpleNamespace(stop=lambda now:events.append('facials_stopped'));ctrl.now=lambda:1.;ctrl.observe_audio_start=lambda:None;ctrl.send=lambda event:events.append(event);ctrl.record=lambda *args,**kwargs:None
  self.assertEqual(ctrl.tick(),{'sentinel':True});self.assertEqual(ctrl.phase,'IDLE');self.assertEqual(len(events),2)
 def test_stream_controls_progress_without_visual_render(self):
  sys.path.insert(0,str(HERE.parents[1]/'aura'))
  spec=importlib.util.spec_from_file_location('tools.stable_streaming',HERE/'stable_fps_sources/streaming_controller.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  ctrl=m.StreamingController.__new__(m.StreamingController);ctrl.render_requested=False;ctrl.last_meta={'sentinel':True};ctrl.core=types.SimpleNamespace(emotion='neutral')
  ctrl.stream={'hint':False,'response_applied':False,'controls':[{'at_sample':0,'emotion':'happy'}],'audio_done':False,'network':None}
  ctrl.output=types.SimpleNamespace(read=lambda:{'audible':False},position=lambda:0.,finished=lambda:False)
  self.assertEqual(ctrl.tick(),{'sentinel':True});self.assertEqual(ctrl.core.emotion,'happy');self.assertEqual(ctrl.stream['controls'],[])
 def test_control_runs_between_unique_visual_frames(self):
  spec=importlib.util.spec_from_file_location('stable_worker',HERE/'stable_fps_sources/board_avatar_worker.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  class Controller:
   ticks=0;renders=0;last_error='';last=None
   def tick(self):
    self.ticks+=1
    if self.render_requested:
     self.renders+=1;self.last={'image':Image.new('RGB',(1,1),(self.renders,0,0))}
    return self.last
   def public(self):return {'phase':'IDLE','error':self.last_error}
   def close(self):pass
  class Sink:
   def __init__(self):self.rows=[]
   def push(self,rgb,sequence):self.rows.append((time.monotonic(),rgb,sequence))
  fake=types.ModuleType('tools.board_avatar_affine');fake.resize_rgb=lambda image,size:image.tobytes()
  ctrl=Controller();sink=Sink()
  with patch.dict(sys.modules,{'tools.board_avatar_affine':fake}):
   worker=m.AvatarRenderWorker(ctrl,'white',(1,1),1/24,native_video=sink,visual_fps=10)
   time.sleep(1.3);worker.close()
  self.assertFalse(ctrl.last_error);self.assertGreaterEqual(len(sink.rows),8);self.assertLessEqual(len(sink.rows),15)
  self.assertGreaterEqual(ctrl.ticks,2*len(sink.rows))
  self.assertIn(ctrl.renders-len(sink.rows),(0,1));self.assertEqual(len({r[1] for r in sink.rows}),len(sink.rows))
  self.assertEqual([r[2] for r in sink.rows],list(range(1,len(sink.rows)+1)))

 def test_presenter_removes_render_jitter_and_discards_cancelled_pixels(self):
  import threading
  spec=importlib.util.spec_from_file_location('paced_worker',HERE/'stable_fps_sources/board_avatar_worker.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  class Sink:
   def __init__(self):self.rows=[]
   def push(self,rgb,sequence):self.rows.append((time.monotonic(),rgb,sequence))
  sink=Sink();generation=[0];guard=threading.Condition();presenter=m.FramePresenter(sink,lambda:generation[0],guard)
  start=time.monotonic()+.02
  for i,delay in enumerate((.002,.065,.012,.055,.005,.070,.025,.040)):
   slot=start+i*.125
   time.sleep(max(0,slot+delay-time.monotonic()))
   presenter.offer(bytes([i]),i,0,slot+.085)
  time.sleep(.11)
  self.assertEqual(len(sink.rows),8)
  self.assertLess(max(abs((b[0]-a[0])-.125) for a,b in zip(sink.rows,sink.rows[1:])),.025)
  presenter.offer(b'old',9,0,time.monotonic()+.06)
  with guard:generation[0]=1
  time.sleep(.09);presenter.close()
  self.assertEqual(len(sink.rows),8);self.assertEqual(presenter.read()['dropped'],1)

if __name__=='__main__':unittest.main()
