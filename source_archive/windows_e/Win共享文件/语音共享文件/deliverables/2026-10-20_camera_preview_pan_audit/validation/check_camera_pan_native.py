"""GTK/GStreamer integration with synthetic pixels and fake pan hardware."""
import argparse,ast,importlib.util,json,sys,tempfile,threading,time,uuid
from pathlib import Path
from types import SimpleNamespace
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk,GLib

parser=argparse.ArgumentParser()
parser.add_argument('--gui',required=True);parser.add_argument('--out',required=True)
args=parser.parse_args()
AURA=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
sys.path[:0]=[str(AURA),str(AURA/'tests/framework')]
from board.vision.local_preview import RawFrameStore
from tools.board_camera_preview import CameraPreviewWorker
from tools.board_screen_capture import capture
from tools.pan_controls import stage_type
from board.motion.manual import ManualPan
from test_manual_pan import Hardware
from PIL import Image

spec=importlib.util.spec_from_file_location('live_gui',args.gui)
gui=importlib.util.module_from_spec(spec);spec.loader.exec_module(gui)
tree=ast.parse(Path(args.gui).read_text())
refresh=next(x for c in tree.body if isinstance(c,ast.ClassDef) for x in c.body if isinstance(x,ast.FunctionDef) and x.name=='refresh_runtime')
visibility=next(x for x in refresh.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call)
                and isinstance(x.value.func,ast.Attribute) and x.value.func.attr=='set_visible'
                and isinstance(x.value.func.value,ast.Attribute) and x.value.func.value.attr=='preview_image')
visibility_code=compile(ast.fix_missing_locations(ast.Module(body=[visibility],type_ignores=[])),'production-visibility','exec')
owner={'board_boot_id':str(uuid.uuid4()),'service_epoch':uuid.uuid4().hex,'camera_epoch':uuid.uuid4().hex}
services=SimpleNamespace(read=lambda:{'snapshot':dict(owner,modules={'camera':{'state':'READY'}},preview={'camera_epoch':owner['camera_epoch']}),'raw_preview':True})
running=threading.Event();running.set();stopped=threading.Event();publisher_errors=[]
temporary=tempfile.TemporaryDirectory();store=RawFrameStore(owner,temporary.name)
pixels=bytes((20,40,210))*(640*480)
def publish():
 try:
  fid=0
  while not stopped.wait(.08):
   if running.is_set():fid+=1;store.publish(fid,int(time.monotonic()*1000),pixels)
 except BaseException as exc:publisher_errors.append(repr(exc))
producer=threading.Thread(target=publish,daemon=True);producer.start()

class Preview(CameraPreviewWorker):
 def __init__(self,*a,**kw):self.attaches=[];super().__init__(*a,**kw)
 def attach(self,name,handle,width,height):
  self.attaches.append((name,handle));return super().attach(name,handle,width,height)

class Base:
 def __init__(self):
  self.Gtk,self.Gdk,self.GLib=Gtk,Gdk,GLib
  self.geometry={'x':593,'y':32,'w':423,'h':516}
  self.window=Gtk.Window();self.window.set_default_size(1024,600)
  self.bridge=SimpleNamespace(allowed_commands=set());self.controls={};self.page='main'
  self.preview_output=Preview(services,raw_directory=temporary.name)
  self.build_window(False)
 def build_window(self,windowed):
  self.fixed=Gtk.Fixed();self.fixed.set_size_request(1024,600);self.window.add(self.fixed)
  self.pages=Gtk.Stack();self.pages.set_size_request(569,432);self.fixed.put(self.pages,8,112)
  self.pages.add_named(Gtk.Label(label='main'),'main')
  vision=Gtk.Fixed();self.pages.add_named(vision,'vision')
  card=Gtk.EventBox();card.set_size_request(569,300);overlay=Gtk.Overlay();card.add(overlay)
  self.preview_image=Gtk.DrawingArea();self.preview_image.set_size_request(400,300);self.preview_image.set_halign(Gtk.Align.CENTER)
  self.preview_image.connect('map',self.attach_preview,'vision',400,300);overlay.add(self.preview_image);vision.put(card,0,0)
  b=Gtk.Button(label='设置');b.set_size_request(132,56);vision.put(b,435,376)
  b.connect('clicked',self.activated,{'type':'ui_page'},'vision_settings');self.controls['vision_settings']=b
  self.vision_insights=Gtk.Label(label='insights');self.fixed.put(self.vision_insights,593,32)
  self.avatar_title=Gtk.Label(label='视觉解读');self.fixed.put(self.avatar_title,593,4)
  self.window.show_all();self.show_page('vision')
 attach_preview=gui.BoardAvatarStage.attach_preview
 def show_page(self,page):
  self.page=page;self.pages.set_visible_child_name(page);self.vision_insights.set_visible(page=='vision')
 def activated(self,widget,data,key):return self.native(data)
 def native(self,data):return self.command(data)
 def command(self,data):
  if data['type']=='ui_page':self.show_page(data['page'])
  return {'ok':True}
 def refresh_runtime(self,state,settings_text):pass
 def observe_touch(self,*args):return False
 def cleanup(self):self.preview_output.close();self.window.destroy()

