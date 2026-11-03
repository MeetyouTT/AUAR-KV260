"""Supplementary hand-region diagnostic; not pose tracking or an acceptance gate."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def center(path):
    with Image.open(path) as im:
        a=np.asarray(im.convert('RGB'),dtype=np.float32)[540:770,300:555]
    r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    mask=(r>100)&(r-g>10)&(g-b>0)&(r-b>18)
    yy,xx=np.nonzero(mask)
    return [float(xx.mean()+300),float(yy.mean()+540)] if len(xx) else None


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--batch-root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    rows=[]
    for d in sorted((args.batch_root/'raw').iterdir()):
        if not d.is_dir():continue
        points=[center(p) for p in sorted(d.glob('*.png'))]
        if any(p is None for p in points):
            rows.append({'id':d.name,'status':'MASK_FAILED'});continue
        offsets=np.asarray(points)-points[0]
        distances=np.linalg.norm(offsets,axis=1)
        i=int(distances.argmax())
        rows.append({'id':d.name,'max_skin_centroid_shift_source_px':round(float(distances[i]),2),
                     'max_frame':i,'offset_at_max':[round(float(v),2) for v in offsets[i]],
                     'centers':points})
    report={'method':'skin-color centroid in fixed raw-image ROI x300:555 y540:770',
            'caution':'Measures region appearance displacement, not anatomical wrist landmarks. Shadows and finger shape affect it. Do not use as an independent pass/fail threshold.',
            'rows':rows}
    args.out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    for r in rows: print(r['id'],r.get('max_skin_centroid_shift_source_px'),r.get('max_frame'))

if __name__=='__main__':main()
