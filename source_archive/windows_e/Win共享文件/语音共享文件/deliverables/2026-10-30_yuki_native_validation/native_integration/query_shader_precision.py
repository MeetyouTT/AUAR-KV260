from pathlib import Path
import ctypes as C,json,sys
root=Path('/home/root/aura-yuki-validation-20261030')
sys.path.insert(0,str(root/'probe_build'))
from gles2_capture import EGL
context=EGL()
try:
    gl=C.CDLL('libGLESv2.so.2');gl.glGetShaderPrecisionFormat.argtypes=[C.c_uint,C.c_uint,C.POINTER(C.c_int),C.POINTER(C.c_int)]
    result={}
    for name,key in [('low_float',0x8DF0),('medium_float',0x8DF1),('high_float',0x8DF2)]:
        span=(C.c_int*2)();precision=C.c_int();gl.glGetShaderPrecisionFormat(0x8B30,key,span,C.byref(precision))
        result[name]={'range':list(span),'precision':precision.value}
    (root/'native_integration/shader-precision.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:context.close()
