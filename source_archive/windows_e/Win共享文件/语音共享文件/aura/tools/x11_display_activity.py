"""Wake only during conversation activity; leave desktop idle policy unchanged."""
import ctypes as C
import ctypes.util
import time


def wake_display():
    x=C.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
    pointer=C.c_void_p
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=pointer
    x.XResetScreenSaver.argtypes=[pointer];x.XSync.argtypes=[pointer,C.c_int]
    x.XCloseDisplay.argtypes=[pointer]
    display=x.XOpenDisplay(None)
    if not display:raise RuntimeError('Cannot connect to X11 display')
    try:
        x.XResetScreenSaver(display)
        name=ctypes.util.find_library('Xext')
        if name:
            ext=C.CDLL(name);ext.DPMSCapable.argtypes=[pointer]
            ext.DPMSInfo.argtypes=[pointer,C.POINTER(C.c_ushort),C.POINTER(C.c_int)]
            ext.DPMSForceLevel.argtypes=[pointer,C.c_ushort]
            if ext.DPMSCapable(display):
                level=C.c_ushort();enabled=C.c_int()
                if ext.DPMSInfo(display,C.byref(level),C.byref(enabled)) and enabled.value and level.value:
                    ext.DPMSForceLevel(display,0)
        x.XSync(display,0)
    finally:x.XCloseDisplay(display)


class DisplayActivity:
    def __init__(self,wake=wake_display,clock=time.monotonic):
        self.wake=wake;self.clock=clock;self.next_wake=0.;self.error=''

    def tick(self,active):
        if not active:
            self.next_wake=0.;return
        now=self.clock()
        if now<self.next_wake:return
        self.next_wake=now+5.
        try:self.wake();self.error=''
        except (OSError,RuntimeError,AttributeError) as exc:self.error=str(exc)
