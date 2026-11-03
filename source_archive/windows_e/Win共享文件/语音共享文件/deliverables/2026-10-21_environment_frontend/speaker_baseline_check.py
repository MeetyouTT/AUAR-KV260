"""Reuse existing ECAPA on public speakers; no private recordings or enrollment."""
import json,socket,sys,time,wave
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
sys.path.insert(0,str(PROJECT/'aura'))
from common.speaker_identity import EcapaEncoder


def blocked(*a,**kw):raise RuntimeError('Network forbidden during speaker inference')
socket.socket.connect=blocked
import torch
torch.set_num_threads(2)
encoder=EcapaEncoder('D:/AIModels/speaker-identity/ecapa')
manifest=json.loads((HERE/'asset_manifest.json').read_text(encoding='utf-8'))
root=Path(manifest['external_root'])
samples=Path('D:/AIModels/speaker-identity/public-samples')
vectors={};times=[]
for person in (1,2):
    for sentence in (1,2):
        name=f'spk{person}_snt{sentence}'
        with wave.open(str(samples/(name+'.wav'))) as a:
            assert (a.getframerate(),a.getnchannels(),a.getsampwidth())==(16000,1,2)
            raw=a.readframes(a.getnframes())
        began=time.perf_counter();vectors[name]=encoder.encode(raw);times.append((time.perf_counter()-began)*1000)
rows=[]
for ref in ('spk1_snt1','spk2_snt1'):
    for query in ('spk1_snt2','spk2_snt2'):
        rows.append({'reference':ref,'query':query,'same_speaker':ref[:4]==query[:4],
                     'cosine':sum(a*b for a,b in zip(vectors[ref],vectors[query]))})
result={'status':'EXISTING_ECAPA_PUBLIC_BASELINE_REUSED','model_id':encoder.model_id,
        'network_blocked':True,'cpu_threads':2,'inference_ms':times,'scores':rows,
        'personal_database_read_or_written':False,'enrollment_performed':False,
        'field_calibrated':False,'production_changed':False,
        'scope':'Two public speakers with separate reference/query clips; no field threshold or noise robustness claim.'}
(HERE/'speaker_public_baseline.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
