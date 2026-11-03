"""Wake only during conversation activity; leave desktop idle policy unchanged."""
import ctypes as C
import ctypes.util
from functools import lru_cache
import time


@lru_cache(maxsize=1)
def _display_libraries():
    """Resolve libraries once, before GTK starts its interactive event loop."""
    x=C.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
    pointer=C.c_void_p
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=pointer
    x.XResetScreenSaver.argtypes=[pointer];x.XSync.argtypes=[pointer,C.c_int]
    x.XCloseDisplay.argtypes=[pointer]
    name=ctypes.util.find_library('Xext')
    ext=C.CDLL(name) if name else None
    if ext is not None:
        ext.DPMSCapable.argtypes=[pointer]
        ext.DPMSInfo.argtypes=[pointer,C.POINTER(C.c_ushort),C.POINTER(C.c_int)]
        ext.DPMSForceLevel.argtypes=[pointer,C.c_ushort]
    return x,ext


def wake_display():
    x,ext=_display_libraries()
    display=x.XOpenDisplay(None)
    if not display:raise RuntimeError('Cannot connect to X11 display')
    try:
        x.XResetScreenSaver(display)
        if ext is not None:
            if ext.DPMSCapable(display):
                level=C.c_ushort();enabled=C.c_int()
                if ext.DPMSInfo(display,C.byref(level),C.byref(enabled)) and enabled.value and level.value:
                    ext.DPMSForceLevel(display,0)
        x.XSync(display,0)
    finally:x.XCloseDisplay(display)


class DisplayActivity:
    def __init__(self,wake=wake_display,clock=time.monotonic):
        self.wake=wake;self.clock=clock;self.next_wake=0.;self.error=''
        if wake is wake_display:
            # Loading symbols opens no X display and changes no idle policy.
            # Keep linker/library discovery off the recurring UI refresh.
            try:_display_libraries()
            except (OSError,RuntimeError,AttributeError) as exc:self.error=str(exc)

    def tick(self,active):
        if not active:
            self.next_wake=0.;return
        now=self.clock()
        if now<self.next_wake:return
        self.next_wake=now+5.
        try:self.wake();self.error=''
        except (OSError,RuntimeError,AttributeError) as exc:self.error=str(exc)
