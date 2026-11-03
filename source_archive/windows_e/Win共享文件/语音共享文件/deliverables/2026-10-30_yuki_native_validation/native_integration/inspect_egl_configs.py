from pathlib import Path
import ctypes as C,json,sys
root=Path('/home/root/aura-yuki-validation-20261030')
sys.path.insert(0,str(root/'probe_build'))
from gles2_capture import EGL
e=EGL();lib=e.e
try:
    lib.eglGetConfigs.argtypes=[C.c_void_p,C.POINTER(C.c_void_p),C.c_int,C.POINTER(C.c_int)];lib.eglGetConfigs.restype=C.c_int
    lib.eglGetConfigAttrib.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.POINTER(C.c_int)];lib.eglGetConfigAttrib.restype=C.c_int
    lib.eglQueryString.argtypes=[C.c_void_p,C.c_int];lib.eglQueryString.restype=C.c_char_p
    configs=(C.c_void_p*128)();count=C.c_int();assert lib.eglGetConfigs(e.d,configs,128,C.byref(count))
    result={'count':count.value,'vendor':lib.eglQueryString(e.d,0x3053).decode(),
      'extensions':lib.eglQueryString(e.d,0x3055).decode(),'configs':[]}
    for config in configs[:count.value]:
        row={}
        for name,key in (('id',0x3028),('surface',0x3033),('visual',0x302E),('r',0x3024),('g',0x3023),('b',0x3022),('a',0x3021),('renderable',0x3040)):
            value=C.c_int();assert lib.eglGetConfigAttrib(e.d,config,key,C.byref(value));row[name]=value.value
        result['configs'].append(row)
    (root/'native_integration/egl-configs.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:e.close()
