"""Losslessly repack browser PNGs, then audit pixel invariants and source integrity."""
import hashlib
import argparse
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
TARGET=HERE/'candidates/talking_calm_reuse_v1'
SHARED=HERE.parent.parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    global TARGET
    parser=argparse.ArgumentParser();parser.add_argument('--variant-b',action='store_true');args=parser.parse_args()
    if args.variant_b:TARGET=HERE/'candidates/talking_calm_reuse_v1_b'
    profile=json.loads((HERE/'profile.json').read_text(encoding='utf-8'))
    files=sorted(TARGET.glob('*.png'))
    assert [p.name for p in files]==[f'{i:06d}.png' for i in range(39)]
    records=[]
    total_before=sum(p.stat().st_size for p in files)
    for p in files:
        with Image.open(p) as original:
            original.load()
            assert original.mode=='RGBA' and original.size==(464,480)
            pixels=original.tobytes()
            packed=io.BytesIO()
            original.save(packed,format='PNG',optimize=True,compress_level=9)
        with Image.open(io.BytesIO(packed.getvalue())) as decoded:
            assert decoded.mode=='RGBA' and decoded.tobytes()==pixels
        if len(packed.getvalue())<p.stat().st_size:p.write_bytes(packed.getvalue())
        records.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size})
    anchor=SHARED/'aura/assets/avatar/idle_normal/000000.png'
    assert sha(anchor)==profile['anchorSha256']
    raw=SHARED/'deliverables/avatar_candidates/batch_003_guide_probe/raw/e2_rest_s421001_L124_guide62'
    assert all(sha(raw/f"{r['frame']:06d}.png")==r['sha256'] for r in profile['frames'])
    with Image.open(files[0]) as im: first=np.asarray(im).astype(np.int16)
    with Image.open(files[-1]) as im: last=np.asarray(im).astype(np.int16)
    yy,xx=np.mgrid[:480,:464]
    outside=((xx+.5-225)/17)**2+((yy+.5-151)/12)**2>1.08**2
    delta_outside=0;delta_alpha=0;mouth_delta=0
    for p in files:
        with Image.open(p) as im: a=np.asarray(im).astype(np.int16)
        d=np.abs(a-first)
        delta_outside=max(delta_outside,int(d[outside].max()))
        delta_alpha=max(delta_alpha,int(d[:,:,3].max()))
        mouth_delta=max(mouth_delta,int(d[~outside].max()))
    assert np.array_equal(first,last)
    assert delta_outside<=1 and delta_alpha==0 and mouth_delta>20
    total_after=sum(r['bytes'] for r in records)
    assert total_after<=12.5*1024**2
    report={'frames':39,'size':[464,480],'fps':24,'lossless_pixel_identity_verified':True,
       'png_bytes_before':total_before,'png_bytes_after':total_after,'png_mib':total_after/1024**2,
       'within_12_5_mib':total_after<=12.5*1024**2,'first_last_pixels_equal':True,
       'max_outside_mouth_channel_delta':delta_outside,'max_alpha_delta':delta_alpha,'max_mouth_delta':mouth_delta,
       'all_124_source_frames_and_anchor_unchanged':True,
       'note':'Outside delta <=1 is Canvas straight/premultiplied alpha rounding; not pose movement. Exact alpha shape is stable. No naturalness score inferred.',
       'files':records}
    (HERE/('reuse_verification_b.json' if args.variant_b else 'reuse_verification.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))


if __name__=='__main__':main()
