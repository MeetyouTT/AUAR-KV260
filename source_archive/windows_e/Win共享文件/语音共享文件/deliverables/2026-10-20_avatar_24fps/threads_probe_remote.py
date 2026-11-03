import sys,time,json,statistics,ctypes
from pathlib import Path
root=Path('/home/root/aura-render24-20261020/candidate-d310443d4f30/runtime');sys.path.insert(0,str(root/'aura'))
from tools.board_avatar_gtk import create_runtime_core
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.native_pixels import NativePixels
core=create_runtime_core(create_demo_core);native=NativePixels(root/'aura/tools/libaura_pixels.so');native.configure(core);facials=RealtimeFacials(core)
setter=getattr(native.lib,'_ZN2cv13setNumThreadsEi');setter.argtypes=[ctypes.c_int]
results={}
for n in (1,2,3,4):
 setter(n);rows=[];cpu=[]
 for i in range(96):
  t=4+i/24;b=time.perf_counter();facials.apply(core.frame_at('IDLE',t),t,.7,.6);rows.append((time.perf_counter()-b)*1000);cpu.append(native.cpu_times())
 rows.sort();results[n]={'p50':statistics.median(rows),'p95':rows[int(len(rows)*.95)],'max':max(rows),'kernels':{k:statistics.median([r[k] for r in cpu]) for k in cpu[0]}}
native.close();print(json.dumps(results))
