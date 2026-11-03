"""Isolated streaming KWS characterization, no production enablement."""
import hashlib,json,time,wave
from pathlib import Path
import numpy as np
import sherpa_onnx
H=Path(__file__).resolve().parent;D=Path(r'D:\AIModels\wake-keyword')
manifest=json.loads((H/'kws_model_manifest.json').read_text())
for row in manifest['files'].values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
tokens={line.split()[0] for line in (D/'tokens.txt').read_text(encoding='utf-8').splitlines()}
for line in (H/'kws_keywords.txt').read_text(encoding='utf-8').splitlines():assert all(t in tokens for t in line.split() if not t.startswith('@'))
spot=sherpa_onnx.KeywordSpotter(tokens=str(D/'tokens.txt'),
 encoder=str(D/'encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx'),decoder=str(D/'decoder-epoch-13-avg-2-chunk-8-left-64.onnx'),
 joiner=str(D/'joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx'),keywords_file=str(H/'kws_keywords.txt'),
 num_threads=1,keywords_score=1,keywords_threshold=.25,num_trailing_blanks=1,provider='cpu')
rows=json.loads((H/'wake_phrases.json').read_text(encoding='utf-8'))
for row in rows:row['path']=H/'synthetic_wake_fixtures'/(row['id']+'.wav')
rows.append({'id':'public_ordinary_chinese','path':H.parents[1]/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav','expected':'reject'})
results=[]
for row in rows:
 with wave.open(str(row['path'])) as f:
  assert (f.getnchannels(),f.getframerate(),f.getsampwidth())==(1,16000,2)
  raw=f.readframes(f.getnframes())
 samples=np.concatenate([np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768,np.zeros(12800,dtype=np.float32)])
 stream=spot.create_stream();hits=[];costs=[]
 for off in range(0,len(samples),320):
  started=time.perf_counter();stream.accept_waveform(16000,samples[off:off+320])
  while spot.is_ready(stream):
   spot.decode_stream(stream);keyword=spot.get_result(stream)
   if keyword:
    hits.append({'keyword':keyword,'input_time_seconds':round(min(off+320,len(samples))/16000,3)})
    spot.reset_stream(stream)
  costs.append((time.perf_counter()-started)*1000)
 results.append({'id':row['id'],'expected':row['expected'],'input_seconds':len(raw)/32000,'detections':hits,
                 'compute_ms':round(sum(costs),3),'chunk_max_ms':round(max(costs),3),'chunk_p95_ms':round(float(np.percentile(costs,95)),3)})
report={'status':'EVALUATION_ONLY','model_files_verified':True,'sherpa_version':sherpa_onnx.__version__,
        'production_changed':False,'threshold':.25,'results':results}
(H/'kws_evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
