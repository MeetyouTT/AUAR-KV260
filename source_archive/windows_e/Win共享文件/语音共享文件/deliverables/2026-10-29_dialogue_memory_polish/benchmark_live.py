"""Same WAV and same persistent explicit fact, before/after; no playback or ACK."""
import argparse,ast,hashlib,json,statistics,subprocess,sys,time,urllib.request,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board.runtime.audio.voice_channel import VoiceChannel
from common.memory_controls import MemoryControlsMixin
from board_ssh import ssh
p=argparse.ArgumentParser();p.add_argument('phase',choices=['before','after']);args=p.parse_args()
output=H/('benchmark_'+args.phase+'.json');assert not output.exists(),'Preserve existing measurement'
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
def ps(parameters,timeout=30):
    r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',*parameters],capture_output=True,timeout=timeout)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace')[-500:])
def health():
    with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4) as r:return json.load(r)
def job(action):
    token=uuid.uuid4().hex;python=r'C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    command='"'+python+'" -B "'+str(H/'benchmark_cleanup.py')+'" --job '+token+' --action '+action
    launch="$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"+"$p=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='"+command+"';ProcessStartupInformation=$s};if($p.ReturnValue -ne 0){throw 'Benchmark cleanup failed'}"
    ps(['-Command',launch]);path=H/('cleanup_'+token+'.json');until=time.monotonic()+20
    while not path.exists() and time.monotonic()<until:time.sleep(.1)
    result=json.loads(path.read_text(encoding='utf-8'));assert result['status']=='PASS',result
    return result
def save_exp():(H/'experiment.json').write_text(json.dumps(exp,ensure_ascii=False,indent=2),encoding='utf-8')
voice=health();assert voice['ready'] and not voice['busy'] and voice['latency_options']['compact_grammar'] is False
assert voice['source_fingerprint']==plan['production_fingerprint' if args.phase=='before' else 'candidate_fingerprint']
if args.phase=='before':
    tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
    script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
    board=json.loads(ssh('python3 -B -',script,timeout=20));assert board['preflight_ready']
    (H/'board_baseline.json').write_text(json.dumps(board,ensure_ascii=False,indent=2),encoding='utf-8')
    token=uuid.uuid4().hex;ps(['-File',str(H/'start_checkpoint.ps1'),'-Job',token,'-Phase','before'])
    path=H/('db_checkpoint_'+token+'.json');until=time.monotonic()+20
    while not path.exists() and time.monotonic()<until:time.sleep(.1)
    original=json.loads(path.read_text(encoding='utf-8'));assert original['status']=='PASS'
    (H/'original_database_checkpoint.json').write_text(json.dumps(original,indent=2),encoding='utf-8')
    assert not (H/'experiment.json').exists()
    exp={'cid':uuid.uuid4().hex,'session':uuid.uuid4().hex,'generation':0,'attempts':[],'public_fact':{'颜色偏好':'绿色'}}
else:
    assert json.loads((H/'deployment.json').read_text(encoding='utf-8'))['status']=='COMMITTED'
    exp=json.loads((H/'experiment.json').read_text(encoding='utf-8'))
report={'status':'RUNNING','phase':args.phase,'started_unix':time.time(),'health_before':voice,
        'context_contract':{'explicit_fact':{'颜色偏好':'绿色'},'prior_played_dialogue':[]},'trials':[],'controls':[]}
def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def synth(name,text):
    path=H/(name+'.wav')
    if not path.exists():ps(['-File',str(H/'synthesize_question.ps1'),'-Text',text,'-OutputPath',str(path)])
    return path
def exchange(audio,*,cid=None,base=False):
    with wave.open(str(audio),'rb') as source:
        assert (source.getframerate(),source.getnchannels(),source.getsampwidth())==(16000,1,2)
        pcm=source.readframes(source.getnframes())
    exp['generation']+=1
    meta={'protocol':'aura-asr-1','board_boot_id':'public-polish-comparison','session_id':exp['session'] if cid else uuid.uuid4().hex,
          'request_id':uuid.uuid4().hex,'generation':exp['generation'],'capture_id':'fixed-public-comparison',
          'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
    if cid:
        exp['attempts'].append({'context':meta})
        if base:exp['base_context']=meta;exp['delete_owner']=MemoryControlsMixin._delete_owner(meta,cid,None)
        save_exp()
    kinds={};end={};transcript='';digest=hashlib.sha256();started=time.monotonic()
    def receive(header,payload):
        nonlocal transcript
        kinds.setdefault(header['kind'],round((time.monotonic()-started)*1000,2))
        if header['kind']=='transcript':transcript=header['text']
        if header['kind']=='audio':digest.update(payload)
        if header['kind']=='end':end.update(header)
    channel=VoiceChannel('192.168.50.1')
    try:result=channel.exchange(meta,pcm,receive,conversation=cid)
    finally:channel.close()
    assert result['network_complete'] and result['pcm_sha256']==digest.hexdigest() and not result['playback_verified']
    return {'input_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'transcript':transcript,'reply':result['reply_text'],
            'first_text_ms':kinds.get('text'),'first_pcm_ms':kinds.get('audio'),'total_ms':round((time.monotonic()-started)*1000,2),
            'sample_count':result['sample_count'],'timing':end.get('timing',{}),'tts_cache_hits':end.get('tts_cache_hits'),'playback_ack_sent':False}
save()
try:
    question=synth('fixed_fact_question','我喜欢什么颜色')
    if args.phase=='before':
        report['setup']=exchange(synth('fixed_fact_setup','记住，颜色是绿色'),cid=exp['cid'],base=True)
        assert '记住' in report['setup']['reply'];save()
    for index in range(4):
        result=exchange(question,cid=exp['cid']);result['index']=index;result['temperature_phase']='initial' if index==0 else 'repeat'
        assert '绿色' in result['reply'],result['reply']
        report['trials'].append(result);save()
        job('trim')
        print(json.dumps({'phase':args.phase,'trial':index,'first_pcm_ms':result['first_pcm_ms'],'first_text_ms':result['first_text_ms'],
            'tts_cache_hits':result['tts_cache_hits'],'backend':result['timing'].get('llm',{}).get('backend')},ensure_ascii=True),flush=True)
    official=A/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'
    for index in range(2):
        result=exchange(official);report['controls'].append(result);save()
        print(json.dumps({'phase':args.phase,'control':index,'first_pcm_ms':result['first_pcm_ms']},ensure_ascii=True),flush=True)
    report.update(status='PASS',finished_unix=time.time(),warm_fact_median_first_pcm_ms=statistics.median(r['first_pcm_ms'] for r in report['trials'][1:]),
        warm_fact_median_first_text_ms=statistics.median(r['first_text_ms'] for r in report['trials'][1:]))
    if args.phase=='after':report['cleanup']=job('all')
except Exception as exc:
    report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
    try:report['cleanup']=job('all')
    except Exception as clean:report['cleanup_error']=str(clean)
finally:save()
print(json.dumps({'status':report['status'],'phase':args.phase,'median_first_pcm_ms':report.get('warm_fact_median_first_pcm_ms')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)

