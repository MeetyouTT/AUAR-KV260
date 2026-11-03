"""Check public Chinese words after endpointing and enhancement, offline CPU only."""
import json,re,socket,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));from benchmark import make_cases,evaluate,SileroFrameGate,EXTERNAL,load,PROJECT
from board.runtime.audio.asr import AsrConfig,SherpaOfflineRecognizer


def distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current
    return previous[-1]


def normalized(text):return ''.join(re.findall(r'\w',text.casefold()))


def blocked(*a,**kw):raise RuntimeError('Network forbidden during offline ASR check')
socket.socket.connect=blocked
engine=SherpaOfflineRecognizer(AsrConfig(model_dir=str(PROJECT/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14'),num_threads=1))
cases,_=make_cases();rows=[]
for case in cases:
    if not any(case['name'].startswith(f'public_{n}_') for n in (4,5,6)):continue
    samples=case['samples']
    direct=normalized(engine.transcribe(samples))
    variants={}
    for name in ('energy','silero_vad.int8.onnx','silero_vad.onnx','silero_vad_v5.onnx'):
        gate=None if name=='energy' else SileroFrameGate(EXTERNAL/name)
        info=evaluate(samples,gate)
        pieces=[samples[round(a*16000):round(b*16000)] for a,b in info['segments']]
        segmented=''.join(normalized(engine.transcribe(x)) for x in pieces)
        variants[name]={'completed_segments':len(pieces),'still_active_at_end':info['still_active_at_end'],
                        'full_input_characters':len(direct),'segmented_characters':len(segmented),
                        'edit_distance_from_full_input_asr':distance(direct,segmented),
                        'same_first_four_characters':bool(direct and segmented[:4]==direct[:4]),
                        'asr_text':segmented}
    row={'name':case['name'],'full_input_asr':direct,'variants':variants}
    if any(case['name'].startswith(f'public_{n}_') for n in (4,5,6)):
        enhanced=EXTERNAL/'derived'/('gtcrn_'+case['name']+'.wav')
        enhanced_samples=load(enhanced)
        text=normalized(engine.transcribe(enhanced_samples))
        row['gtcrn_full_input_asr']=text
        row['gtcrn_edit_distance_from_unenhanced_asr']=distance(direct,text)
        info=evaluate(enhanced_samples,SileroFrameGate(EXTERNAL/'silero_vad_v5.onnx'))
        pieces=[enhanced_samples[round(a*16000):round(b*16000)] for a,b in info['segments']]
        segmented=''.join(normalized(engine.transcribe(x)) for x in pieces)
        row['gtcrn_v5']={'segments':len(pieces),'still_active_at_end':info['still_active_at_end'],
                         'asr_text':segmented,'edit_distance_from_full_input_asr':distance(direct,segmented),
                         'same_first_four_characters':bool(direct and segmented[:4]==direct[:4])}
        # Test an analysis-only enhancement branch: classifier sees denoised
        # audio, while ASR receives the original PCM at the same sample indices.
        raw_pieces=[samples[round(a*16000):round(b*16000)] for a,b in info['segments']]
        raw_text=''.join(normalized(engine.transcribe(x)) for x in raw_pieces)
        row['gtcrn_v5_original_pcm']={'segments':len(raw_pieces),'asr_text':raw_text,
            'edit_distance_from_full_input_asr':distance(direct,raw_text),
            'same_first_four_characters':bool(direct and raw_text[:4]==direct[:4]),
            'scope':'Offline aligned sample indices only; live delay alignment is not yet validated.'}
    rows.append(row)
    print(json.dumps({'case':case['name'],'edit_vs_full':{k:v['edit_distance_from_full_input_asr'] for k,v in variants.items()}},ensure_ascii=False),flush=True)
r={'rows':rows,'network_blocked':True,'production_changed':False,'public_samples_only':True,
   'limitation':'ASR-to-ASR comparison is a regression proxy, not independently annotated word accuracy or human acceptance.'}
if not (HERE/'asr_public_comparison_v4.json').exists():
    (HERE/'asr_public_comparison_v4.json').write_bytes((HERE/'asr_public_comparison.json').read_bytes())
(HERE/'asr_public_comparison.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
