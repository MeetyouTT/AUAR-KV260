"""Native EGL child surface for GTK builds without GdkGLContext support.

The opaque child X window has its own backing surface, so GTK's Cairo paint
cannot overwrite a completed GL frame. All calls stay on the GTK main thread.
"""
import ctypes as C

I,U,L,P=C.c_int,C.c_uint,C.c_ulong,C.c_void_p
class Attributes(C.Structure):
    _fields_=[(k,I) for k in ('x','y','width','height','border_width','depth')]+[
      ('visual',P),('root',L),('window_class',I),('bit_gravity',I),('win_gravity',I),('backing_store',I),
      ('backing_planes',L),('backing_pixel',L),('save_under',I),('colormap',L),('map_installed',I),('map_state',I),
      ('all_event_masks',C.c_long),('your_event_mask',C.c_long),('do_not_propagate_mask',C.c_long),('override_redirect',I),('screen',P)]

class EGLWindow:
    def __init__(self,parent,width,height):
        self.x=C.CDLL('libX11.so.6');self.e=C.CDLL('libEGL.so.1')
        self.xd=self.display=self.surface=self.context=None;self.child=0;self.size=None
        for name,result,args in (
          ('XOpenDisplay',P,[C.c_char_p]),('XCloseDisplay',I,[P]),('XGetWindowAttributes',I,[P,L,C.POINTER(Attributes)]),
          ('XVisualIDFromVisual',L,[P]),('XCreateSimpleWindow',L,[P,L,I,I,U,U,U,L,L]),
          ('XMapWindow',I,[P,L]),('XDestroyWindow',I,[P,L]),('XResizeWindow',I,[P,L,U,U]),('XFlush',I,[P])):
            fn=getattr(self.x,name);fn.restype=result;fn.argtypes=args
        for name,result,args in (
          ('eglGetDisplay',P,[P]),('eglInitialize',I,[P,C.POINTER(I),C.POINTER(I)]),('eglBindAPI',I,[U]),
          ('eglChooseConfig',I,[P,C.POINTER(I),C.POINTER(P),I,C.POINTER(I)]),('eglGetConfigAttrib',I,[P,P,I,C.POINTER(I)]),
          ('eglCreateWindowSurface',P,[P,P,L,C.POINTER(I)]),('eglCreateContext',P,[P,P,P,C.POINTER(I)]),
          ('eglGetCurrentContext',P,[]),
          ('eglMakeCurrent',I,[P,P,P,P]),('eglSwapBuffers',I,[P,P]),('eglSwapInterval',I,[P,I]),
          ('eglDestroyContext',I,[P,P]),('eglDestroySurface',I,[P,P]),('eglTerminate',I,[P]),('eglGetError',I,[])):
            fn=getattr(self.e,name);fn.restype=result;fn.argtypes=args
        try:
            self.xd=self.x.XOpenDisplay(None)
            if not self.xd:raise RuntimeError('Existing X display unavailable')
            attr=Attributes()
            if not self.x.XGetWindowAttributes(self.xd,parent,C.byref(attr)):raise RuntimeError('GTK parent X window unavailable')
            visual=int(self.x.XVisualIDFromVisual(attr.visual))
            self.display=self.e.eglGetDisplay(self.xd)
            if not self.e.eglInitialize(self.display,C.byref(I()),C.byref(I())):self.failure('eglInitialize')
            if not self.e.eglBindAPI(0x30A0):self.failure('eglBindAPI')
            # EGL_WINDOW_BIT, EGL_OPENGL_ES2_BIT; native X visual must match the parent.
            attrs=(I*13)(0x3033,4,0x3040,4,0x3024,0,0x3023,0,0x3022,0,0x3021,0,0x3038)
            configs=(P*128)();count=I()
            if not self.e.eglChooseConfig(self.display,attrs,configs,128,C.byref(count)):self.failure('eglChooseConfig')
            config=None
            for candidate in configs[:count.value]:
                native_visual=I()
                if self.e.eglGetConfigAttrib(self.display,candidate,0x302E,C.byref(native_visual)) and native_visual.value==visual:
                    config=candidate;break
            if not config:raise RuntimeError('No Mali EGL config matches GTK X visual '+str(visual))
            self.visual=visual;self.config_bits=[]
            for key in (0x3024,0x3023,0x3022,0x3021):
                value=I();self.e.eglGetConfigAttrib(self.display,config,key,C.byref(value));self.config_bits.append(value.value)
            self.child=self.x.XCreateSimpleWindow(self.xd,parent,0,0,width,height,0,0,0xFCFCF3)
            if not self.child:raise RuntimeError('Cannot create EGL child window')
            self.size=(width,height);self.x.XMapWindow(self.xd,self.child);self.x.XFlush(self.xd)
            self.surface=self.e.eglCreateWindowSurface(self.display,config,self.child,(I*1)(0x3038))
            self.context=self.e.eglCreateContext(self.display,config,None,(I*3)(0x3098,2,0x3038))
            if not self.surface or not self.context:self.failure('EGL window/context creation')
            # GTK's frame clock already paces presentation; avoid a second driver wait.
            self.current()
            if not self.e.eglSwapInterval(self.display,0):self.failure('eglSwapInterval(0)')
        except Exception:
            self.close();raise
    def failure(self,operation):raise RuntimeError(operation+' failed: EGL '+hex(self.e.eglGetError()))
    def current(self):
        if self.e.eglGetCurrentContext()==self.context:return
        if not self.e.eglMakeCurrent(self.display,self.surface,self.surface,self.context):self.failure('eglMakeCurrent')
    def resize(self,width,height):
        if (width,height)!=self.size:
            self.x.XResizeWindow(self.xd,self.child,width,height);self.x.XFlush(self.xd);self.size=(width,height)
    def swap(self):
        if not self.e.eglSwapBuffers(self.display,self.surface):self.failure('eglSwapBuffers')
    def close(self,*,parent_alive=True):
        if self.display:
            self.e.eglMakeCurrent(self.display,None,None,None)
            if self.context:self.e.eglDestroyContext(self.display,self.context);self.context=None
            if self.surface:self.e.eglDestroySurface(self.display,self.surface);self.surface=None
            self.e.eglTerminate(self.display);self.display=None
        if self.xd:
            if self.child and parent_alive:self.x.XDestroyWindow(self.xd,self.child)
            self.child=0;self.x.XCloseDisplay(self.xd);self.xd=None
