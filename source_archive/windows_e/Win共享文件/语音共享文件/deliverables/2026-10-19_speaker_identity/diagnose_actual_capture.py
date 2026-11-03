"""Read-only diagnostics for the explicit four-clip speaker experiment."""
import json
from pathlib import Path
import sqlite3
import struct
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from common.speaker_identity import EcapaEncoder,read_pcm,voiced_pcm
import torch
torch.set_num_threads(2)
config=json.loads((HERE/'actual_experiment.json').read_text(encoding='utf-8'))
sid=config['session_id']; directory=ROOT/'声纹测试录音'/sid
encoder=EcapaEncoder('D:/AIModels/speaker-identity/ecapa')
vectors={};result={'scope':'READ_ONLY_ACTUAL_CAPTURE_DIAGNOSTIC','clips':{},'pairs':[]}
for index in (1,2,3,4):
    raw=read_pcm(directory/('clip-%02d.wav'%index))
    pcm,quality=voiced_pcm(raw)
    started=time.perf_counter();vector=encoder.encode(pcm)
    vectors[index]=vector
    samples=struct.unpack('<%dh'%(len(raw)//2),raw)
    quality['inference_ms']=round((time.perf_counter()-started)*1000,2)
    quality['rms_by_second']=[round((sum(v*v for v in samples[i:i+16000])/16000)**.5,1)
                               for i in range(0,len(samples),16000)]
    result['clips'][str(index)]=quality
for index in vectors:
    for other in vectors:
        if other>index:
            result['pairs'].append({'first':index,'second':other,
                                    'cosine':sum(a*b for a,b in zip(vectors[index],vectors[other]))})
db=Path('D:/AIModels/speaker-identity/runtime')/('speaker-test-'+sid+'.sqlite3')
connection=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
try:
    result['database']={'identities':connection.execute('SELECT COUNT(*) FROM identities').fetchone()[0],
                       'templates':connection.execute('SELECT COUNT(*) FROM templates').fetchone()[0]}
finally:connection.close()
(HERE/'actual_capture_diagnosis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
