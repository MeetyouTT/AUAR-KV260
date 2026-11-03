"""Raise only this GTK window's frame above an existing unmanaged preview."""
import ctypes as C
import ctypes.util


def raise_owned_window(window):
    import gi
    gi.require_version('GdkX11', '3.0')
    from gi.repository import GdkX11
    native = window.get_window()
    xid = GdkX11.X11Window.get_xid(native)
    x = C.CDLL(ctypes.util.find_library('X11'))
    P, U, I = C.c_void_p, C.c_ulong, C.c_int
    x.XOpenDisplay.argtypes, x.XOpenDisplay.restype = [C.c_char_p], P
    x.XDefaultRootWindow.argtypes, x.XDefaultRootWindow.restype = [P], U
    x.XQueryTree.argtypes = [P, U, C.POINTER(U), C.POINTER(U),
                            C.POINTER(C.POINTER(U)), C.POINTER(C.c_uint)]
    x.XQueryTree.restype = I
    x.XFree.argtypes = [P]
    x.XRaiseWindow.argtypes = [P, U]
    x.XSync.argtypes, x.XCloseDisplay.argtypes = [P, I], [P]
    display = x.XOpenDisplay(None)
    if not display:
        raise RuntimeError('Cannot connect to the current X11 display')
    try:
        screen, target = x.XDefaultRootWindow(display), xid
        for _ in range(8):
            root, parent, children, count = U(), U(), C.POINTER(U)(), C.c_uint()
            if not x.XQueryTree(display, target, C.byref(root), C.byref(parent),
                                C.byref(children), C.byref(count)):
                raise RuntimeError('Cannot query this window ancestry')
            if children:
                x.XFree(C.cast(children, P))
            if parent.value == screen:
                break
            if parent.value in (0, target):
                raise RuntimeError('Invalid window ancestry')
            target = parent.value
        else:
            raise RuntimeError('Unexpected window ancestry depth')
        if target == screen:
            raise RuntimeError('Refusing to raise the root window')
        x.XRaiseWindow(display, target)
        x.XSync(display, 0)
        return {'own_window': hex(xid), 'own_frame': hex(target)}
    finally:
        x.XCloseDisplay(display)
