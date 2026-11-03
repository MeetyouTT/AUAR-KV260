"""Metadata-only discovery and one exact-window move, for an idle layout slot.

This module does not connect to X11 until explicitly constructed by the later
granted layout step. It never creates a window or restarts an original process.
"""
import ctypes as C


class PopupDisplay:
    def __init__(self):
        self.x = C.CDLL('libX11.so.6')
        x = self.x
        x.XOpenDisplay.argtypes = [C.c_char_p]; x.XOpenDisplay.restype = C.c_void_p
        x.XDefaultRootWindow.argtypes = [C.c_void_p]; x.XDefaultRootWindow.restype = C.c_ulong
        x.XDefaultScreen.argtypes = [C.c_void_p]; x.XDefaultScreen.restype = C.c_int
        for name in ('XDisplayWidth', 'XDisplayHeight'):
            fn = getattr(x,name); fn.argtypes = [C.c_void_p,C.c_int]; fn.restype = C.c_int
        x.XInternAtom.argtypes = [C.c_void_p,C.c_char_p,C.c_int]; x.XInternAtom.restype = C.c_ulong
        x.XQueryTree.argtypes = [C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),
                                C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
        x.XQueryTree.restype = C.c_int
        x.XGetWindowProperty.argtypes = [C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,
            C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ubyte))]
        x.XGetWindowProperty.restype = C.c_int
        x.XGetGeometry.argtypes = [C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_int),
                                  C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)]
        x.XGetGeometry.restype = C.c_int
        x.XTranslateCoordinates.argtypes = [C.c_void_p,C.c_ulong,C.c_ulong,C.c_int,C.c_int,
                                            C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_ulong)]
        x.XTranslateCoordinates.restype = C.c_int
        x.XMoveWindow.argtypes = [C.c_void_p,C.c_ulong,C.c_int,C.c_int]; x.XMoveWindow.restype = C.c_int
        x.XSync.argtypes = [C.c_void_p,C.c_int]; x.XSync.restype = C.c_int
        x.XFree.argtypes = [C.c_void_p]; x.XFree.restype = C.c_int
        x.XCloseDisplay.argtypes = [C.c_void_p]; x.XCloseDisplay.restype = C.c_int
        self.errors = []
        handler = C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)
        self.error_handler = handler(lambda display,event: self.errors.append(True) or 0)
        x.XSetErrorHandler.argtypes = [handler]; x.XSetErrorHandler.restype = C.c_void_p
        x.XSetErrorHandler(self.error_handler)
        self.display = x.XOpenDisplay(b':0'); assert self.display, 'Original display unavailable'
        self.root = int(x.XDefaultRootWindow(self.display))
        self.pid_atom = x.XInternAtom(self.display,b'_NET_WM_PID',True)
        assert self.pid_atom, 'Original X11 PID metadata unavailable'
        screen = x.XDefaultScreen(self.display)
        self.screen = [x.XDisplayWidth(self.display,screen),x.XDisplayHeight(self.display,screen)]

    def close(self):
        if self.display: self.x.XCloseDisplay(self.display); self.display = None

    def children(self, window):
        root,parent,count = C.c_ulong(),C.c_ulong(),C.c_uint()
        values = C.POINTER(C.c_ulong)()
        ok = self.x.XQueryTree(self.display,window,C.byref(root),C.byref(parent),C.byref(values),C.byref(count))
        assert ok, 'Original X11 tree unavailable'
        try: return int(parent.value),[int(values[i]) for i in range(count.value)]
        finally:
            if values: self.x.XFree(values)

    def pid(self, window):
        kind,fmt,count,extra = C.c_ulong(),C.c_int(),C.c_ulong(),C.c_ulong()
        data = C.POINTER(C.c_ubyte)()
        code = self.x.XGetWindowProperty(self.display,window,self.pid_atom,0,1,False,0,
            C.byref(kind),C.byref(fmt),C.byref(count),C.byref(extra),C.byref(data))
        try:
            if code == 0 and fmt.value == 32 and count.value == 1 and data:
                return int(C.cast(data,C.POINTER(C.c_ulong))[0])
            return None
        finally:
            if data: self.x.XFree(data)

    def geometry(self, window):
        root,child = C.c_ulong(),C.c_ulong()
        x,y,root_x,root_y = C.c_int(),C.c_int(),C.c_int(),C.c_int()
        width,height,border,depth = C.c_uint(),C.c_uint(),C.c_uint(),C.c_uint()
        assert self.x.XGetGeometry(self.display,window,C.byref(root),C.byref(x),C.byref(y),C.byref(width),
                                   C.byref(height),C.byref(border),C.byref(depth)), 'Popup geometry unavailable'
        assert self.x.XTranslateCoordinates(self.display,window,self.root,0,0,C.byref(root_x),C.byref(root_y),C.byref(child))
        return dict(window=window,x=root_x.value,y=root_y.value,width=width.value,height=height.value,border=border.value)

    def windows_for_pid(self, pid):
        # GTK popup windows are root children; do not inspect window names,
        # text, screenshots, private properties, or unrelated descendants.
        _,windows = self.children(self.root)
        result = []
        for window in windows:
            if self.pid(window) == pid:
                row = self.geometry(window); row['parent'] = self.children(window)[0]; result.append(row)
        self.x.XSync(self.display,False)
        assert not self.errors, 'X11 tree changed during metadata query; inspect again under a new read step'
        return result

    def move_exact(self, pid, expected, new_y):
        assert expected['parent'] == self.root, 'Move only the exact root-level original popup'
        assert 0 <= new_y and new_y + expected['height'] <= self.screen[1]
        matches = [row for row in self.windows_for_pid(pid) if row['window'] == expected['window']]
        assert matches == [expected], 'Exact PID/window/before geometry changed'
        self.x.XMoveWindow(self.display,expected['window'],expected['x'],new_y)
        self.x.XSync(self.display,False)
        assert not self.errors, 'X11 move has an uncertain result; observe without resending'
        after = self.geometry(expected['window'])
        self.x.XSync(self.display,False)
        assert not self.errors
        assert after == {k:v for k,v in dict(expected,y=new_y).items() if k!='parent'}, 'Popup did not reach the exact requested position'
        return dict(after,parent=self.root)
