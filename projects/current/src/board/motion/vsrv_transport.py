"""Board-only, exclusive, word-wide VSRV transport. Never loads PL or arms."""
import ctypes
import hashlib
import os
from pathlib import Path

READ_OFFSETS=frozenset(range(0,0x48,4))-frozenset((0x24,))
WRITE_OFFSETS=frozenset((0x10,0x14,0x18,0x1c,0x20,0x24,0x3c))

class NativeRegisters:
    def __init__(self,library,library_sha256,boot_id,runtime_hashes):
        self.handle=ctypes.c_void_p()
        if os.uname().machine!='aarch64' or os.geteuid()!=0:
            raise RuntimeError('Board-only transport; no host MMIO')
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=boot_id:
            raise RuntimeError('Boot mismatch; no MMIO')
        for path,digest in runtime_hashes.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:
                raise RuntimeError('Installed runtime hash mismatch; no MMIO')
        if hashlib.sha256(Path(library).read_bytes()).hexdigest()!=library_sha256:
            raise RuntimeError('Native library hash mismatch; no MMIO')
        self.lib=ctypes.CDLL(str(library))
        self.lib.vsrv_open.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)]
        self.lib.vsrv_read.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint32)]
        self.lib.vsrv_write.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint32]
        self.lib.vsrv_close.argtypes=[ctypes.c_void_p]
        for n in ('vsrv_open','vsrv_read','vsrv_write','vsrv_close'):
            getattr(self.lib,n).restype=ctypes.c_int
        self._check(self.lib.vsrv_open(boot_id.encode(),ctypes.byref(self.handle)))

    @staticmethod
    def _check(rc):
        if rc:raise OSError(rc,os.strerror(rc))

    def read(self,offset):
        if type(offset) is not int or offset not in READ_OFFSETS or not self.handle.value:
            raise ValueError('Invalid or closed register read')
        value=ctypes.c_uint32()
        self._check(self.lib.vsrv_read(self.handle,offset,ctypes.byref(value)))
        return value.value

    def write(self,offset,value):
        if (type(offset) is not int or offset not in WRITE_OFFSETS or not self.handle.value
                or type(value) is not int or not 0<=value<=0xffffffff):
            raise ValueError('Invalid or closed register write')
        self._check(self.lib.vsrv_write(self.handle,offset,value))

    def close(self):
        if self.handle.value:
            rc=self.lib.vsrv_close(self.handle)
            self.handle=ctypes.c_void_p()
            self._check(rc)

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
