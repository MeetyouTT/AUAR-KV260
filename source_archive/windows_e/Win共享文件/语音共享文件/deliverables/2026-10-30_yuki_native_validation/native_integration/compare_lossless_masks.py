from pathlib import Path
import json
from PIL import Image
import numpy as np
BASE=Path(__file__).parent.parent
report=[]
for name in ('motion_self','sprite_self','ordinary_child','other_stencil'):
    a=np.array(Image.open(str(BASE/'native_integration/mask_fixtures'/(name.replace('_','-')+'-reference-lossless.png'))).convert('RGB')).astype(np.int16)
    b=np.array(Image.open(str(BASE/'evidence/native_integration/results'/(name+'-native.png'))).convert('RGB')).astype(np.int16)
    delta=np.abs(a-b);middle=a[3:-3,3:-3];interior=np.ones(middle.shape[:2],dtype=bool)
    for dx,dy in ((dx,dy) for dx in range(-2,3) for dy in range(-2,3)):
        interior &= np.all(middle==a[3+dy:a.shape[0]-3+dy,3+dx:a.shape[1]-3+dx],axis=2)
    errors=int(np.any(delta[3:-3,3:-3]>2,axis=2)[interior].sum());mae=float(delta.mean())
    report.append(dict(name=name,mae=mae,interior_errors=errors,interior_checked=int(interior.sum()),pass_=errors==0 and mae<.8))
result={'fixtures':report,'pass':all(x['pass_'] for x in report),'reference_format':'lossless PNG from visible export UI',
 'threshold_unchanged':True,'flat_interior_definition':'all 25 pixels in radius-2 square equal; includes diagonal corner checks',
 'supersedes':'JPEG screenshot comparisons and cross-only corner classification, retained as failed/invalid evidence'}
(BASE/'native_integration/mask-lossless-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
