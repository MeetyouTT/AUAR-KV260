"""Keep Windows speech workers owned by their parent host's lifetime."""
import ctypes
from ctypes import wintypes
import os


class OwnedSpeechJob:
    def __init__(self, process):
        self.handle = None
        if os.name != 'nt':return
        class Basic(ctypes.Structure):
            _fields_ = [('ProcessTime',ctypes.c_longlong),('JobTime',ctypes.c_longlong),
                ('Flags',wintypes.DWORD),('MinWorkingSet',ctypes.c_size_t),('MaxWorkingSet',ctypes.c_size_t),
                ('ActiveProcesses',wintypes.DWORD),('Affinity',ctypes.c_size_t),
                ('Priority',wintypes.DWORD),('Scheduling',wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name,ctypes.c_ulonglong) for name in
                ('ReadOperations','WriteOperations','OtherOperations','ReadBytes','WriteBytes','OtherBytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('Basic',Basic),('IO',IO),('ProcessMemory',ctypes.c_size_t),
                ('JobMemory',ctypes.c_size_t),('PeakProcessMemory',ctypes.c_size_t),('PeakJobMemory',ctypes.c_size_t)]
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype=wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=self.kernel.CreateJobObjectW(None,None)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        limits=Extended();limits.Basic.Flags=0x00002000
        try:
            if not self.kernel.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not self.kernel.AssignProcessToJobObject(handle,wintypes.HANDLE(int(process._handle))):
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            self.kernel.CloseHandle(handle);raise
        self.handle=handle

    def close(self):
        if self.handle:
            handle,self.handle=self.handle,None
            self.kernel.CloseHandle(handle)
