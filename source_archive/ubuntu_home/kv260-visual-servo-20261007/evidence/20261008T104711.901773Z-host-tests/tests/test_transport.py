import ctypes,unittest
from unittest.mock import Mock
from vsrv_transport import NativeRegisters

class TransportValidation(unittest.TestCase):
    def setUp(self):
        self.io=NativeRegisters.__new__(NativeRegisters)
        self.io.handle=ctypes.c_void_p(1);self.io.lib=Mock()

    def test_invalid_mmio_never_reaches_native_library(self):
        for offset in (0x24,1,-4,0x48,4096,True):
            with self.assertRaises(ValueError):self.io.read(offset)
        for offset,value in ((0,1),(0x28,1),(1,1),(0x24,-1),(0x24,1<<32),(0x24,True)):
            with self.assertRaises(ValueError):self.io.write(offset,value)
        self.assertFalse(self.io.lib.mock_calls)

    def test_native_failure_propagates_without_retry(self):
        self.io.lib.vsrv_write.return_value=1
        with self.assertRaises(OSError):self.io.write(0x24,0x53544f50)
        self.io.lib.vsrv_write.assert_called_once()

    def test_close_invalidates_handle_even_if_stop_fails(self):
        self.io.lib.vsrv_close.return_value=1
        with self.assertRaises(OSError):self.io.close()
        with self.assertRaises(ValueError):self.io.write(0x24,0x53544f50)
        self.io.lib.vsrv_close.assert_called_once()

if __name__=='__main__':unittest.main()
