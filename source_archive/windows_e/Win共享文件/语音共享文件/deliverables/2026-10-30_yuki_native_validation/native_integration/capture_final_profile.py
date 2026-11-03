"""Untimed visual evidence only; never mix PNG readback with performance data."""
from pathlib import Path
import ctypes as C,json,sys
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');base=root.parent
sys.path.insert(0,str(root/'host'));sys.path.insert(0,str(base/'probe_build'))
from native_yuki import Native,Control
from gles2_capture import EGL
assert json.loads((root/'results/precision-validation-result.json').read_text())['status']=='PASS'
out=root/'results/final-profile';out.mkdir(exist_ok=True)
assets=root/'runtime_assets';context=EGL();native=None
try:
    api=C.CDLL(str(root/'build_host/libaura_yuki.so'))
    api.yuki_diagnostic_frames.argtypes=[C.c_char_p]*5+[C.c_int]*2
    api.yuki_diagnostic_frames.restype=C.c_int;api.yuki_diagnostic_error.restype=C.c_char_p
    count=api.yuki_diagnostic_frames(*(str(x).encode() for x in (assets/'model.runtime.json',assets/'yuk_0.ems.resx.json',assets,root/'results/final-profile-frames.json',out/'scenario')),423,438)
    if count<=0:raise RuntimeError(api.yuki_diagnostic_error().decode())
    native=Native(root/'build_host/libaura_yuki.so',assets/'model.runtime.json',assets/'yuk_0.ems.resx.json',assets,seed=1)
    clip=out/'idle-expression';clip.mkdir(exist_ok=True);rows=[]
    # Deterministic author time; capture speed deliberately not described as real-time FPS.
    for i in range(135):
        now=1000+i/15;expression=(0,1,5)[min(2,i//45)]
        assert native.offer(Control(1,i+1,0,24000,0,0,0,expression,0,0,0,now))
        stats=native.render(now,423,438);native.capture(clip/(str(i).zfill(4)+'.png'),423,438)
        rows.append(dict(frame=i,author_time=i/15,**stats))
    (out/'capture.json').write_text(json.dumps(dict(scenario_frames=count,clip_frames=135,clip_fps=15,duration=9,
      purpose='untimed direct native GLES2 visual evidence; no audio/device; physics enabled',frames=rows),indent=2))
    print(json.dumps(dict(scenario_frames=count,clip_frames=135,performance_claim=False)))
finally:
    if native:native.close()
    context.close()
