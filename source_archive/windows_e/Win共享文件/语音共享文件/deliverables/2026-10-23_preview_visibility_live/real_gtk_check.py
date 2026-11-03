"""Synthetic off-screen X11 windows: real Gtk/Gst, no camera/audio/DPU inputs."""
import ast,base64,hashlib,json,os,sys,time,types
from pathlib import Path

BASE=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
sys.dont_write_bytecode=True;sys.path.insert(0,str(BASE/'aura'))
for item in Path('/proc/450593/environ').read_bytes().split(b'\0'):
    key,sep,value=item.partition(b'=')
    if sep and key in (b'DISPLAY',b'XAUTHORITY',b'GDK_BACKEND'):os.environ[key.decode()]=value.decode()
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0');gi.require_version('GdkX11','3.0')
from gi.repository import Gtk,Gdk,GdkX11,GLib
assert Gtk.init_check([])[0],'X11 not available for off-screen lifecycle test'
from board.vision.local_preview import RawFrameStore

raw={name:base64.b64decode(encoded) for name,encoded in CANDIDATE.items()}
preview=types.ModuleType('real_lifecycle_candidate');preview.__file__='candidate/board_camera_preview.py'
exec(compile(raw['tools/board_camera_preview.py'],preview.__file__,'exec'),preview.__dict__)
tree=ast.parse(raw['tools/board_avatar_gtk.py'])
stage=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BoardAvatarStage')
methods=[n for n in stage.body if isinstance(n,ast.FunctionDef) and n.name in ('attach_preview','detach_preview')]
namespace={};exec(compile(ast.fix_missing_locations(ast.Module(body=methods,type_ignores=[])),'actual-map-methods','exec'),namespace)
Stage=type('LifecycleStage',(),{name:namespace[name] for name in ('attach_preview','detach_preview')})

owner={'board_boot_id':'synthetic-lifecycle-only','service_epoch':'synthetic-private-epoch','camera_epoch':ROOT.name[:32]}
class Services:
    calls=0
    def read(self):
        self.calls+=1
        return {'snapshot':dict(owner,modules={'camera':{'state':'READY'}},preview={'camera_epoch':owner['camera_epoch']}),'raw_preview':True}

store=RawFrameStore(owner,ROOT);services=Services();worker=preview.CameraPreviewWorker(services,raw_directory=ROOT)
context=GLib.MainContext.default();windows=[];fid=0;last_published=0.
pixels=bytes((13,97,211))*(640*480)
s=Stage();s.GLib=GLib;s.Gdk=Gdk;s.preview_output=worker
def pump(seconds,feed=True):
    global fid,last_published
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if feed and time.monotonic()-last_published>=.08:
            fid+=1;store.publish(fid,int(time.monotonic()*1000),pixels);last_published=time.monotonic()
        for _ in range(30):
            if not context.pending():break
            context.iteration(False)
        time.sleep(.005)
def make(name,x):
    window=Gtk.Window(type=Gtk.WindowType.POPUP);window.set_accept_focus(False);window.move(x,-2000)
    area=Gtk.DrawingArea();area.set_size_request(64,48)
    area.connect('map',s.attach_preview,name,64,48);area.connect('unmap',s.detach_preview,name)
    window.add(area);windows.append(window);window.show_all();return window,area
def await_frames(name,minimum=1):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        pump(.08)
        row=worker.read(name)
        if row['displayed_frames']>=minimum and row['frame_visible']:
            assert not row['error'];return row
    raise AssertionError(('No live synthetic sink',name,worker.read(name)))
result={'scope':'REAL_GTK_GST_X11_SYNTHETIC_OFFSCREEN_NO_BUSINESS_INPUT',
        'candidate_pins':{name:hashlib.sha256(data).hexdigest() for name,data in raw.items()},'checks':[]}
try:
    vision,area=make('vision',-2000);first=await_frames('vision')
    xid=GdkX11.X11Window.get_xid(area.get_window());vision.hide();pump(.15)
    assert not worker.read('vision')['sink_active'];calls=services.calls;pump(.12)
    assert calls==services.calls,'Hidden output still reads services'
    result['checks'].append({'case':'real_unmap_stops_sink_and_reads','passed':True})
    vision.show_all();second=await_frames('vision')
    assert GdkX11.X11Window.get_xid(area.get_window())==xid
    result['checks'].append({'case':'same_xid_remap_receives_fresh_frame','passed':True,'frame_id':second['frame_reference']['frame_id']})
    large,other=make('large',-2100);await_frames('large');before=worker.read('large')['displayed_frames']
    vision.hide();pump(.25);after=worker.read('large')
    assert after['displayed_frames']>before and after['active_outputs']==['large']
    assert not worker.read('vision')['sink_active']
    result['checks'].append({'case':'large_continues_when_vision_unmaps','passed':True,'frames_added':after['displayed_frames']-before})
    large.hide();pump(.15);calls=services.calls;pump(.12)
    assert services.calls==calls and not worker.read('large')['active_outputs']
    result['checks'].append({'case':'all_outputs_hidden_no_service_reads','passed':True})
    for _ in range(4):
        vision.show_all();pump(.01);vision.hide();pump(.01)
    pump(.12);assert not worker.read('vision')['active_outputs']
    vision.show_all();await_frames('vision')
    result['checks'].append({'case':'rapid_map_generation_and_reopen','passed':True})
    result['passed']=True
finally:
    for window in windows:window.destroy()
    pump(.05,False);worker.close();store.close()
    result['worker_stopped']=not worker.thread.is_alive()
assert result['worker_stopped']
print(json.dumps(result))
