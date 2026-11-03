"""Independent source-selection, padding, alpha and metadata checks. No GI/board."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

HERE=Path(__file__).resolve().parent
GTK=HERE.parent/'gtk'
original=(GTK/'original/tools/board_camera_preview.py').read_bytes()
candidate=(GTK/'candidate/tools/board_camera_preview.py').read_bytes()
assert hashlib.sha256(original).hexdigest()=='6e697c16f7ae264dff56b6b35f38da4b531ea13026b69a7c8bdbfb1960a6afcd'
assert hashlib.sha256(candidate).hexdigest()=='022098636a41b35bc17929da1cbef0f05e5c257640f9b64a8504c1b4a13e7127'
old=b'videoconvert ! videoscale ! video/x-raw,width='
new=b'videoscale ! videoconvert ! video/x-raw,width='
assert original.count(old)==1 and candidate==original.replace(old,new)
checks=['production is exactly the one reviewed chain substitution']

class Captured(Exception):pass
def description(source,width,height):
    tree=ast.parse(source)
    klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CameraPreviewWorker')
    function=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='attach')
    namespace={}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'<isolated-attach>','exec'),namespace)
    recorded=[]
    def capture(value):recorded.append(value);raise Captured()
    self=NS(detach=lambda name:None,Gst=NS(parse_launch=capture))
    try:namespace['attach'](self,'test',123,width,height)
    except Captured:pass
    assert len(recorded)==1
    return recorded[0]
for width,height in ((568,300),(587,440),(640,480)):
    a,b=description(original,width,height),description(candidate,width,height)
    assert a.replace('videoconvert ! videoscale','videoscale ! videoconvert')==b
    assert 'format=BGR,width=640,height=480,framerate=0/1' in b
    assert 'max-size-buffers=1' in b and 'leaky=downstream' in b
    assert 'video/x-raw,width='+str(width)+',height='+str(height) in b
checks.append('actual candidate attach builds the selected chain at all three sizes')

hardened=(HERE/'gst_synthetic_compare_hardened.py').read_text(encoding='utf-8')
tree=ast.parse(hardened)
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('packed','error','compare','push')]
namespace={}
exec(compile(ast.Module(body=functions,type_ignores=[]),'<pure-gst-metadata-functions>','exec'),namespace)
class Caps:
    def to_string(self):return 'video/x-raw,format=BGR,width=2,height=2'
info=NS(finfo=NS(name='BGR',format=7),width=2,height=2,stride=[8],offset=[0],size=16)
meta=NS(n_planes=1,width=2,height=2,format=7,stride=[12],offset=[4])
class Buffer:
    offset=101
    pts=202
    def __init__(self,pixels):self.pixels=pixels;self.unmapped=False
    def map(self,flags):return True,NS(data=self.pixels)
    def unmap(self,mapping):self.unmapped=True
buffer=Buffer(b'xxxx'+bytes(range(1,7))+b'pppppp'+bytes(range(7,13)))
sample=NS(get_caps=lambda:Caps(),get_buffer=lambda:buffer)
namespace.update(Gst=NS(MapFlags=NS(READ=1)),GstVideo=NS(VideoInfo=NS(new_from_caps=lambda caps:info),buffer_get_video_meta=lambda value:meta))
packed=namespace['packed'](sample)
assert packed['data']==bytes(range(1,13)) and packed['row_stride']==12 and packed['plane_offset']==4 and buffer.unmapped
checks.append('VideoMeta stride and nonzero plane offset override caps defaults')
meta.stride=[-12]
try:namespace['packed'](sample);raise RuntimeError('Negative stride was accepted')
except AssertionError:pass
meta.stride=[12]
checks.append('unvalidated negative stride is rejected')

def image(fmt,data):return dict(width=2,height=2,format=fmt,bpp=4,data=data,offset=1,pts=1)
left=bytes((1,2,3,0))*4;right=bytes((1,2,3,255))*4
result=namespace['compare'](image('BGRx',left),image('BGRx',right))
assert result['visible']['maximum']==0 and result['x_padding_equal'] is False and result['top_bottom_rows']['maximum']==0
checks.append('undefined X padding differences do not fail visible pixels')
result=namespace['compare'](image('BGRA',left),image('BGRA',right))
assert result['visible']['maximum']==0 and result['alpha']['maximum']==255
checks.append('BGRA alpha changes remain a strict failure')

class Allocated:
    def fill(self,*args):pass
    offset=0
    pts=0
namespace.update(Gst=NS(Buffer=NS(new_allocate=lambda *args:Allocated()),FlowReturn=NS(OK=1),MSECOND=1000,SECOND=1000000),
    DEADLINE=100,time=NS(monotonic=lambda:1))
source=NS(emit=lambda *args:1)
good=NS(get_buffer=lambda:NS(offset=7,pts=7000))
bad=NS(get_buffer=lambda:NS(offset=6,pts=6000))
assert namespace['push'](source,NS(emit=lambda *args:good),b'abc',7) is good
try:namespace['push'](source,NS(emit=lambda *args:bad),b'abc',7);raise RuntimeError('Stale frame was accepted')
except AssertionError:pass
checks.append('performance push rejects a stale or wrong frame sample')
namespace['DEADLINE']=.5
try:namespace['push'](source,NS(emit=lambda *args:good),b'abc',7);raise RuntimeError('Expired deadline was accepted')
except RuntimeError as exc:assert str(exc)=='Synthetic global deadline expired'
checks.append('expired benchmark pull deadline raises')
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='SystemExit' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value==2 for n in ast.walk(tree))
checks.append('pixel mismatch has explicit nonzero exit')

result={'status':'PASS_LOCAL_STATIC_AND_MOCK_CHECKS','checks':checks,'count':len(checks),
    'candidate_sha256':hashlib.sha256(candidate).hexdigest(),
    'hardened_sha256_lf':hashlib.sha256(hardened.encode()).hexdigest(),
    'production_functional_runtime_pass_claimed':False,'actual_gstreamer_executed':False,
    'board_or_network_called':False}
(HERE/'GTK_INDEPENDENT_OFFLINE_CHECK.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
