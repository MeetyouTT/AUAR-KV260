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
    import numpy as np
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
        raw=np.frombuffer(C.string_at(source.data,source.bytes_per_line*source.height),dtype=np.uint8)
        raw=raw.reshape(source.height,source.bytes_per_line)
        bpp=source.bits_per_pixel//8
        packed=raw[:,:source.width*bpp].reshape(source.height,source.width,bpp).astype(np.uint32)
        pixels=np.zeros((source.height,source.width),dtype=np.uint32)
        for j in range(bpp):pixels |= packed[:,:,j] << (8*(j if source.byte_order==0 else bpp-1-j))
        channels=[]
        for mask in (source.red_mask,source.green_mask,source.blue_mask):
            if not mask:raise ValueError('Missing screen color mask')
            shift=(mask & -mask).bit_length()-1;maximum=mask>>shift
            channels.append((((pixels & mask)>>shift)*255//maximum).astype(np.uint8))
        image=Image.fromarray(np.stack(channels,axis=2),'RGB')
        image.save(str(path),format='PNG')
        return image.size
    finally:
        if handle:lib.XDestroyImage(handle)
        lib.XCloseDisplay(display)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination')
    capture(parser.parse_args().destination)
