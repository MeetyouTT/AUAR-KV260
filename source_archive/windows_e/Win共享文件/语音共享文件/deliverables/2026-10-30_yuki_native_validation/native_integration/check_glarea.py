"""Create a transparent test window only; never changes the running stage."""
from pathlib import Path
import json,os,subprocess
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
for value in Path('/proc',pid,'environ').read_bytes().split(b'\0'):
    key,sep,data=value.partition(b'=')
    if sep and key in (b'DISPLAY',b'XAUTHORITY'):os.environ[key.decode()]=os.fsdecode(data)
os.environ['GDK_GL']='gles'
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
assert Gtk.init_check([])[0]
window=Gtk.Window();window.set_decorated(False);window.set_accept_focus(False);window.set_skip_taskbar_hint(True)
window.set_default_size(64,64);window.set_opacity(0.0);window.move(-9000,-9000)
area=Gtk.GLArea();area.set_use_es(True);area.set_required_version(2,0);area.set_has_depth_buffer(False)
result={'frames':0,'production_modified':False}
def render(widget,context):
    result['frames']+=1;result['context_use_es']=bool(context.get_use_es());return True
def realized(widget):
    widget.make_current();error=widget.get_error();result['error']=str(error) if error else None
area.connect('render',render);area.connect('realize',realized);window.add(area);window.show_all()
GLib.timeout_add(800,lambda:(Gtk.main_quit(),False)[1]);Gtk.main();window.destroy()
out=Path('/home/root/aura-yuki-validation-20261030/native_integration/glarea-probe.json');out.write_text(json.dumps(result,indent=2))
print(json.dumps(result))
