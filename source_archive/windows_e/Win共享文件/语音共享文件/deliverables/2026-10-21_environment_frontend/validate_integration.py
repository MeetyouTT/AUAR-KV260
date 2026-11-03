"""Exercise the actual bounded TCP service and capture endpoint with public PCM."""
import json,socket,sys,threading,time
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1]
sys.path.insert(0,str(PROJECT/'aura'));sys.path.insert(0,str(HERE))
from benchmark import make_cases,pcm
from board.runtime.audio.automatic_capture import SpeechEndpoint
from board.runtime.audio.remote_frontend import RemoteSpeechGate,health
from tools.audio_frontend_host import Pipeline,FrontendServer
from board.runtime.audio.asr import AsrConfig,SherpaOfflineRecognizer

def blocked(*a,**kw):raise RuntimeError('External network forbidden')
# The only permitted connections are this process's temporary loopback server.
original_connect=socket.socket.connect
def local_only(self,address):
    if address[0]!='127.0.0.1':raise RuntimeError('Non-loopback connection forbidden')
    return original_connect(self,address)
socket.socket.connect=local_only
models=Path('D:/AIModels/audio-frontend-eval-20261021')
server=FrontendServer(('127.0.0.1',0),[Pipeline(models),Pipeline(models)])
thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
config={'enabled':True,'host':'127.0.0.1','port':server.server_address[1],'timeout_ms':180}
cases,_=make_cases();rows=[]
asr=SherpaOfflineRecognizer(AsrConfig(model_dir=str(PROJECT/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14'),num_threads=1))
try:
    assert health(config)['ready']
    for case in cases:
        gate=RemoteSpeechGate(config);endpoint=SpeechEndpoint(frame_classifier=gate,pre_roll_ms=500)
        raw=pcm(case['samples']);starts=[];segments=[];result=None;timings=[]
        try:
            for offset in range(0,len(raw)-639,640):
                active=endpoint.active;began=time.monotonic()
                result=endpoint.feed(raw[offset:offset+640]);timings.append((time.monotonic()-began)*1000)
                if endpoint.active and not active:starts.append((offset+640)/32000)
                if result is not None:
                    end=offset+640;start=end-len(result);assert result==raw[start:end]
                    segments.append([start/32000,end/32000]);break
            row={'name':case['name'],'expected':case['expected'],'starts':starts,'segments':segments,
                 'still_active':endpoint.active,'roundtrip_p95_ms':float(np.percentile(timings,95)),
                 'roundtrip_max_ms':max(timings),'frontend':gate.public(),'pcm_original_slice_exact':True}
            if case['name'].startswith(('public_4_','public_5_','public_6_')):
                source=case['samples'];text=asr.transcribe(source)
                captured=asr.transcribe(np.frombuffer(result,dtype='<i2').astype(np.float32)/32768) if result else ''
                row.update(full_public_asr=text,captured_public_asr=captured)
            rows.append(row)
            print(json.dumps({'case':case['name'],'segments':segments,'starts':len(starts),'active':endpoint.active}),flush=True)
        finally:gate.close()
finally:
    server.shutdown();server.server_close();thread.join(2)
report={'cases':rows,'production_changed':False,'microphone_opened':False,'temporary_server_closed':True,
        'pipeline':'Stock GTCRN+Silero native SDK, duration and 500ms preroll on existing board endpoint, original PCM ASR.',
        'noise_starts':sum(len(r['starts']) for r in rows if r['expected']=='non_speech'),
        'speech_cases_without_result':[r['name'] for r in rows if r['expected']=='speech' and not r['segments']]}
(HERE/'integration_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'noise_starts':report['noise_starts'],'speech_cases_without_result':report['speech_cases_without_result']}))
