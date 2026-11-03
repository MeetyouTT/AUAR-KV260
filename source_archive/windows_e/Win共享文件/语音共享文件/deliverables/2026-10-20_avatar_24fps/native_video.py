"""Native GStreamer handoff; no Python/GTK callback on the frame delivery path."""
import ctypes as C

class NativeVideo:
    def __init__(self,library,size):
        self.lib=C.CDLL(str(library));p=C.c_void_p
        self.lib.aura_video_create.restype=p
        self.lib.aura_video_attach.argtypes=[p,C.c_ulong,C.c_int,C.c_int]
        self.lib.aura_video_push.argtypes=[p,p,C.c_int,C.c_uint64]
        self.lib.aura_video_stats.argtypes=[p,C.POINTER(C.c_double)]
        self.lib.aura_video_destroy.argtypes=[p]
        self.lib.aura_pixels_error.restype=C.c_char_p
        self.owner=self.lib.aura_video_create();self.size=tuple(size)
    def attach(self,handle):
        if self.lib.aura_video_attach(self.owner,int(handle),*self.size):raise RuntimeError(self.lib.aura_pixels_error().decode())
    def push(self,rgb,sequence):
        result=self.lib.aura_video_push(self.owner,rgb,len(rgb),sequence)
        if result<0:raise RuntimeError('Native avatar sink failed: '+self.lib.aura_pixels_error().decode())
    def read(self):
        values=(C.c_double*9)()
        if self.lib.aura_video_stats(self.owner,values):raise RuntimeError(self.lib.aura_pixels_error().decode())
        return dict(zip(('pushed','received','sequence','fps','p50_ms','p95_ms','p99_ms','max_ms','age_ms'),values))
    def close(self):
        if self.owner:self.lib.aura_video_destroy(self.owner);self.owner=None
