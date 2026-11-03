"""Fixed-crop inspection contact sheets; source and candidate PNGs are read-only."""
from pathlib import Path
import argparse
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
TARGET=HERE/'candidates/talking_calm_reuse_v1'
RAW=HERE.parent/'avatar_candidates/batch_003_guide_probe/raw/e2_rest_s421001_L124_guide62'


def main():
    global TARGET
    parser=argparse.ArgumentParser();parser.add_argument('--variant-b',action='store_true');args=parser.parse_args()
    if args.variant_b:TARGET=HERE/'candidates/talking_calm_reuse_v1_b'
    faces=Image.new('RGB',(8*180,5*172),'#eeeeee')
    d=ImageDraw.Draw(faces)
    for i in range(39):
        x,y=(i%8)*180,(i//8)*172
        d.text((x+5,y+4),f'frame {i:02d}',fill='black')
        with Image.open(TARGET/f'{i:06d}.png') as im:
            faces.paste(im.convert('RGB').crop((185,100,275,175)).resize((180,150),Image.Resampling.LANCZOS),(x,y+22))
    faces.save(HERE/('review_faces_b.png' if args.variant_b else 'review_faces.png'))
    canvas=Image.new('RGB',(6*232,302),'#edf1f3')
    draw=ImageDraw.Draw(canvas)
    for j,i in enumerate((0,19,38)):
        with Image.open(RAW/f'{i+(80 if args.variant_b else 0):06d}.png') as im:
            before=im.crop((0,0,864,891)).resize((232,240),Image.Resampling.LANCZOS)
        draw.text((j*232+6,5),f'Original frame {i+(80 if args.variant_b else 0)}',fill='black')
        canvas.paste(before,(j*232,26))
        with Image.open(TARGET/f'{i:06d}.png') as im:
            out=Image.new('RGBA',im.size,(237,241,243,255));out.alpha_composite(im)
            after=out.convert('RGB').resize((232,240),Image.Resampling.LANCZOS)
        x=(j+3)*232
        draw.text((x+6,5),f'Reuse frame {i}',fill='black')
        canvas.paste(after,(x,26))
    draw.text((8,277),'Left: source poses | Right: same body anchor, local mouth only',fill='black')
    canvas.save(HERE/('review_keyframes_b.png' if args.variant_b else 'review_keyframes.png'))
    print('review_faces.png, review_keyframes.png')


if __name__=='__main__':main()
