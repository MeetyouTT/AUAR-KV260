from pathlib import Path
import json,sys,tempfile,threading,time
sys.path.insert(0,'/home/ghmd/Win共享文件/共享文件夹/aura')
from tools.board_avatar_gtk import load_gtk
from tools.board_camera_preview import CameraPreviewWorker
from tools.board_screen_capture import capture
from board.vision.local_preview import RawFrameStore
from PIL import Image
import gi
gi.require_version('GdkX11','3.0')
from gi.repository import GdkX11
Gtk,Gdk,Pixbuf,GLib=load_gtk()
assert Gtk.init_check([])[0]
output=Path('/home/ghmd/aura-board-ui-design-20261009/host-native-video');output.mkdir(exist_ok=True)
owner={'board_boot_id':'host-fixture','service_epoch':'host-fixture','camera_epoch':'f'*32}
class Services:
 def read(self):
  return {'snapshot':dict(owner,source_kind='fixture',modules={'camera':{'state':'READY'}},
     preview={'camera_epoch':owner['camera_epoch'],'frame_id':1,'captured_mono_ms':int(time.monotonic()*1000)}),
   'raw_preview':True,'preview':None}
with tempfile.TemporaryDirectory() as directory:
 store=RawFrameStore(owner,directory)
 worker=CameraPreviewWorker(Services(),raw_directory=directory)
 window=Gtk.Window();window.set_decorated(False)
 window.move(380,210)
 fixed=Gtk.Fixed();fixed.set_size_request(340,230);window.add(fixed)
 area=Gtk.DrawingArea();area.set_size_request(197,148);fixed.put(area,65,32)
 area.connect('realize',lambda w:worker.attach('main',GdkX11.X11Window.get_xid(w.get_window()),197,148))
 window.show_all()
 stop=threading.Event()
 def produce():
  fid=0
  while not stop.wait(.03):
   fid+=1;store.publish(fid,int(time.monotonic()*1000),bytes([30,40,220])*(640*480))
 thread=threading.Thread(target=produce);thread.start()
 try:
  end=time.monotonic()+4
  while time.monotonic()<end:
   while Gtk.events_pending():Gtk.main_iteration_do(False)
   if worker.read()['displayed_frames']>=3:break
   time.sleep(.01)
  before=worker.read();assert before['frame_visible'],before
  time.sleep(.4) # Deliberately do not iterate GTK; streaming must continue.
  after=worker.read();assert after['displayed_frames']>=before['displayed_frames']+4,(before,after)
  capture(output/'native-video.png')
  origin=area.get_window().get_origin();point=(origin[-2]+98,origin[-1]+74)
  image=Image.open(output/'native-video.png');color=image.getpixel(point)
  assert color[0]>180 and color[1]<80 and color[2]<80,(color,after)
  # A camera reconnect resets the pipeline; it must retain the same embedded XID.
  stop.set();thread.join();store.close()
  owner['camera_epoch']='e'*32;store=RawFrameStore(owner,directory)
  stop.clear();thread=threading.Thread(target=produce);thread.start()
  end=time.monotonic()+3
  while time.monotonic()<end:
   while Gtk.events_pending():Gtk.main_iteration_do(False)
   ref=worker.read()['frame_reference']
   if ref and ref['camera_epoch']==owner['camera_epoch']:break
   time.sleep(.01)
  assert ref and ref['camera_epoch']==owner['camera_epoch']
  time.sleep(.1);capture(output/'reconnected-video.png')
  rebound=Image.open(output/'reconnected-video.png').getpixel(point)
  assert rebound[0]>180 and rebound[1]<80 and rebound[2]<80,rebound
  stop.set();thread.join();time.sleep(.4)
  frozen=worker.read();assert not frozen['frame_visible'],frozen
  capture(output/'expired-video.png')
  dark=Image.open(output/'expired-video.png').getpixel(point)
  assert max(dark)<5,dark
  result={'scope':'HOST_SYNTHETIC_GSTREAMER_AND_RAM_TRANSPORT_NOT_CAMERA_ACCEPTANCE',
   'before_blocking_gtk':before,'after_blocking_gtk':after,'freeze_hidden':frozen,
   'embedded_pixel_position':point,'reconnect_pixel':rebound,'pixel':color,'cleared_pixel':dark}
  (output/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 finally:
  stop.set();thread.join();worker.close();store.close();window.destroy()
