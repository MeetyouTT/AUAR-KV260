"""Verify ARM library loading and mathematical bounds without actuator access."""
import ctypes,hashlib,json,time
from pathlib import Path
R=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v6')
manifest=json.loads((R/'deployment-manifest.json').read_text())
assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in manifest['files'])
lib=ctypes.CDLL(str(R/'libaura_trajectory.so'));f=lib.aura_trajectory_step
f.argtypes=[ctypes.c_double,ctypes.POINTER(ctypes.c_double),ctypes.c_double,ctypes.c_double,ctypes.c_double,ctypes.c_double,ctypes.POINTER(ctypes.c_double)];f.restype=ctypes.c_int
pva=[1469.,0.,0.];rows=[];begin=time.monotonic()
for n in range(300):
 current=(ctypes.c_double*3)(*pva);out=(ctypes.c_double*3)()
 desired=20. if n<100 else -20. if n<200 else 0.
 assert f(.02,current,desired,40.,80.,400.,out)==0
 assert abs(out[1])<=40.001 and abs(out[2])<=80.001 and abs(out[2]-pva[2])<=8.00001
 pva=list(out)
 if n%50==0:rows.append(pva)
print(json.dumps({'status':'V6_ARM_LIBRARY_PURE_MATH_PREFLIGHT_PASS','steps':300,'elapsed_ms':round((time.monotonic()-begin)*1000,3),
 'samples':rows,'final':pva,'ARM':0,'COMMIT':0,'MMIO_opened':False,'camera_restarted':False,'gui_restarted':False}))
