"""Real GTK layout and button smoke test with fake hardware, under Xvfb."""
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import gi
gi.require_version('Gtk','3.0')
gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk,GLib

AURA=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
sys.path.insert(0,str(AURA));sys.path.insert(0,str(AURA/'tests/framework'))
from board.motion.manual import ManualPan
from test_manual_pan import Hardware
from tools.pan_controls import stage_type

class Base:
 def __init__(self):
  self.Gtk,self.Gdk,self.GLib=Gtk,Gdk,GLib
  self.window=Gtk.Window();self.window.set_default_size(1024,600)
  self.bridge=SimpleNamespace(allowed_commands=set());self.controls={};self.results=[]
  self.build_window(False)
 def build_window(self,windowed):
  box=Gtk.Fixed();self.window.add(box)
  b=Gtk.Button(label='设置');b.set_size_request(132,56)
  b.connect('clicked',self.activated,{'type':'ui_page'},'vision_settings')
  box.put(b,440,488);self.controls['vision_settings']=b;self.window.show_all()
 def activated(self,widget,data,key):
  self.results.append(self.command(data))
 def native(self,data):
  try:return self.command(data)
  except Exception as exc:return {'ok':False,'error':str(exc)}
 def command(self,data):return {'ok':True}
 def refresh_runtime(self,state,settings_text):pass
 def observe_touch(self,*args):return False
 def cleanup(self):self.window.destroy()

def spin(predicate,timeout=2):
 end=time.monotonic()+timeout
 while not predicate():
  while Gtk.events_pending():Gtk.main_iteration_do(False)
  if time.monotonic()>end:raise AssertionError('GTK smoke timeout')
  time.sleep(.005)
 for _ in range(5):
  while Gtk.events_pending():Gtk.main_iteration_do(False)
  time.sleep(.005)

h=Hardware();pan=ManualPan(lambda:h,duration_s=.16)
s=stage_type(Base,lambda:pan)()
try:
 spin(lambda:pan.read()['state']=='READY')
 assert s.controls['pan_open'].get_label()=='转轴调节'
 s.controls['pan_open'].clicked();spin(lambda:s.pan_dialog is not None)
 def click(direction,expected):
  s.refresh_pan_dialog();s.pan_buttons[direction].clicked()
  spin(lambda:pan.read()['state']=='READY')
  assert pan.read()['pulse_us']==expected,(direction,pan.read())
 click('left',1410);click('right',1430)
 s.pan_step.set_active_id('5');click('left',1425);click('right',1430)
 s.pan_reverse.set_active(True);spin(lambda:pan.read()['left_sign']==1)
 click('left',1435);click('right',1430)
 s.pan_reverse.set_active(False);spin(lambda:pan.read()['left_sign']==-1)
 s.refresh_pan_dialog();assert s.pan_buttons['stop'].get_sensitive()
 s.pan_buttons['right'].clicked();spin(lambda:pan.read()['state']=='MOVING')
 s.pan_buttons['stop'].clicked();spin(lambda:pan.read()['state']=='READY')
 s.refresh_pan_dialog();spin(lambda:s.pan_dialog.get_window() is not None)
 allocation=s.pan_dialog.get_allocation();assert allocation.width<=1024 and allocation.height<=600
 sizes={k:[b.get_allocated_width(),b.get_allocated_height()] for k,b in s.pan_buttons.items()}
 assert all(w>=150 and h>=48 for w,h in sizes.values())
 out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
 pix=Gdk.pixbuf_get_from_window(s.pan_dialog.get_window(),0,0,allocation.width,allocation.height)
 pix.savev(str(out/'host-manual-dialog.png'),'png',[],[])
 result={'status':'GTK_FAKE_HARDWARE_PASS','actuation':False,'dialog_size':[allocation.width,allocation.height],
         'button_sizes':sizes,'left_right_coarse_fine_swap_stop':True,'original_settings_button_repurposed':True}
 (out/'host-gtk-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 s.close_pan_dialog();assert s.pan_dialog is None
finally:s.cleanup()
