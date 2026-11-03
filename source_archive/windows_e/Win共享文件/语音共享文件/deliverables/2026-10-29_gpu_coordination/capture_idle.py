"""Read-only GPU/endpoint audit. Does not call generation or model loading APIs."""
import concurrent.futures,datetime,json,subprocess,sys,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
def http(host,port,path='/health'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4) as r:return json.load(r)
jobs={'voice':lambda:http('192.168.50.1',8792),'asr':lambda:http('192.168.50.1',8791),
 'visual':lambda:http('127.0.0.1',8810),'memory':lambda:http('127.0.0.1',8812),
 'project_ollama_ps':lambda:http('127.0.0.1',11435,'/api/ps'),
 'other_ollama_ps':lambda:http('127.0.0.1',11434,'/api/ps')}
endpoints={}
with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
    futures={name:pool.submit(job) for name,job in jobs.items()}
    for name,future in futures.items():
        try:endpoints[name]={'reachable':True,'data':future.result()}
        except Exception as exc:endpoints[name]={'reachable':False,'error':type(exc).__name__+': '+str(exc)}
samples=[]
for _ in range(12):
    r=subprocess.run(['nvidia-smi','--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,utilization.gpu',
      '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3)
    samples.append({'at':time.monotonic(),'returncode':r.returncode,'csv':r.stdout.strip(),'stderr':r.stderr.strip()[:200]})
    time.sleep(.5)
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'idle/read-only; no generation, loading, microphone, sound or board actions',
 'endpoints':endpoints,'samples':samples,'can_measure_inference_peak':False}
(H/'idle_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
voice=endpoints['voice'].get('data',{})
print(json.dumps({'status':'CAPTURED','services':{name:row['reachable'] for name,row in endpoints.items()},
 'voice_revision':voice.get('service_revision'),'voice_keys':list(voice),'gpu_samples':len(samples),
 'project_ollama':endpoints['project_ollama_ps'].get('data',{}),'other_ollama':endpoints['other_ollama_ps'].get('data',{})}))
