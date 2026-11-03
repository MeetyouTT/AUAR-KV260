"""Read-only contact sheets and actual script source positions for mouth inspection."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw

from preview_script import AURA,ScriptRunner
from tools.demo_script import create_demo_core

HERE=Path(__file__).resolve().parent


def sheet(images,labels,path):
    columns=8;w=160;h=150
    canvas=Image.new('RGB',(columns*w,math.ceil(len(images)/columns)*h),'#eef2f3')
    draw=ImageDraw.Draw(canvas)
    for i,(image,label) in enumerate(zip(images,labels)):
        x=i%columns*w;y=i//columns*h
        canvas.paste(image.crop((178,89,278,177)).convert('RGB').resize((160,130)),(x,y+20))
        draw.text((x+3,y+3),label,fill='#172b38')
    canvas.save(path)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',default='before_speech_fix');args=parser.parse_args()
    target=HERE/'speech_review';target.mkdir(exist_ok=True)
    for name in ('talking_normal','talking_normal_b','talking_low'):
        images=[]
        for path in sorted((AURA/'assets/avatar'/name).glob('*.png')):
            with Image.open(path) as image:images.append(image.convert('RGBA'))
        sheet(images,[f'{name} {i:02d}' for i in range(len(images))],target/(name+'_faces.png'))
    picks=[12,13,14,16,17,20,22,28,35,41,42,45,46,47,49,52,53,55,57,58]
    images=[];labels=[];positions=[]
    core=create_demo_core();core.idle_gain=0
    class Inspector(ScriptRunner):
        def _sample(self,t):
            meta=super()._sample(t)
            if meta is not None:
                positions.append({k:meta.get(k) for k in ('display_state','target_state','asset','source_position','stage','alpha') }|{'t':t})
                if picks and t>=picks[0]:
                    labels.append(f'{picks.pop(0):.1f}s {meta.get("display_state")} f{meta.get("source_position",0):.1f}')
                    images.append(meta['image'].copy())
            return meta
    runner=Inspector(core,dt=1/30);trace=runner.run(quiet=True)
    assert not trace.errors and not trace.rejected
    sheet(images,labels,target/(args.prefix+'_timeline_faces.png'))
    (target/(args.prefix+'_positions.json')).write_text(json.dumps(positions,indent=2),encoding='utf-8')
    print(str(target))


if __name__=='__main__':main()
