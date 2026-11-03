"""Bounded, audio-device-free evaluation using the board's existing CPU runtime."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
EXTERNAL=Path('D:/AIModels/audio-frontend-eval-20261021')
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
sys.path.insert(0,str(HERE))
from board_ssh import ssh
from benchmark import make_cases,pcm

cases,_=make_cases()
selected=[c for c in cases if c['name'] in ('generated_harmonic_fan_like','public_4_clean','public_4_quiet','public_5_fan_like_snr0')]
payload={'modules':{},'models':{},'cases':[]}
wheel=json.loads((HERE/'board_runtime_wheel.json').read_text(encoding='utf-8'))
wheel_data=Path(wheel['path']).read_bytes()
assert hashlib.sha256(wheel_data).hexdigest()==wheel['official_sha256']
payload['wheel']={'name':wheel['filename'],'data':base64.b64encode(wheel_data).decode(),'sha256':wheel['official_sha256']}
for name,source in [('silero_gate.py',PROJECT/'aura/board/runtime/audio/silero_gate.py'),
                    ('vad.py',PROJECT/'aura/board/runtime/audio/vad.py'),
                    ('automatic_capture.py',PROJECT/'aura/board/runtime/audio/automatic_capture.py')]:
    data=source.read_bytes()
    payload['modules'][name]={'data':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
for name in ('silero_vad_v5.onnx',):
    data=(EXTERNAL/name).read_bytes()
    payload['models'][name]={'data':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
for case in selected:
    data=pcm(case['samples'][:8*16000])
    payload['cases'].append({'name':case['name'],'data':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()})
remote=r'''
import base64,hashlib,importlib.util,io,json,re,socket,statistics,subprocess,sys,time,zipfile
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
config=Path(re.findall(r'--config (\S+)',unit)[-1])
root=Path(json.loads(config.read_text())['runtime'])
assert str(config) in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
stage=Path('/home/root/aura-environment-eval-20261021')
stage.mkdir(exist_ok=True)
wheel=base64.b64decode(payload['wheel']['data']);assert hashlib.sha256(wheel).hexdigest()==payload['wheel']['sha256']
deps=stage/'official-ort-1.17.3';deps.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
 assert sum(i.file_size for i in archive.infolist())<60*1024*1024
 for item in archive.infolist():
  path=deps/item.filename
  assert deps.resolve() in path.resolve().parents
  if not item.is_dir():
   path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(item))
sys.path.insert(0,str(deps))
for kind in ('modules','models'):
 for name,entry in payload[kind].items():
  data=base64.b64decode(entry['data']);assert hashlib.sha256(data).hexdigest()==entry['sha256']
  (stage/name).write_bytes(data)
sys.path.insert(0,str(root/'aura'))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
 sys.modules[name]=module;spec.loader.exec_module(module);return module
# These replacements affect only this disposable process, never the UI process.
load('board.runtime.audio.vad',stage/'vad.py')
cap=load('eval_capture',stage/'automatic_capture.py')
model=load('eval_silero',stage/'silero_gate.py')
def blocked(*a,**kw):raise RuntimeError('Network forbidden during model evaluation')
socket.socket.connect=blocked
import onnxruntime as ort
started=time.monotonic();rows=[]
for model_name in ('silero_vad_v5.onnx',):
 for case in payload['cases']:
  data=base64.b64decode(case['data']);assert hashlib.sha256(data).hexdigest()==case['sha256']
  began=time.perf_counter();gate=model.SileroFrameGate(stage/model_name);load_ms=(time.perf_counter()-began)*1000
  endpoint=cap.SpeechEndpoint(frame_classifier=gate);times=[];starts=0;segments=[]
  cpu_started=time.process_time();wall_started=time.monotonic()
  for offset in range(0,len(data)-639,640):
   before=endpoint.active;t=time.perf_counter();result=endpoint.feed(data[offset:offset+640]);times.append((time.perf_counter()-t)*1000)
   if endpoint.active and not before:starts+=1
   if result is not None:
    end=offset+640;begin=end-len(result);assert data[begin:end]==result
    segments.append([begin/32000,end/32000]);endpoint=cap.SpeechEndpoint(frame_classifier=gate)
   if time.monotonic()-started>45:raise RuntimeError('Disposable evaluation exceeded 45 seconds')
  elapsed=time.monotonic()-wall_started;cpu=time.process_time()-cpu_started;duration=len(data)/32000
  times.sort();rows.append({'model':model_name,'case':case['name'],'seconds':duration,'load_ms':load_ms,
    'feed_p95_ms':times[int((len(times)-1)*.95)],'feed_max_ms':max(times),'wall_rtf':elapsed/duration,
    'cpu_rtf':cpu/duration,'starts':starts,'segments':segments,'still_active_at_end':endpoint.active,
    'gate':gate.public(),'pcm_exact':True})
print(json.dumps({'runtime_untouched':str(root),'onnxruntime':ort.__version__,'rows':rows,
 'runtime_isolation':str(deps),'runtime_official_wheel_sha256':payload['wheel']['sha256'],
 'microphone_opened':False,'playback_started':False,'network_blocked':True,
 'production_changed':False,'total_wall_seconds':time.monotonic()-started}))
'''
result=json.loads(ssh('python3 -B -','payload='+repr(payload)+'\n'+remote,timeout=65))
if not (HERE/'board_benchmark_v4.json').exists():
    (HERE/'board_benchmark_v4.json').write_bytes((HERE/'board_benchmark.json').read_bytes())
(HERE/'board_benchmark_v5.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
