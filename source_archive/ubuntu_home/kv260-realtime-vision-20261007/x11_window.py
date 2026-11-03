"""Owned X11 full-screen window for the GStreamer video overlay."""
import ctypes as C
import ctypes.util


class Window:
    def __init__(self):
        self.x = C.CDLL(ctypes.util.find_library('X11'))
        P, U, I = C.c_void_p, C.c_ulong, C.c_int
        def bind(name, result, args):
            f = getattr(self.x, name)
            f.restype, f.argtypes = result, args
            return f
        bind('XInitThreads', I, [])()
        self.display = bind('XOpenDisplay', P, [C.c_char_p])(b':0')
        if not self.display:
            raise RuntimeError('Cannot open X display :0')
        root = bind('XDefaultRootWindow', U, [P])(self.display)
        self.width = bind('XDisplayWidth', I, [P, I])(self.display, 0)
        self.height = bind('XDisplayHeight', I, [P, I])(self.display, 0)
        self.handle = bind('XCreateSimpleWindow', U, [P, U, I, I, C.c_uint, C.c_uint, C.c_uint, U, U])(
            self.display, root, 0, 0, self.width, self.height, 0, 0, 0)
        class Attributes(C.Structure):
            _fields_ = [('background_pixmap', U), ('background_pixel', U), ('border_pixmap', U),
                        ('border_pixel', U), ('bit_gravity', I), ('win_gravity', I), ('backing_store', I),
                        ('backing_planes', U), ('backing_pixel', U), ('save_under', I),
                        ('event_mask', C.c_long), ('do_not_propagate_mask', C.c_long),
                        ('override_redirect', I), ('colormap', U), ('cursor', U)]
        attrs = Attributes()
        attrs.override_redirect = 1
        bind('XChangeWindowAttributes', I, [P, U, U, C.POINTER(Attributes)])(
            self.display, self.handle, 1 << 9, C.byref(attrs))
        bind('XStoreName', I, [P, U, C.c_char_p])(self.display, self.handle, b'AURA Real-time Face Tracking')
        bind('XMapRaised', I, [P, U])(self.display, self.handle)
        bind('XSync', I, [P, I])(self.display, 0)
        self._keep_awake = bind('XResetScreenSaver', I, [P])
        self._destroy = bind('XDestroyWindow', I, [P, U])
        self._close = bind('XCloseDisplay', I, [P])

    def keep_awake(self):
        self._keep_awake(self.display)
        self.x.XFlush.argtypes = [C.c_void_p]
        self.x.XFlush(self.display)

    def close(self):
        if self.display:
            self._destroy(self.display, self.handle)
            self._close(self.display)
            self.display = None
