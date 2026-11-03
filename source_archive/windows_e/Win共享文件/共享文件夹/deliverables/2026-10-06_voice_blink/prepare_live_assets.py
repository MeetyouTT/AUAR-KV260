"""Export existing local mouth keys and shared eye schedule for the live player."""
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

HERE=Path(__file__).resolve().parent
AURA=HERE.parent.parent/'aura';sys.path.insert(0,str(AURA))
from tools.demo_script import create_demo_core
from tools.facial_layers import MouthBank,BlinkSchedule,BlinkLayer


def main():
    core=create_demo_core('reuse');bank=MouthBank(core);eyes=BlinkLayer();tiles=[];mouths={}
    for name,keys in bank.keys.items():
        records=[]
        for aperture,image in keys:
            slot=len(tiles);tiles.append(image)
            records.append({'level':aperture,'slot':slot})
        mouths[name]=records
    columns=4;rows=(len(tiles)+columns-1)//columns
    sheet=Image.new('RGB',(464*columns,480*rows),'#FCFCF3')
    for i,image in enumerate(tiles):
        tile=Image.new('RGBA',image.size,'#FCFCF3');tile.alpha_composite(image)
        sheet.paste(tile.convert('RGB'),(i%columns*464,i//columns*480))
    assets=HERE/'assets';assets.mkdir(exist_ok=True);sheet.save(assets/'mouths.webp','WEBP',lossless=True,method=3)
    document={'width':464,'height':480,'columns':columns,'mouth_sheet':'assets/mouths.webp',
              'mouths':mouths,'blink':{'starts':BlinkSchedule().starts,'duration':.29,'times':eyes.profile['times'],
                                     'bounds':eyes.profile['bounds'],'aliases':eyes.ALIASES,
                                     'targets':{name:{'layers':data['layers']} for name,data in eyes.profile['targets'].items()}},
              'mouth_sheet_sha256':hashlib.sha256((assets/'mouths.webp').read_bytes()).hexdigest()}
    (HERE/'live_assets.json').write_text(json.dumps(document,indent=2),encoding='utf-8')
    print(json.dumps({'mouth_sets':len(mouths),'mouth_keys':len(tiles),'bytes':(assets/'mouths.webp').stat().st_size}),flush=True)


if __name__=='__main__':main()
