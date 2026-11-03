from pathlib import Path
import ctypes as C,json,sys
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');base=phase.parent
sys.path.insert(0,str(base/'probe_build'))
from gles2_capture import EGL
context=EGL()
try:
    api=C.CDLL(str(phase/'build_host/libaura_yuki.so'))
    api.yuki_diagnostic_parameters.argtypes=[C.c_char_p]*5+[C.c_int]*2;api.yuki_diagnostic_parameters.restype=C.c_int
    api.yuki_diagnostic_error.restype=C.c_char_p
    results=[]
    for name in ('normal','smile','angry','sad','concern','shy'):
        parameters=phase/('complete-'+name+'-parameters.json')
        output=phase/('results/complete-'+name+'-native.png')
        ok=api.yuki_diagnostic_parameters(*(str(x).encode() for x in (base/'inputs/ems/yuk_0.ems.json',base/'inputs/ems/yuk_0.ems.resx.json',base/'inputs/ems',parameters,output)),423,438)
        results.append({'expression':name,'ok':bool(ok),'error':api.yuki_diagnostic_error().decode() if not ok else None,'output':str(output)})
    (phase/'results/complete-parameter-render.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results))
    if not all(x['ok'] for x in results):raise SystemExit(1)
finally:context.close()
