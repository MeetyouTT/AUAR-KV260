from pathlib import Path
import ctypes as C,json,sys
import numpy as np
from PIL import Image
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');base=phase.parent;out=phase/'results/precision'
out.mkdir(exist_ok=True)
sys.path.insert(0,str(base/'probe_build'))
from gles2_capture import EGL
def pixels(path):return np.array(Image.open(str(path)).convert('RGB')).astype(np.int16)
def bounds(image):
    y,x=np.nonzero(np.any(np.abs(image-np.array([252,252,243]))>8,axis=2))
    return [int(x.min()),int(y.min()),int(x.max()),int(y.max())] if x.size else None
context=EGL();results=[]
try:
    api=C.CDLL(str(phase/'build_host/libaura_yuki.so'))
    api.yuki_diagnostic_error.restype=C.c_char_p
    api.yuki_diagnostic_parameters.argtypes=[C.c_char_p]*5+[C.c_int]*2;api.yuki_diagnostic_parameters.restype=C.c_int
    api.yuki_diagnostic_geometry.argtypes=[C.c_char_p]*4+[C.c_int]*2;api.yuki_diagnostic_geometry.restype=C.c_int
    for name in ('normal','smile','angry','sad','concern','shy','pose0','pose1','extreme0','extreme1'):
        output=out/(name+'.png');parameters=phase/'bp_diagnostic'/(name+'-parameters.json')
        assets=phase/'runtime_assets'
        ok=api.yuki_diagnostic_parameters(*(str(x).encode() for x in (assets/'model.runtime.json',assets/'yuk_0.ems.resx.json',assets,parameters,output)),423,438)
        if not ok:raise RuntimeError(api.yuki_diagnostic_error().decode())
        reference=phase/'native_references'/((name if name.startswith(('pose','extreme')) else 'face-'+name)+'.png')
        a=pixels(reference);b=pixels(output);delta=np.abs(a-b);ba=bounds(a);bb=bounds(b)
        box_error=max(abs(x-y) for x,y in zip(ba,bb)) if ba and bb else 999
        foreground=np.any(np.abs(a-np.array([252,252,243]))>8,axis=2)
        row=dict(case=name,mae=float(delta.mean()),foreground_mae=float(delta[foreground].mean()),
          pixels_over_20=int(np.any(delta>20,axis=2).sum()),reference_bounds=ba,native_bounds=bb,bounds_error=box_error)
        # Source-specific cross-driver picture gate, set before examining this result.
        row['pass']=row['mae']<1.0 and box_error<=2
        results.append(row)
    masks=[]
    for name in ('motion_self','sprite_self','ordinary_child','other_stencil'):
        folder=phase/'mask_fixtures'/name;output=out/(name+'.png')
        ok=api.yuki_diagnostic_geometry(*(str(x).encode() for x in (folder/'model.json',folder/'model.resx.json',folder,output)),423,438)
        if not ok:raise RuntimeError(api.yuki_diagnostic_error().decode())
        a=pixels(phase/'native_references'/(name.replace('_','-')+'-reference-lossless.png'));b=pixels(output);delta=np.abs(a-b)
        middle=a[3:-3,3:-3];interior=np.ones(middle.shape[:2],dtype=bool)
        for dx in range(-2,3):
            for dy in range(-2,3):interior &= np.all(middle==a[3+dy:a.shape[0]-3+dy,3+dx:a.shape[1]-3+dx],axis=2)
        errors=int(np.any(delta[3:-3,3:-3]>2,axis=2)[interior].sum());mae=float(delta.mean())
        masks.append(dict(case=name,mae=mae,interior_errors=errors,pass_=errors==0 and mae<.8))
    report=dict(status='PASS' if all(x['pass'] for x in results) and all(x['pass_'] for x in masks) else 'FAIL',
      images=results,masks=masks,reference='lossless original FreeMote full-model source;57 synced variables;same423x438 engine viewport;zero-offset Canvas2D copy',
      profile='source frame mesh, retained raw author tables; no second deformation',
      sampler='per-icon local UV, original two-pixel atlas neighbours',production_deployed=False)
    (phase/'results/precision-images.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
    if report['status']!='PASS':raise SystemExit(2)
finally:context.close()
