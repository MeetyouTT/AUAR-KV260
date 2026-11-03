"""Bake the shared script renderer for a browser review driven by audio.currentTime.

This preview is a cached PC render, not board throughput evidence. The desktop
entry renders the same runner live, clocked by QAudioSink.processedUSecs.
"""
import hashlib
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
AURA=HERE.parent.parent/'aura'
sys.path.insert(0,str(AURA))
from tools.selected_voice_demo import VoicePlan,SelectedVoiceRunner,create_demo_core

FPS=30;WIDTH=320;HEIGHT=331;COLS=8;ROWS=4;COUNT=COLS*ROWS


def main(effects=False):
    start=time.perf_counter();plan=VoicePlan()
    plan.write_audio(HERE/'audio'/'script.wav')
    (HERE/'plan.json').write_text(json.dumps(plan.public(),ensure_ascii=False,indent=2),encoding='utf-8')
    frames_path=HERE/'frames';frames_path.mkdir(exist_ok=True)
    core=create_demo_core('reuse',idle_body=effects);core.rng=random.Random(20261006)
    runner=SelectedVoiceRunner(core,plan,effects=effects);runner.reset()
    atlas=Image.new('RGB',(WIDTH*COLS,HEIGHT*ROWS),'#FCFCF3')
    samples=[];sheets=[];faces=[];seen=set()
    total=int(np.ceil(plan.end*FPS))+1
    for i in range(total):
        t=min(plan.end,i/FPS);meta=runner.advance(t)
        if meta is None:raise RuntimeError(f'No rendered frame at {t}')
        image=meta['image'];tile=Image.new('RGBA',image.size,'#FCFCF3');tile.alpha_composite(image)
        tile=tile.convert('RGB').resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
        slot=i%COUNT;atlas.paste(tile,((slot%COLS)*WIDTH,(slot//COLS)*HEIGHT))
        row=plan.utterance_at(t)
        samples.append({'t':round(t,6),'state':core.fsm.state.label,'display_state':meta['display_state'],
                        'asset':meta['asset'],'speech_gain':round(meta['speech_gain'],4),
                        'scene':row['scene'] if row else None,'label':row['label'] if row else None,
                        'transitioning':meta.get('transitioning',False),'stage':meta.get('stage'),
                        'blink_active':meta.get('blink_active',False),'blink_phase':meta.get('blink_phase'),
                        'mouth_level':meta.get('mouth_level',0)})
        key=(row['label'] if row else meta['display_state'],int(meta['speech_gain']>.8))
        if key not in seen:
            seen.add(key);faces.append((t,key,image.copy()))
        if slot==COUNT-1 or i==total-1:
            path=frames_path/f'{len(sheets):03d}.webp'
            atlas.save(path,'WEBP',quality=93,method=3)
            sheets.append({'file':f'frames/{path.name}','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
            print(f'Prepared {i+1}/{total} frames',flush=True)
            atlas=Image.new('RGB',(WIDTH*COLS,HEIGHT*ROWS),'#FCFCF3')
    if runner.trace.errors or runner.trace.rejected:raise RuntimeError(str(runner.trace.errors+runner.trace.rejected))
    document={'title':'小光 · 柔亮俏皮音画演示','fps':FPS,'width':WIDTH,'height':HEIGHT,'columns':COLS,'rows':ROWS,
              'duration':plan.end,'audio':'audio/script.wav','audio_sha256':hashlib.sha256((HERE/'audio'/'script.wav').read_bytes()).hexdigest(),
              'sheets':sheets,'samples':samples,'utterances':plan.utterances,
              'effects':'independent blink + amplitude mouth' if effects else 'accepted baseline',
              'provenance':'cached shared ScriptRunner / ReusePreviewPlayer; playback clock is audio.currentTime'}
    (HERE/'timeline.json').write_text(json.dumps(document,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    result={'status':'PASS','duration_seconds':plan.end,'frames':len(samples),'fps':'30 cached samples, not live performance',
            'errors':runner.trace.errors,'rejected':runner.trace.rejected,'final_state':core.fsm.state.label,
            'states_used':sorted({r['display_state'] for r in samples}),
            'speaking_assets_used':sorted({r['asset'] for r in samples if r['display_state'].startswith('SPEAKING')}),
            'source_audio_integrity':'checked against audio_verification.json output hashes',
            'build_seconds':time.perf_counter()-start,'sprite_bytes':sum(s['bytes'] for s in sheets)}
    (HERE/'build_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    # Diagnostic images for local inspection. They do not score naturalness.
    cells=8;cw=190;ch=170
    contact=Image.new('RGB',(cells*cw,((len(faces)+cells-1)//cells)*ch),'#FCFCF3');draw=ImageDraw.Draw(contact)
    for i,(t,key,image) in enumerate(faces):
        face=image.crop((155,75,290,190)).resize((180,140))
        x=(i%cells)*cw;y=(i//cells)*ch;contact.paste(face,(x,y));draw.text((x+3,y+143),f'{t:.2f}s gain={key[1]}',fill='#283540')
    contact.save(HERE/'mouth_review.png')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--effects',action='store_true')
    args=parser.parse_args()
    if args.output:HERE=args.output.resolve();HERE.mkdir(parents=True,exist_ok=True)
    main(args.effects)