out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
h=Hardware();pan=ManualPan(lambda:h,duration_s=.16)
s=stage_type(Base,lambda:pan)();checks=[]
def spin(seconds):
 until=time.monotonic()+seconds
 while time.monotonic()<until:
  while Gtk.events_pending():Gtk.main_iteration_do(False)
  image=s.preview_output.read('vision')['frame_visible']
  exec(visibility_code,{'self':s,'image':image})
  time.sleep(.005)
def actual_pixel(name,red=True):
 path=out/(name+'.png');capture(path)
 with Image.open(str(path)) as im:rgb=im.getpixel((290,260))
 assert (rgb[0]>150 and rgb[1]<80 and rgb[2]<80) if red else max(rgb)<8,(name,rgb,s.preview_output.read('vision'))
 checks.append({'name':name,'pixel':rgb,'preview':s.preview_output.read('vision')})
try:
 spin(1.3);actual_pixel('initial')
 running.clear();spin(.5)
 assert not s.preview_output.read('vision')['frame_visible']
 assert s.preview_image.get_mapped(),'stale frame unmapped the native camera canvas'
 actual_pixel('expired-cleared',red=False)
 running.set();spin(.6);actual_pixel('source-recovered')
 for i in range(5):
  s.show_page('main');spin(.15);s.show_page('vision');spin(.35);actual_pixel('remap-'+str(i))
 assert len(s.preview_output.attaches)>=6,s.preview_output.attaches
 for i in range(3):
  s.open_pan_dialog();spin(.35);actual_pixel('pan-open-'+str(i))
  r=s.pan_dialog.get_allocation();xy=s.pan_dialog.translate_coordinates(s.fixed,0,0)
  assert r.width<=423 and r.height<=516,(r.width,r.height)
  assert xy[-2]>=593 and xy[-2]+r.width<=1024,xy
  assert not any(isinstance(w,Gtk.Dialog) and w.get_visible() for w in Gtk.Window.list_toplevels())
  for k,w in s.controls.items():
   if w.get_mapped():assert w.translate_coordinates(s.fixed,0,0) is not None,k
  assert all(b.get_allocated_width()>=110 and b.get_allocated_height()>=48 for b in s.pan_buttons.values())
  if i==0:
   s.pan_buttons['left'].clicked();spin(.35);assert pan.read()['pulse_us']==1410
   s.pan_step.set_active_id('5');s.pan_buttons['right'].clicked();spin(.35);assert pan.read()['pulse_us']==1415
   s.pan_reverse.set_active(True);spin(.1);assert pan.read()['left_sign']==1
  s.close_pan_dialog();spin(.15);assert not any(k in s.controls for k in ('pan_left','pan_stop','pan_right'))
  actual_pixel('pan-closed-'+str(i))
 s.open_pan_dialog();spin(.15);s.show_page('main');spin(.2);assert s.pan_dialog is None
 assert not publisher_errors,publisher_errors
 report={'status':'NATIVE_GTK_SYNTHETIC_PASS','real_hardware':False,'checks':checks,'native_binds':s.preview_output.attaches,'panel_max':[423,516],'stale_deadline_ms':250,'pan_pulse':pan.read()['pulse_us']}
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
finally:
 s.cleanup();stopped.set();producer.join(timeout=1);store.close();temporary.cleanup()
