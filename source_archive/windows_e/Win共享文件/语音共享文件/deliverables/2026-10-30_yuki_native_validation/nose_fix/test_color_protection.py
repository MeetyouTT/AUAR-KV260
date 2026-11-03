"""Actual GLES2 regression: a translucent overlay on opaque color must not bleach it."""
from pathlib import Path
import importlib.util
import json
from PIL import Image

ROOT = Path('/home/root/aura-yuki-validation-20261030')
OUTPUT = ROOT/'nose-fix-tests'


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exercise(module, label, base, overlay, number):
    assets=ROOT/'inputs/ems/nose-fix-tests'
    assets.mkdir(exist_ok=True)
    Image.new('RGBA',(1,1),tuple(base)+(255,)).save(assets/'base.png')
    Image.new('RGBA',(1,1),tuple(overlay)).save(assets/'overlay.png')
    document={'texture_bindings':[
        {'id':1,'path':'nose-fix-tests/base.png'},
        {'id':2,'path':'nose-fix-tests/overlay.png'}]}
    w,h=module.W,module.H
    frame={'vertices':[[0,0,0,0,1,1,1,1],[w,0,1,0,1,1,1,1],
                       [w,h,1,1,1,1,1,1],[0,h,0,1,1,1,1,1]],
           'indices':[0,1,2,0,2,3,0,1,2,0,2,3],
           'commands':[{'texture':1,'first_index':0,'index_count':6,'blend':0,'protection':0,'mask':0},
                       {'texture':2,'first_index':6,'index_count':6,'blend':0,'protection':1,'mask':0}],
           'composition':1,'mask_commands':[],'masks':[]}
    context=module.EGL()
    try:
        g=module.GL();renderer=module.Renderer(g,document)
        path=OUTPUT/f'{label}-{number}.png'
        renderer.render(frame,(0,0,1),path)
        with Image.open(path) as image:actual=list(image.getpixel((w//2,h//2))[:3])
    finally:context.close()
    alpha=overlay[3]/255
    expected=[round(overlay[k]*alpha+base[k]*(1-alpha)) for k in range(3)]
    error=max(abs(a-b) for a,b in zip(actual,expected))
    return {'actual_rgb':actual,'expected_rgb':expected,'maximum_error':error,'pass':error<=2}


def main():
    OUTPUT.mkdir(exist_ok=True)
    old=load('gles_before',ROOT/'nose_fix/gles2_capture_before.py')
    fixed=load('gles_fixed',ROOT/'probe_build/gles2_capture.py')
    cases=[([153,102,51],[255,255,255,64]),
           ([100,130,160],[240,200,180,128]),
           ([30,200,30],[255,255,255,16])]
    rows=[]
    for index,(base,overlay) in enumerate(cases):
        rows.append({'base_rgb':base,'overlay_rgba':overlay,
                     'before':exercise(old,'before',base,overlay,index),
                     'fixed':exercise(fixed,'fixed',base,overlay,index)})
    report={'hardware':'actual board GLES2','integration_path':'Renderer.render protected straight prepass + final composite',
            'cases':rows,'before_failed':sum(not r['before']['pass'] for r in rows),
            'fixed_passed':sum(r['fixed']['pass'] for r in rows)}
    (OUTPUT/'regression.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    assert report['before_failed']==3 and report['fixed_passed']==3


if __name__=='__main__':main()
