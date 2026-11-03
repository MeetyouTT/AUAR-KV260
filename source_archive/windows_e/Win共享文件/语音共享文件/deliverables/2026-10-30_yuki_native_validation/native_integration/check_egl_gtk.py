from pathlib import Path
import ctypes as C,json,os,subprocess,sys
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
for value in Path('/proc',pid,'environ').read_bytes().split(b'\0'):
    key,sep,data=value.partition(b'=')
    if sep and key in (b'DISPLAY',b'XAUTHORITY'):os.environ[key.decode()]=os.fsdecode(data)
sys.path.insert(0,str(root/'host'))
from egl_window import EGLWindow
import gi
gi.require_version('Gtk','3.0');gi.require_version('GdkX11','3.0')
from gi.repository import Gtk,GdkX11,GLib
assert Gtk.init_check([])[0]
window=Gtk.Window();window.set_decorated(False);window.set_accept_focus(False);window.set_skip_taskbar_hint(True)
window.set_default_size(64,64);window.set_opacity(0.0);window.move(-9000,-9000)
area=Gtk.DrawingArea();area.set_has_window(True);area.set_visual(area.get_screen().get_rgba_visual() or area.get_screen().get_system_visual())
result={'frames':0,'production_modified':False};contexts=[]
gl=C.CDLL('libGLESv2.so.2');gl.glGetString.argtypes=[C.c_uint];gl.glGetString.restype=C.c_char_p
gl.glClearColor.argtypes=[C.c_float]*4;gl.glClear.argtypes=[C.c_uint]
def realized(widget):
    try:
        parent=widget.get_window();assert parent.ensure_native();parent.get_display().sync()
        egl=EGLWindow(GdkX11.X11Window.get_xid(parent),64,64);contexts.append(egl)
        result.update(renderer=gl.glGetString(0x1F01).decode(),version=gl.glGetString(0x1F02).decode(),visual=egl.visual,config_bits=egl.config_bits)
    except Exception as error:result['error']=str(error)
def draw(widget,context):
    if contexts:
        contexts[0].current();gl.glClearColor(.2,.3,.4,1);gl.glClear(0x4000);contexts[0].swap();result['frames']+=1
    return True
area.connect('draw',draw);area.connect('realize',realized);window.add(area);window.show_all()
GLib.timeout_add(40,lambda:(area.queue_draw(),True)[1]);GLib.timeout_add(800,lambda:(Gtk.main_quit(),False)[1]);Gtk.main()
for egl in contexts:egl.close()
window.destroy();(root/'egl-gtk-probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
