"""Windows identity guard for the diagnostic fixture, never a production host."""
import ctypes as C
from ctypes import wintypes as W
import os

k=C.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=(W.DWORD,W.BOOL,W.DWORD);k.OpenProcess.restype=W.HANDLE
k.GetProcessTimes.argtypes=(W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME));k.GetProcessTimes.restype=W.BOOL
k.QueryFullProcessImageNameW.argtypes=(W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD));k.QueryFullProcessImageNameW.restype=W.BOOL
k.CloseHandle.argtypes=(W.HANDLE,);k.CloseHandle.restype=W.BOOL
k.TerminateProcess.argtypes=(W.HANDLE,W.UINT);k.TerminateProcess.restype=W.BOOL
k.WaitForSingleObject.argtypes=(W.HANDLE,W.DWORD);k.WaitForSingleObject.restype=W.DWORD

def _identity(handle,pid):
    values=[W.FILETIME() for _ in range(4)]
    if not k.GetProcessTimes(handle,*(C.byref(v) for v in values)):raise C.WinError(C.get_last_error())
    size=W.DWORD(32768);name=C.create_unicode_buffer(size.value)
    if not k.QueryFullProcessImageNameW(handle,0,name,C.byref(size)):raise C.WinError(C.get_last_error())
    return dict(pid=int(pid),creation_filetime=(values[0].dwHighDateTime<<32)|values[0].dwLowDateTime,executable=name.value)

def process_identity(pid):
    handle=k.OpenProcess(0x1000,False,int(pid))
    if not handle:raise C.WinError(C.get_last_error())
    try:return _identity(handle,pid)
    finally:k.CloseHandle(handle)

def terminate_verified(identity):
    """One held handle: verify creation+executable, then stop only that process."""
    handle=k.OpenProcess(0x1000|0x0001|0x00100000,False,int(identity['pid']))
    if not handle:
        if C.get_last_error()==87:return dict(status='ALREADY_EXITED',pid=identity['pid'])
        raise C.WinError(C.get_last_error())
    try:
        actual=_identity(handle,identity['pid'])
        assert actual['creation_filetime']==identity['creation_filetime'],'PID creation token changed'
        assert os.path.normcase(actual['executable'])==os.path.normcase(identity['executable']),'Executable changed'
        if not k.TerminateProcess(handle,0):raise C.WinError(C.get_last_error())
        assert k.WaitForSingleObject(handle,5000)==0,'Owned fixture did not exit'
        return dict(status='EXITED_VERIFIED_OWNED_DIAGNOSTIC_PROCESS',identity=actual)
    finally:k.CloseHandle(handle)
