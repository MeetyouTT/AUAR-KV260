"""Pinned read-only batch extension; single-word writes retain all checks."""
import ctypes
from vsrv_transport import NativeRegisters,READ_OFFSETS


class BatchRegisters(NativeRegisters):
    def __init__(self,library,library_sha256,boot_id,runtime_hashes):
        super().__init__(library,library_sha256,boot_id,runtime_hashes)
        self.lib.vsrv_read_many.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint),ctypes.c_uint,
                                         ctypes.POINTER(ctypes.c_uint32)]
        self.lib.vsrv_read_many.restype=ctypes.c_int

    def read_many(self,offsets):
        values=tuple(offsets)
        if not 1<=len(values)<=32 or any(type(n) is not int or n not in READ_OFFSETS for n in values) or not self.handle.value:
            raise ValueError('Invalid or closed register batch read')
        offsets_array=(ctypes.c_uint*len(values))(*values)
        output=(ctypes.c_uint32*len(values))()
        self._check(self.lib.vsrv_read_many(self.handle,offsets_array,len(values),output))
        return list(output)
