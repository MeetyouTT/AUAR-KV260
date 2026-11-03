"""Prepare and hash the four 汐蓝 demo lines in the selected voice."""
import argparse
import json
from pathlib import Path
import sys
AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from board.runtime.character import CHARACTER_NAME,DEMO_LINES
from tools.selected_voice_service import VoiceWorker

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=AURA.parent/'deliverables/2026-10-06_xilan_live');args=parser.parse_args()
    worker=VoiceWorker(args.root);records=[]
    try:
        for index,line in enumerate(DEMO_LINES):
            result=worker.generate(line['text']);records.append(dict(index=index,**line,**result))
            print(json.dumps({key:records[-1][key] for key in ('index','text','duration_seconds','generation_seconds','cache_hit')},ensure_ascii=False),flush=True)
        (args.root/'voice_manifest.json').write_text(json.dumps({'character':CHARACTER_NAME,'voice':'柔亮俏皮','clips':records},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:worker.close()

if __name__=='__main__':main()
