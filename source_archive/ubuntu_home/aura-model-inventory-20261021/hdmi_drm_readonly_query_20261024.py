import ctypes,ctypes.util,json,os
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
library=ctypes.util.find_library('drm');assert library
drm=ctypes.CDLL(library,use_errno=True)
drm.drmModeGetResources.argtypes=[ctypes.c_int];drm.drmModeGetResources.restype=ctypes.c_void_p
drm.drmModeFreeResources.argtypes=[ctypes.c_void_p];drm.drmModeFreeResources.restype=None
fd=os.open('/dev/dri/card0',os.O_RDONLY|os.O_CLOEXEC)
try:
 resources=drm.drmModeGetResources(fd)
 assert resources,os.strerror(ctypes.get_errno())
 drm.drmModeFreeResources(resources)
finally:os.close(fd)
symbols={line.split()[-1] for line in Path('/proc/kallsyms').read_text().splitlines() if len(line.split())>=3}
print(json.dumps({'scope':'read-only GETRESOURCES on explicit display node; no modeset',
 'resources_read':bool(resources),'driver_name':Path('/sys/kernel/debug/dri/0/name').read_text().split()[0],
 'train_symbol_present':'zynqmp_dp_train' in symbols,
 'module_present':Path('/sys/module/aura_dp_retrain_candidate').exists(),
 'kernel_probe_messages':[s for s in os.popen('dmesg').read().splitlines() if 'aura DP candidate' in s or 'kprobe' in s][-12:]}))
