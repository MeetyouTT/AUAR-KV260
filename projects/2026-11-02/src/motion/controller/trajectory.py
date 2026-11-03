"""Local one-axis Ruckig velocity solver; all authority remains in the session."""
import ctypes,hashlib,math
from pathlib import Path


class Trajectory:
    def __init__(self,path,digest):
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise RuntimeError('Trajectory library changed')
        self.lib=ctypes.CDLL(str(path));self.f=self.lib.aura_trajectory_step
        self.f.argtypes=[ctypes.c_double,ctypes.POINTER(ctypes.c_double),ctypes.c_double,
                        ctypes.c_double,ctypes.c_double,ctypes.c_double,ctypes.POINTER(ctypes.c_double)]
        self.f.restype=ctypes.c_int

    def step(self,pva,desired,dt,config):
        current=(ctypes.c_double*3)(*pva);out=(ctypes.c_double*3)()
        result=self.f(dt,current,desired,config.maximum_speed_us_s,
                      config.maximum_acceleration_us_s2,config.maximum_jerk_us_s3,out)
        if result or not all(math.isfinite(x) for x in out):raise RuntimeError('Trajectory solver rejected state: '+str(result))
        return list(out)
