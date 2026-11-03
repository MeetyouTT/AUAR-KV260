"""Read the actual X11 screen in a separate process, without GTK/Cairo surfaces."""
import argparse
import ctypes as C
import ctypes.util
import os


class XImage(C.Structure):
    _fields_ = [(n,C.c_int) for n in ('width','height','xoffset','format')] + [('data',C.c_void_p)] + [
        (n,C.c_int) for n in ('byte_order','bitmap_unit','bitmap_bit_order','bitmap_pad','depth',
                            'bytes_per_line','bits_per_pixel')] + [
        (n,C.c_ulong) for n in ('red_mask','green_mask','blue_mask')]


def capture(path):
    from PIL import Image
    lib = C.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
    lib.XOpenDisplay.argtypes = [C.c_char_p]; lib.XOpenDisplay.restype = C.c_void_p
    lib.XDefaultRootWindow.argtypes = [C.c_void_p]; lib.XDefaultRootWindow.restype = C.c_ulong
    lib.XGetGeometry.argtypes = [C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),
        C.POINTER(C.c_int),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)]
    lib.XGetImage.argtypes = [C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_ulong,C.c_int]
    lib.XGetImage.restype = C.POINTER(XImage)
    lib.XDestroyImage.argtypes = [C.POINTER(XImage)]
    lib.XCloseDisplay.argtypes = [C.c_void_p]
    display = lib.XOpenDisplay(os.environ.get('DISPLAY',':0').encode())
    if not display:raise RuntimeError('Cannot connect to X11 for screen capture')
    handle = None
    try:
        root = lib.XDefaultRootWindow(display)
        parent=C.c_ulong();x=C.c_int();y=C.c_int();width=C.c_uint();height=C.c_uint()
        border=C.c_uint();depth=C.c_uint()
        if not lib.XGetGeometry(display,root,C.byref(parent),C.byref(x),C.byref(y),C.byref(width),
                                C.byref(height),C.byref(border),C.byref(depth)):
            raise RuntimeError('Cannot query screen geometry')
        if not (0<width.value<=4096 and 0<height.value<=2160):raise ValueError('Unexpected screen size')
        handle = lib.XGetImage(display,root,0,0,width.value,height.value,C.c_ulong(-1).value,2)
        if not handle:raise RuntimeError('X11 did not return a screen image')
        source=handle.contents
        if source.bits_per_pixel not in (16,24,32):raise ValueError('Unsupported screen pixel format')
        # Pillow's native raw decoders cover this board's RGB565 screen and
        # ordinary X11 RGB24/32, including padded rows. No NumPy startup needed.
        modes={(16,0xF800,0x07E0,0x001F):'BGR;16',
               (16,0x7C00,0x03E0,0x001F):'BGR;15',
               (24,0xFF0000,0x00FF00,0x0000FF):'BGR',
               (32,0xFF0000,0x00FF00,0x0000FF):'BGRX',
               (24,0x0000FF,0x00FF00,0xFF0000):'RGB',
               (32,0x0000FF,0x00FF00,0xFF0000):'RGBX'}
        mode=modes.get((source.bits_per_pixel,source.red_mask,source.green_mask,source.blue_mask))
        if source.byte_order!=0 or mode is None:raise ValueError('Unsupported screen color masks or byte order')
        raw=C.string_at(source.data,source.bytes_per_line*source.height)
        image=Image.frombytes('RGB',(source.width,source.height),raw,'raw',mode,source.bytes_per_line,1)
        image.save(str(path),format='PNG',compress_level=1)
        return image.size
    finally:
        if handle:lib.XDestroyImage(handle)
        lib.XCloseDisplay(display)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination')
    capture(parser.parse_args().destination)
