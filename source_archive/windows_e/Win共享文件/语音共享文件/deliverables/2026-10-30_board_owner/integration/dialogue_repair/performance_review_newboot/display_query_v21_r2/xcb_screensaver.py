"""Read-only MIT-SCREEN-SAVER queries using the installed generic libxcb.

Wire layouts follow the official XCB screensaver.h and xcbext.h interfaces.
Only QueryVersion (0) and QueryInfo (1) can be emitted by this adapter.
"""
import ctypes as C
import ctypes.util
import select
import struct
import time


class Refused(RuntimeError):
    pass


def need(value, code):
    if not value:
        raise Refused(code)


def signature(library, name, arguments, result=C.c_int):
    function = getattr(library, name)
    function.argtypes, function.restype = arguments, result
    return function


class Extension(C.Structure):
    _fields_ = [('name', C.c_char_p), ('global_id', C.c_int)]


class ProtocolRequest(C.Structure):
    _fields_ = [('count', C.c_size_t), ('ext', C.POINTER(Extension)),
                ('opcode', C.c_uint8), ('isvoid', C.c_uint8)]


class IOVec(C.Structure):
    _fields_ = [('base', C.c_void_p), ('length', C.c_size_t)]


def checked_reply(raw, sequence):
    need(len(raw) == 32 and raw[0] == 1, 'XCB_REPLY_HEADER_INVALID')
    need(struct.unpack_from('=H', raw, 2)[0] == sequence & 65535
         and struct.unpack_from('=I', raw, 4)[0] == 0, 'XCB_REPLY_SEQUENCE_OR_LENGTH_INVALID')
    return raw


def decode_info(raw):
    state, kind = raw[1], raw[24]
    need(state in (0, 1, 2, 3) and kind in (0, 1, 2), 'XCB_SCREENSAVER_ENUM_INVALID')
    return dict(xss_idle_ms=struct.unpack_from('=I', raw, 16)[0], xss_state=state, xss_kind=kind)


class XcbScreenSaver:
    def __init__(self, root_window, library=None, free_library=None, clock=time.monotonic, wait=select.select):
        need(type(root_window) is int and 0 < root_window <= 0xffffffff, 'ROOT_WINDOW_REQUIRED')
        self.connection = None
        self.root_window, self.clock, self.wait = root_window, clock, wait
        self.lib = library or C.CDLL(ctypes.util.find_library('xcb') or 'libxcb.so.1')
        self.libc = free_library or C.CDLL(None)
        pointer = C.c_void_p
        signature(self.lib, 'xcb_connect', [C.c_char_p, C.POINTER(C.c_int)], pointer)
        signature(self.lib, 'xcb_connection_has_error', [pointer])
        signature(self.lib, 'xcb_disconnect', [pointer], None)
        signature(self.lib, 'xcb_get_extension_data', [pointer, C.POINTER(Extension)], pointer)
        signature(self.lib, 'xcb_send_request', [pointer, C.c_int, C.POINTER(IOVec), C.POINTER(ProtocolRequest)], C.c_uint)
        signature(self.lib, 'xcb_poll_for_reply', [pointer, C.c_uint, C.POINTER(pointer), C.POINTER(pointer)])
        signature(self.lib, 'xcb_flush', [pointer])
        signature(self.lib, 'xcb_get_file_descriptor', [pointer])
        signature(self.libc, 'free', [pointer], None)
        self.extension = Extension(b'MIT-SCREEN-SAVER', 0)
        self.connection = self.lib.xcb_connect(None, None)
        try:
            need(bool(self.connection) and self.lib.xcb_connection_has_error(self.connection) == 0,
                 'XCB_CONNECTION_UNAVAILABLE')
            pointer = self.lib.xcb_get_extension_data(self.connection, C.byref(self.extension))
            need(bool(pointer), 'XCB_EXTENSION_REPLY_UNAVAILABLE')
            extension = C.string_at(pointer, 32)
            need(extension[0] == 1 and extension[8] == 1 and extension[9] >= 128,
                 'SCREENSAVER_EXTENSION_UNAVAILABLE')
            self.major_opcode = extension[9]
            raw = self._reply(0)
            self.version = list(struct.unpack_from('=HH', raw, 8))
            need(self.version[0] == 1 and self.version[1] in (0, 1), 'SCREENSAVER_VERSION_UNSUPPORTED')
        except BaseException:
            self.close()
            raise

    def _reply(self, opcode):
        need(opcode in (0, 1) and type(opcode) is int, 'READONLY_OPCODE_REQUIRED')
        raw = struct.pack('=BBBBBBBB', 0, 0, 0, 0, 1, 1, 0, 0) if opcode == 0 else struct.pack('=BBHI', 0, 0, 0, self.root_window)
        payload = C.create_string_buffer(raw, len(raw))
        # libxcb owns two scratch iovecs immediately before the passed vector.
        vectors = (IOVec * 4)()
        vectors[2] = IOVec(C.cast(payload, C.c_void_p), len(raw))
        vectors[3] = IOVec(None, (-len(raw)) & 3)
        request = ProtocolRequest(2, C.pointer(self.extension), opcode, 0)
        vector = C.cast(C.byref(vectors, 2 * C.sizeof(IOVec)), C.POINTER(IOVec))
        sequence = self.lib.xcb_send_request(self.connection, 1, vector, C.byref(request))
        need(sequence != 0 and self.lib.xcb_flush(self.connection) > 0, 'XCB_QUERY_SEND_FAILED')
        deadline = self.clock() + 2.
        descriptor = self.lib.xcb_get_file_descriptor(self.connection)
        need(descriptor >= 0, 'XCB_CONNECTION_DESCRIPTOR_INVALID')
        reply, error = C.c_void_p(), C.c_void_p()
        try:
            while not self.lib.xcb_poll_for_reply(self.connection, sequence, C.byref(reply), C.byref(error)):
                need(self.lib.xcb_connection_has_error(self.connection) == 0, 'XCB_CONNECTION_LOST')
                remaining = deadline - self.clock()
                need(remaining > 0, 'XCB_QUERY_TIMEOUT')
                self.wait([descriptor], [], [], min(remaining, .05))
            need(not error.value and bool(reply.value), 'XCB_QUERY_REJECTED')
            return checked_reply(C.string_at(reply.value, 32), sequence)
        finally:
            if reply.value:
                self.libc.free(reply)
            if error.value:
                self.libc.free(error)

    def query(self):
        return decode_info(self._reply(1))

    def close(self):
        if self.connection:
            self.lib.xcb_disconnect(self.connection)
            self.connection = None


