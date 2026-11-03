"""Use the official packaged SDK for both denoising and VAD on public audio."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
EXTERNAL=Path('D:/AIModels/audio-frontend-eval-20261021')
sys.path.insert(0,str(HERE));from benchmark import make_cases,pcm
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'));from board_ssh import ssh
wheels=json.loads((HERE/'sherpa_runtime_wheels.json').read_text(encoding='utf-8'))['wheels']
payload={'files':{},'cases':[]}
for row in wheels:
    data=Path(row['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256']
    payload['files'][row['filename']]={'data':base64.b64encode(data).decode(),'sha256':row['sha256']}
for name in ('gtcrn_simple.onnx','silero_vad_v5.onnx'):
    data=(EXTERNAL/name).read_bytes()
    payload['files'][name]={'data':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
cases,_=make_cases()
for case in cases:
    if case['name'] in ('generated_harmonic_fan_like','public_5_fan_like_snr0','public_4_quiet'):
        data=pcm(case['samples'][:8*16000])
        payload['cases'].append({'name':case['name'],'data':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()})
remote=r'''
import base64,hashlib,io,json,socket,sys,time,zipfile
from pathlib import Path
stage=Path('/home/root/aura-environment-eval-20261021/official-sherpa-1.13.8');stage.mkdir(exist_ok=True)
for name,entry in payload['files'].items():
 data=base64.b64decode(entry['data']);assert hashlib.sha256(data).hexdigest()==entry['sha256']
 if name.endswith('.whl'):
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
   assert sum(i.file_size for i in archive.infolist())<100*1024*1024
   for item in archive.infolist():
    path=stage/item.filename;assert stage.resolve() in path.resolve().parents
    if not item.is_dir():
     path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(item))
 else:(stage/name).write_bytes(data)
sys.path.insert(0,str(stage))
def blocked(*a,**kw):raise RuntimeError('Network forbidden during SDK evaluation')
socket.socket.connect=blocked
try:
 import numpy as np
 import sherpa_onnx as s
 config=s.OnlineSpeechDenoiserConfig(model=s.OfflineSpeechDenoiserModelConfig(
  gtcrn=s.OfflineSpeechDenoiserGtcrnModelConfig(model=str(stage/'gtcrn_simple.onnx')),
  num_threads=1,provider='cpu'))
 assert config.validate()
 vc=s.VadModelConfig();vc.silero_vad.model=str(stage/'silero_vad_v5.onnx')
 vc.silero_vad.min_speech_duration=.18;vc.silero_vad.min_silence_duration=.7
 vc.silero_vad.threshold=.5;vc.sample_rate=16000;vc.num_threads=1
 rows=[];total_start=time.monotonic()
 for case in payload['cases']:
  data=base64.b64decode(case['data']);assert hashlib.sha256(data).hexdigest()==case['sha256']
  samples=np.frombuffer(data,dtype='<i2').astype(np.float32)/32768
  begin=time.monotonic();sd=s.OnlineSpeechDenoiser(config);vad=s.VoiceActivityDetector(vc,buffer_size_in_seconds=25)
  load_ms=(time.monotonic()-begin)*1000
  times=[];cpu=time.process_time();wall=time.monotonic();segments=[];output_count=0
  for offset in range(0,len(samples),320):
   begin=time.perf_counter();out=sd(samples[offset:offset+320],16000)
   values=np.asarray(out.samples,dtype=np.float32);output_count+=len(values)
   if len(values):vad.accept_waveform(values)
   while not vad.empty():
    seg=vad.front;segments.append([seg.start/16000,(seg.start+len(seg.samples))/16000]);vad.pop()
   times.append((time.perf_counter()-begin)*1000)
   if time.monotonic()-total_start>45:raise RuntimeError('Bounded SDK probe exceeded 45 seconds')
  cpu_seconds=time.process_time()-cpu;wall_seconds=time.monotonic()-wall
  unresolved=vad.is_speech_detected();times.sort();duration=len(samples)/16000
  rows.append({'case':case['name'],'seconds':duration,'load_ms':load_ms,
    'cpu_rtf':cpu_seconds/duration,'wall_rtf':wall_seconds/duration,
    'process_ms_p95':times[int((len(times)-1)*.95)],'process_ms_max':max(times),
    'segments':segments,'speech_active_at_input_end':unresolved,
    'output_samples_before_flush':output_count,'input_samples':len(samples)})
 result={'status':'OFFICIAL_SDK_ISOLATED_PROBE_COMPLETE','version':s.__version__,'rows':rows}
except Exception as exc:
 result={'status':'OFFICIAL_SDK_ISOLATED_PROBE_FAILED','error_type':type(exc).__name__,'error':str(exc)[:1400]}
result.update(production_changed=False,microphone_opened=False,playback_started=False,network_blocked=True)
print(json.dumps(result))
'''
try:result=json.loads(ssh('python3 -B -','payload='+repr(payload)+'\n'+remote,timeout=100))
except Exception as exc:result={'status':'TRANSPORT_OR_IMPORT_FAILURE','error':str(exc)[-1600:],'production_changed':False}
(HERE/'board_sdk_benchmark.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
