"""Public-data calibration for this host; no device, business DB or playback."""
import argparse, csv, datetime, hashlib, http.client, json, math, os, subprocess, sys, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
AURA=ROOT/'aura'
sys.path[:0]=[str(AURA),str(ROOT/'deliverables/2026-10-18_board_dialogue')]
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'
MIB=1024*1024

def gpu():
    r=subprocess.run(['nvidia-smi','--query-gpu=uuid,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode:raise RuntimeError('GPU read failed')
    rows=list(csv.reader(r.stdout.strip().splitlines()))
    if len(rows)!=1 or len(rows[0])!=4:raise RuntimeError('Exactly one measured GPU required')
    u,total,used,free=[x.strip() for x in rows[0]]
    return dict(uuid=u,total_mib=int(total),used_mib=int(used),free_mib=int(free),monotonic=time.monotonic())

def rounded(n):return int(math.ceil(n/256)*256)

def save(name,value):
    p=OUT/name;temporary=p.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temporary,p)

class Sampler:
    def __init__(self):self.values=[];self.stop=threading.Event();self.thread=threading.Thread(target=self.work,daemon=True)
    def work(self):
        while not self.stop.is_set():
            try:self.values.append(gpu())
            except (OSError,RuntimeError,ValueError,subprocess.TimeoutExpired):pass
            self.stop.wait(.2)
    def __enter__(self):self.values.append(gpu());self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join(6)
    def peak(self,after=0):
        return max([x['used_mib'] for x in self.values if x['monotonic']>=after]+[gpu()['used_mib']])

def tts():
    before=gpu()
    if before['free_mib']<8192:raise RuntimeError('Insufficient fresh free GPU memory for isolated TTS calibration')
    import torch
    from board.runtime.audio.omnivoice_voice import OmniVoiceSynthesizer,PARAMETERS,REVISION
    from common.model_inference_wire import decode_audio
    from tools.cuda_memory_stats import begin,finish
    synth=OmniVoiceSynthesizer(None,AURA/'models/tts/OmniVoice',memory_only=True)
    measurements=[]
    with Sampler() as samples:
        initial=begin(torch);began=time.monotonic()
        synth.load();torch.manual_seed(8701)
        with torch.inference_mode():synth.generate_waves('嗯，我在呢。')
        torch.cuda.synchronize()
        cold=finish(torch,initial,warmup=True)
        measurements.append(dict(kind='warmup',seconds=round(time.monotonic()-began,3),cuda=cold))
        for text in ('你好，我已经准备好了。','这是本机部署的公开语音验证。'):
            initial=begin(torch);began=time.monotonic();result=synth.synthesize_pcm(text);torch.cuda.synchronize()
            pcm,rate=decode_audio(result['audio'])
            if rate!=24000 or not pcm or not any(pcm):raise RuntimeError('Fresh PCM validation failed')
            measurements.append(dict(kind='uncached_public_tts',seconds=round(time.monotonic()-began,3),
                samples=len(pcm)//2,rate=rate,sha256=hashlib.sha256(pcm).hexdigest(),cache_hit=result['cache_hit'],
                cuda=finish(torch,initial)))
            pcm=result=None
    peak=max(samples.peak()-before['used_mib'],max(x['cuda'].get('peak_reserved_bytes',0)/MIB for x in measurements))
    steady=max(x['cuda'].get('reserved_extra_peak_bytes',0)/MIB for x in measurements[1:])
    report=dict(passed=True,scope='individual_original_omnivoice16_public_pcm_no_playback',gpu_before=before,
        torch=torch.__version__,cuda_build=torch.version.cuda,compute_capability=list(torch.cuda.get_device_capability(0)),
        model_revision=REVISION,parameters=PARAMETERS,reference_sha256=synth.selection['reference_sha256'],measurements=measurements,
        candidate_cold_extra_mib=rounded(peak+768),candidate_steady_extra_mib=rounded(steady+512),
        physical_peak_used_mib=samples.peak(),sampler_count=len(samples.values),audio_archived=False)
    save('tts_calibration.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='measurements'}),flush=True)

def api(method,path,body=None,timeout=300):
    c=http.client.HTTPConnection('127.0.0.1',11435,timeout=timeout)
    try:
        c.request(method,path,json.dumps(body).encode() if body is not None else None,{'Content-Type':'application/json'})
        r=c.getresponse();raw=r.read(2*1024*1024+1)
        if r.status!=200 or len(raw)>2*1024*1024:raise RuntimeError('Project Ollama calibration HTTP failure')
        return json.loads(raw)
    finally:c.close()

def llm():
    from project_ollama import inspect_ownership
    expected=inspect_ownership()
    if api('GET','/api/ps').get('models')!=[]:raise RuntimeError('Project model was already resident; refusing to adopt or unload it')
    before=gpu()
    if before['free_mib']<17000:raise RuntimeError('Insufficient fresh free GPU memory for isolated 27B calibration')
    loaded=False
    try:
        with Sampler() as samples:
            began=time.monotonic()
            response=api('POST','/api/generate',dict(model=MODEL,prompt='',stream=False,keep_alive=-1,think=False,options={'num_ctx':2048}))
            loaded=True
            if response.get('done') is not True or response.get('response')!='':raise RuntimeError('No-prompt preload did not complete')
            load_seconds=time.monotonic()-began
            residency=api('GET','/api/ps')['models']
            if len(residency)!=1 or residency[0].get('name')!=MODEL:raise RuntimeError('Unexpected project model residency')
            if 'context_length' in residency[0] and residency[0]['context_length']!=2048:raise RuntimeError('Loaded context changed')
            resident=gpu();probe_started=time.monotonic()
            response=api('POST','/api/chat',dict(model=MODEL,stream=False,keep_alive=-1,think=False,
                messages=[{'role':'system','content':'这是公开的部署验证，请简短作答。'},{'role':'user','content':'请回复你已经准备好了。'}],
                options={'num_ctx':2048,'num_predict':32,'temperature':.6}),timeout=120)
            text=response.get('message',{}).get('content','')
            if response.get('done') is not True or not text or response.get('eval_count',0)<=0:raise RuntimeError('Fresh public 27B generation failed')
            chat_metrics={k:response[k] for k in ('eval_count','prompt_eval_count','load_duration','eval_duration','total_duration') if k in response}
            peak=samples.peak();steady=max(0,samples.peak(probe_started)-resident['used_mib'])
            report=dict(passed=True,scope='individual_fixed_27b_public_generation',gpu_before=before,
                model=MODEL,context_length=2048,load_seconds=round(load_seconds,3),residency=residency,
                response_characters=len(text),metrics=chat_metrics,physical_peak_used_mib=peak,sampler_count=len(samples.values),
                candidate_cold_extra_mib=rounded(max(peak-before['used_mib'],residency[0].get('size_vram',0)/MIB)+1024),
                candidate_steady_extra_mib=rounded(steady+512),request_or_response_text_archived=False)
    finally:
        if loaded:
            current=inspect_ownership()
            keys=('pid','creation_utc','executable','command_line','listeners')
            if any(current[k]!=expected[k] for k in keys):raise RuntimeError('Project daemon owner changed; no unload sent')
            rows=api('GET','/api/ps').get('models')
            if any(row.get('name')!=MODEL for row in rows):raise RuntimeError('Foreign model appeared; no unload sent')
            api('POST','/api/generate',dict(model=MODEL,prompt='',stream=False,keep_alive=0),timeout=30)
            until=time.monotonic()+20
            while api('GET','/api/ps').get('models') and time.monotonic()<until:time.sleep(.5)
            if api('GET','/api/ps').get('models'):raise RuntimeError('Owned model release was not confirmed')
    report['owned_model_released_after_calibration']=True
    save('llm_calibration.json',report);print(json.dumps(report),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('tts','llm'));args=parser.parse_args()
    try:tts() if args.stage=='tts' else llm()
    except Exception as error:
        save(args.stage+'_calibration_failure.json',dict(error_type=type(error).__name__,message=str(error)))
        raise
