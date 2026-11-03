import ctypes,ctypes.util,json,os,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
assert Path('/sys/class/drm/card0-DP-1/dpms').read_text().strip()=='On'
class Request(ctypes.Structure):
 _fields_=[('type',ctypes.c_uint),('sequence',ctypes.c_uint),('signal',ctypes.c_ulong)]
class Reply(ctypes.Structure):
 _fields_=[('type',ctypes.c_uint),('sequence',ctypes.c_uint),('sec',ctypes.c_long),('usec',ctypes.c_long)]
class Vblank(ctypes.Union):
 _fields_=[('request',Request),('reply',Reply)]
assert ctypes.sizeof(Vblank)==24
drm=ctypes.CDLL(ctypes.util.find_library('drm'),use_errno=True)
drm.drmWaitVBlank.argtypes=[ctypes.c_int,ctypes.POINTER(Vblank)];drm.drmWaitVBlank.restype=ctypes.c_int
def irq():return [s.strip() for s in Path('/proc/interrupts').read_text().splitlines() if 'fd4a0000' in s]
before=irq();fd=os.open('/dev/dri/card0',os.O_RDONLY|os.O_CLOEXEC)
try:
 value=Vblank();value.request.type=1;value.request.sequence=1
 started=time.monotonic();rc=drm.drmWaitVBlank(fd,ctypes.byref(value));elapsed=time.monotonic()-started
 error=ctypes.get_errno()
finally:os.close(fd)
print(json.dumps({'scope':'wait one vblank; no modeset, pixel write or DP training request',
 'exit_code':rc,'errno':error,'elapsed_seconds':elapsed,'returned_sequence':value.reply.sequence,
 'irq_before':before,'irq_after':irq()}))
