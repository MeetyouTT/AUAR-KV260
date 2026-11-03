"""Untimed regression: caller GL state and resize cannot poison the next draw."""
from pathlib import Path
import ctypes as C,json,sys
from PIL import Image
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');base=phase.parent
sys.path.insert(0,str(base/'probe_build'))
sys.path.insert(0,str(phase/'host'))
from gles2_capture import EGL
from native_yuki import Native,Control
assert json.loads((phase/'results/precision-validation-result.json').read_text())['status']=='PASS'
out=phase/'results/state-cache';out.mkdir(exist_ok=True);assets=phase/'runtime_assets'
context=EGL();native=None
try:
    native=Native(phase/'build_host/libaura_yuki.so',assets/'model.runtime.json',assets/'yuk_0.ems.resx.json',assets)
    assert native.offer(Control(1,1,0,24000,0,0,0,0,0,0,0,1000))
    native.render(1000,423,438);native.capture(out/'baseline.png',423,438)
    gl=C.CDLL('libGLESv2.so.2')
    gl.glClearColor.argtypes=[C.c_float]*4;gl.glColorMask.argtypes=[C.c_ubyte]*4
    gl.glViewport.argtypes=[C.c_int]*4;gl.glScissor.argtypes=[C.c_int]*4
    # All mutations occur in this private context, never in the running UI.
    gl.glActiveTexture(0x84C0);gl.glBindTexture(0x0DE1,0)
    gl.glActiveTexture(0x84C1);gl.glBindTexture(0x0DE1,0)
    gl.glEnable(0x0C11);gl.glScissor(0,0,1,1);gl.glViewport(1,1,1,1)
    gl.glClearColor(1,0,1,1);gl.glColorMask(0,0,0,0);gl.glBlendFunc(1,0)
    native.render(1000,423,438);native.capture(out/'after-caller-state.png',423,438)
    native.render(1000,320,320);native.capture(out/'smaller-target.png',320,320)
    native.render(1000,423,438);native.capture(out/'after-resize.png',423,438)
    original=Image.open(out/'baseline.png').convert('RGBA').tobytes()
    checks={name:Image.open(out/(name+'.png')).convert('RGBA').tobytes()==original for name in ('after-caller-state','after-resize')}
    report=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
      comparisons='pixel exact within same native model instance, fixed author time; private context',production_deployed=False)
    (phase/'results/state-cache.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
    assert report['status']=='PASS'
finally:
    if native:native.close()
    context.close()