class ReadOnlyXSession:
    """Core policy and DPMS from existing Xlib, idle/state from a private XCB connection."""
    def __init__(self, helper, xcb_factory=XcbScreenSaver):
        self.display, self.xcb = None, None
        self.x, self.ext = helper._display_libraries()
        need(self.ext is not None, 'DPMS_LIBRARY_UNAVAILABLE')
        pointer, integer, ushort = C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_ushort)
        signature(self.x, 'XGetScreenSaver', [pointer, integer, integer, integer, integer])
        signature(self.x, 'XDefaultRootWindow', [pointer], C.c_ulong)
        signature(self.ext, 'DPMSCapable', [pointer])
        signature(self.ext, 'DPMSInfo', [pointer, ushort, integer])
        signature(self.ext, 'DPMSGetTimeouts', [pointer, ushort, ushort, ushort])
        self.display = self.x.XOpenDisplay(None)
        try:
            need(bool(self.display), 'X11_CONNECTION_UNAVAILABLE')
            need(bool(self.ext.DPMSCapable(self.display)), 'DPMS_CAPABILITY_UNAVAILABLE')
            self.xcb = xcb_factory(int(self.x.XDefaultRootWindow(self.display)))
            self.query()
        except BaseException:
            self.close()
            raise

    def query(self):
        values = [C.c_int() for _ in range(4)]
        self.x.XGetScreenSaver(self.display, *(C.byref(value) for value in values))
        level, enabled = C.c_ushort(), C.c_int()
        need(bool(self.ext.DPMSInfo(self.display, C.byref(level), C.byref(enabled))), 'DPMS_QUERY_FAILED')
        timeouts = [C.c_ushort() for _ in range(3)]
        need(bool(self.ext.DPMSGetTimeouts(self.display, *(C.byref(value) for value in timeouts))),
             'DPMS_TIMEOUT_QUERY_FAILED')
        need(level.value in (0, 1, 2, 3) and enabled.value in (0, 1), 'DPMS_ENUM_INVALID')
        return dict(screen_saver=dict(zip(('timeout', 'interval', 'prefer_blank', 'allow_exposures'),
                                         (value.value for value in values))),
                    dpms_enabled=bool(enabled.value), dpms_level=level.value,
                    dpms_timeouts=[value.value for value in timeouts], **self.xcb.query())

    def close(self):
        if self.xcb is not None:
            self.xcb.close()
            self.xcb = None
        if self.display:
            self.x.XCloseDisplay(self.display)
            self.display = None
