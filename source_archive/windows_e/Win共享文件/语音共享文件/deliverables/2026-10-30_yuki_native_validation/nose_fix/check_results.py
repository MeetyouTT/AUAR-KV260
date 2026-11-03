from pathlib import Path
import hashlib
import json
import math
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence'
source=json.loads((ROOT/'inputs/ems/yuk_0.ems.json').read_text(encoding='utf-8-sig'))
extent=source['source']['tex']['texture']
expected_uv=[]
for label in ['0000','0001']:
    icon=source['source']['tex']['icon'][label]
    expected_uv.append([icon['left']/extent['width'],icon['top']/extent['height'],
                        (icon['left']+icon['width'])/extent['width'],
                        (icon['top']+icon['height'])/extent['height']])
markers=source['metadata']['charaProfile']['pixelMarker']
left,top,right,bottom=[markers[k] for k in ['boundsLeft','boundsTop','boundsRight','boundsBottom']]
bottom=top+(bottom-top)*.48
scale=min(423/(right-left),438/(bottom-top))*.88
ox,oy=423/2-(left+right)/2*scale,438/2-(top+bottom)/2*scale


def nose_box(frame):
    matches=[]
    for command in frame['commands']:
        vertices=np.array([frame['vertices'][i] for i in frame['indices'][command['first_index']:command['first_index']+command['index_count']]])
        uv=[vertices[:,2].min(),vertices[:,3].min(),vertices[:,2].max(),vertices[:,3].max()]
        if min(np.max(np.abs(np.array(uv)-candidate)) for candidate in expected_uv)<1e-6:
            x0=math.floor(vertices[:,0].min()*scale+ox)-1
            y0=math.floor(vertices[:,1].min()*scale+oy)-1
            x1=math.ceil(vertices[:,0].max()*scale+ox)+1
            y1=math.ceil(vertices[:,1].max()*scale+oy)+1
            matches.append([max(0,x0),max(0,y0),min(423,x1),min(438,y1)])
    assert len(matches)==1, matches
    return matches[0]


rows=[]
for document,before_dir,after_dir in [
    ('candidate-frames.json','candidate-captures','nose-fix-captures'),
    ('static-reference-frames.json','static-reference-captures','nose-fix-static')]:
    data=json.loads((EVIDENCE/document).read_text(encoding='utf-8'))
    for scenario in data['scenarios']:
        for snapshot in scenario['snapshots']:
            name=scenario['name']+'-'+str(snapshot['tick']).zfill(4)+'.png'
            box=nose_box(snapshot['frame'])
            first=EVIDENCE/before_dir/name;second=EVIDENCE/after_dir/name
            with Image.open(str(first)) as im:before=np.array(im.convert('RGB').crop(box))
            with Image.open(str(second)) as im:after=np.array(im.convert('RGB').crop(box))
            rows.append({'image':name,'nose_box':box,
                         'before_near_white_pixels':int((before.min(axis=2)>=248).sum()),
                         'after_near_white_pixels':int((after.min(axis=2)>=248).sum()),
                         'after_path':second.relative_to(ROOT).as_posix(),
                         'after_sha256':hashlib.sha256(second.read_bytes()).hexdigest()})
run=json.loads((EVIDENCE/'nose-fix-run-result.json').read_text())
regression=json.loads((EVIDENCE/'nose-fix-tests/regression.json').read_text())
assert run['ok'] and run['ui_unchanged'] and run['protected_files_changed']==[]
assert regression['before_failed']==3 and regression['fixed_passed']==3
assert len(rows)==43
example=next(r for r in rows if r['image']=='blink_mouth-0073.png')
assert example['before_near_white_pixels']>example['after_near_white_pixels']
report={'status':'NOSE_WHITE_BLOB_FIXED_IN_DIAGNOSTIC_RENDERER',
        'cause':'ProtectedStraight prepass incorrectly used GL_ONE_MINUS_DST_COLOR (0x0307); corrected to GL_ONE_MINUS_DST_ALPHA (0x0305).',
        'constant_reference':'https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/main/api/GLES2/gl2.h',
        'model_or_texture_modified':False,'geometry_core_modified_for_this_fix':False,
        'same_input_frames_reused':True,'gpu_regression_before_failures':3,'gpu_regression_fixed_passes':3,
        'frames_rerendered':len(rows),'example':example,
        'total_near_white_nose_pixels_before':sum(r['before_near_white_pixels'] for r in rows),
        'total_near_white_nose_pixels_after':sum(r['after_near_white_pixels'] for r in rows),
        'renderer_sha256':run['renderer_sha256'],'production_ui_unchanged':True,
        'protected_files_checked':run['protected_files_checked'],'protected_files_changed':[],
        'production_deployed':False,'overall_model_compatibility_accepted':False,
        'before_renderer':'nose_fix/gles2_capture_before.py','frames':rows}
(ROOT/'nose_fix/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
verification=json.loads((ROOT/'verification.json').read_text(encoding='utf-8'))
verification['nose_color_correction']={k:v for k,v in report.items() if k!='frames'}
(ROOT/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('frames','cause','constant_reference')},ensure_ascii=False))
