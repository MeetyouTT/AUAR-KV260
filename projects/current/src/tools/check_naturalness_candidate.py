"""Candidate structural gate and motion diagnostics; never approves visual quality."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def inspect(directory, max_body_mad=None, max_area_range=None):
    errors=[]
    try:
        meta=json.loads((directory/'meta.json').read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        return {'status':'FAIL','errors':['invalid meta.json: %s'%exc]}
    paths=sorted(directory.glob('*.png'))
    if len(paths)!=39: errors.append('candidate requires 39 source frames, found %d'%len(paths))
    if meta.get('fps')!=24: errors.append('candidate requires fps=24')
    if meta.get('frames')!=len(paths): errors.append('meta.frames differs from PNG count')
    images=[]
    for path in paths:
        try:
            with Image.open(path) as im:
                if im.mode!='RGBA': errors.append('%s must contain RGBA alpha'%path.name)
                if im.size!=(464,480): errors.append('%s must be 464x480'%path.name)
                images.append(im.convert('RGBA'))
        except OSError:
            errors.append('unreadable PNG: %s'%path.name)
    if errors:
        return {'status':'FAIL','errors':errors}
    arrays=[]; areas=[]
    for im in images:
        areas.append(int((np.asarray(im.getchannel('A'))>100).sum()))
        small=im.resize((116,120),Image.Resampling.BILINEAR)
        bg=Image.new('RGBA',small.size,(252,252,243,255)); bg.alpha_composite(small)
        arrays.append(np.asarray(bg.convert('RGB'),dtype=np.float32))
    diffs=[float(np.abs(a-b).mean()) for a,b in zip(arrays,arrays[1:])]
    body=[float(np.abs(a[40:]-b[40:]).mean()) for a,b in zip(arrays,arrays[1:])]
    area_range=(max(areas)-min(areas))/max(1.0,float(np.mean(areas)))
    if max_body_mad is not None and max(body)>max_body_mad:
        errors.append('body movement exceeds the requested diagnostic ceiling')
    if max_area_range is not None and area_range>max_area_range:
        errors.append('alpha area variation exceeds the requested diagnostic ceiling')
    if not min(areas): errors.append('empty foreground frame')
    if sum(p.stat().st_size for p in paths)>12.5*1024*1024:
        errors.append('PNG budget exceeds 12.5 MiB')
    return {'status':'FAIL' if errors else 'STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW',
        'errors':errors,'frames':len(paths),'fps':meta['fps'],
        'max_adjacent_pixel_mad':max(diffs),'max_body_pixel_mad':max(body),
        'first_last_pixel_mad':float(np.abs(arrays[0]-arrays[-1]).mean()),
        'alpha_area_range_over_mean':area_range,'worst_pair':[int(np.argmax(diffs)),int(np.argmax(diffs))+1],
        'note':'MAD is a 116x120 RGB diagnostic (0..255), not a percentage or perceptual score. Body ROI is lower two thirds; alpha area is not a true body-scale measurement. Manual review required.'}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path)
    ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--max-body-mad',type=float)
    ap.add_argument('--max-area-range',type=float)
    args=ap.parse_args(argv)
    report=inspect(args.directory,args.max_body_mad,args.max_area_range)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(report['status'])
    return 1 if report['status']=='FAIL' else 0

if __name__=='__main__': raise SystemExit(main())
