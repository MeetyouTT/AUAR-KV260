"""Real existing ECAPA/public recordings; no private gallery or new audio."""
import json,socket,sys,time,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'aura'))
from common.speaker_identity import EcapaEncoder
from common.speaker_attribution import SpeakerContext,evaluate
def blocked(*a,**kw):raise RuntimeError('Network disabled for public validation')
socket.socket.connect=blocked
import torch
torch.set_num_threads(2)
encoder=EcapaEncoder('D:/AIModels/speaker-identity/ecapa')
vectors={};timings=[]
for person in (1,2):
    for sentence in (1,2):
        name=f'spk{person}_snt{sentence}'
        with wave.open(str(Path('D:/AIModels/speaker-identity/public-samples')/(name+'.wav'))) as w:
            assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(16000,1,2)
            raw=w.readframes(w.getnframes())
        start=time.perf_counter();vectors[name]=encoder.encode(raw);timings.append((time.perf_counter()-start)*1000)
context=SpeakerContext('public-validation',1,encoder.model_id,0)
trials=[]
for person in (1,2):
    score=sum(a*b for a,b in zip(vectors['spk1_snt1'],vectors[f'spk{person}_snt2']))
    result=dict(capture_id=context.capture_id,turn_generation=1,model_id=encoder.model_id,gallery_revision=0,
                started_ms=0,ended_ms=3500,deadline_ms=5000,voiced_ms=3000,
                single_speaker_verified=True,face_identity_conflict=False,scores={'public-speaker-1':score})
    # Synthetic window/verification flags exercise protocol only, not actual ASD/VAD.
    decision=evaluate(result,context,4000,threshold=.8,margin=.1,minimum_voiced_ms=3000,field_calibrated=True)
    default=evaluate(result,context,4000,threshold=.8,margin=.1,minimum_voiced_ms=3000)
    trials.append(dict(same_speaker=person==1,cosine=score,protocol_fixture_decision=decision,
                       production_default=default))
assert all(r['protocol_fixture_decision']['accepted']==(r['cosine']>=.8) for r in trials)
assert all(not r['production_default']['accepted'] for r in trials)
value=dict(status='PUBLIC_MODEL_PROTOCOL_SMOKE_ONLY',model_id=encoder.model_id,trials=trials,
           inference_ms=timings,field_calibrated=False,personal_database_accessed=False,
           production_integrated=False,network_blocked=True,
           limitation='0.8 is an uncalibrated fixture, not a selected speaker threshold. Public two-speaker scores with synthetic window/single-speaker flags; not field accuracy or ASD validation.')
(HERE/'public_speaker_validation.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
