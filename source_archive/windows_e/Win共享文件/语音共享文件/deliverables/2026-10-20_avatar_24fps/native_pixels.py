"""Native pixel proof; only opt-in candidates load this library."""
import ctypes as C
import math
from pathlib import Path
import weakref
from collections import OrderedDict
from PIL import Image

class NativePixels:
    def __init__(self,library,background='white',size=(423,438),cache_bytes=128*1024*1024,threads=1):
        if not isinstance(threads,int) or not 1<=threads<=4:raise ValueError('Pixel threads must be 1..4')
        self.lib=C.CDLL(str(library));ptr=C.c_void_p
        self.lib.aura_pixels_create.restype=ptr
        self.lib.aura_pixels_threads.argtypes=[C.c_int]
        self.lib.aura_pixels_destroy.argtypes=[ptr]
        self.lib.aura_pixels_error.restype=C.c_char_p
        self.lib.aura_pixels_mode.argtypes=[ptr,C.c_int]
        self.lib.aura_pixels_times.argtypes=[ptr,C.POINTER(C.c_double)]
        self.lib.aura_blend.argtypes=[ptr,ptr,ptr,C.c_int,C.c_float]
        self.lib.aura_pose.argtypes=[ptr,ptr,C.c_int,C.c_int,C.POINTER(C.c_double),C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,ptr]
        self.lib.aura_pose_blend.argtypes=[ptr,ptr,ptr,C.c_float,C.c_int,C.c_int,C.POINTER(C.c_double),C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,ptr]
        self.owner=self.lib.aura_pixels_create();self.size=tuple(size)
        self.lib.aura_pixels_threads(threads);self.threads=threads
        self.background=Image.new('RGB',(1,1),background).getpixel((0,0))
        self.inputs=OrderedDict();self.cached_bytes=0;self.limit=cache_bytes
        self.output=C.create_string_buffer(self.size[0]*self.size[1]*3)
    def data(self,image):
        key=id(image);old=self.inputs.get(key)
        if old and old[0]() is image:
            self.inputs.move_to_end(key);return old[1]
        raw=image.tobytes()
        if len(raw)<=self.limit:
            def expired(ref,k=key):
                found=self.inputs.get(k)
                if found and found[0] is ref:
                    self.cached_bytes-=len(found[1]);self.inputs.pop(k,None)
            self.inputs[key]=(weakref.ref(image,expired),raw);self.cached_bytes+=len(raw)
            while self.cached_bytes>self.limit:
                _,value=self.inputs.popitem(last=False);self.cached_bytes-=len(value[1])
        return raw
    def blend(self,a,b,alpha):
        if alpha<=0:return a
        if alpha>=1:return b
        if a.mode!=b.mode or a.size!=b.size:raise ValueError('Mismatched frames')
        if not hasattr(a,'_native_blend') and not hasattr(b,'_native_blend'):
            proxy=a._new(a.im);proxy._native_blend=(a,b,float(alpha));return proxy
        return self.materialize_blend(a,b,alpha)
    def materialize_blend(self,a,b,alpha):
        first,second=self.data(self.materialize(a)),self.data(self.materialize(b));out=C.create_string_buffer(len(first))
        assert self.lib.aura_blend(first,second,out,len(first),alpha)==0
        return Image.frombytes(a.mode,a.size,out.raw)
    def materialize(self,image):
        blend=getattr(image,'_native_blend',None)
        return self.materialize_blend(*blend) if blend else image
    def pose(self,image,off):
        if image.mode!='RGBA':raise ValueError('Native pose expects RGBA')
        w,h=image.size;angle=math.radians(off.tilt_deg);c,s=math.cos(angle),math.sin(angle)
        sy=max(1e-6,off.scale_y);cx,cy=w/2+off.dx,h-off.dy
        matrix=(C.c_double*6)(c,-s,w/2-c*cx+s*cy,s/sy,c/sy,h-(s*cx+c*cy)/sy)
        blend=getattr(image,'_native_blend',None)
        if blend:
            a,b,t=blend;first,second=self.data(a),self.data(b)
            result=self.lib.aura_pose_blend(self.owner,first,second,t,w,h,matrix,*self.size,*self.background,self.output)
        else:
            raw=self.data(image)
            result=self.lib.aura_pose(self.owner,raw,w,h,matrix,*self.size,*self.background,self.output)
        if result:raise RuntimeError(self.lib.aura_pixels_error().decode())
        return Image.frombytes('RGB',self.size,self.output.raw)
    def configure(self,core):
        core.defer_portrait_offsets=True;core._apply_offsets=self.pose;core.blend_frames=self.blend;core.native_pixels=self
    def cpu_times(self):
        values=(C.c_double*4)();self.lib.aura_pixels_times(self.owner,values)
        return dict(zip(('flatten','affine','resize','total'),values))
    def close(self):
        if self.owner:self.lib.aura_pixels_destroy(self.owner);self.owner=None
