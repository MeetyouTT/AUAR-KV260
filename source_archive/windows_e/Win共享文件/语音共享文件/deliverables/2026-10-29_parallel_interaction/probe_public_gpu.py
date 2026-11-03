"""Actual public ASR/LLM/TTS, RAM output only, no durable CID or playback ACK."""
import argparse,datetime,hashlib,json,sys,threading,time,urllib.request,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from board.runtime.audio.voice_channel import VoiceChannel
from common.gpu_coordination import NvidiaMemoryProbe
sys.path.insert(0,str(H.parent/'2026-10-29_audio_animation_polish'));from board_guard import capture
p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--labels',default='short,medium,long')
p.add_argument('--inputs',default='public_inputs.json');p.add_argument('--require-uncached',action='store_true');args=p.parse_args()
assert '/' not in args.inputs and '\\' not in args.inputs
assert args.phase.replace('_','').isalnum();output=H/('public_gpu_'+args.phase+'.json');assert not output.exists()
safe=capture();assert safe['safe'] and not safe['mismatches']
def health():
    with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as r:return json.load(r)
initial=health();assert initial['ready'] and not initial['busy']
inputs=json.loads((H/args.inputs).read_text(encoding='utf-8'))['inputs'];labels=args.labels.split(',')
report=dict(status='RUNNING',phase=args.phase,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 revision=initial['service_revision'],fingerprint=initial['source_fingerprint'],checks=[],
 microphone_opened=False,physical_playback=False,playback_ack_sent=False,durable_conversation_used=False,
 note='Observed device samples are not a guaranteed device peak; worker allocator peaks are per inference')
probe=NvidiaMemoryProbe(ttl=.1);samples=[];stop=threading.Event();began=time.monotonic()
def sample():
    while not stop.is_set():
        try:samples.append(dict(at=time.monotonic()-began,**probe.read().public(time.monotonic())))
        except Exception:pass
        stop.wait(.15)
worker=threading.Thread(target=sample,daemon=True);worker.start()
try:
    for entry in inputs:
        if entry['label'] not in labels:continue
        current=health();assert current['ready'] and not current['busy'] and current['source_fingerprint']==initial['source_fingerprint']
        with wave.open(str(H/entry['file']),'rb') as f:pcm=f.readframes(f.getnframes())
        meta=dict(protocol='aura-asr-1',board_boot_id='public-gpu-calibration',session_id=uuid.uuid4().hex,request_id=uuid.uuid4().hex,
          generation=1,capture_id='public-gpu-'+entry['label'],sample_count=len(pcm)//2,pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=120000)
        started=time.monotonic();events={};digest=hashlib.sha256();end={};segments={};play_end=None;gap=0
        def receive(header,payload):
            nonlocal_placeholder=None
            elapsed=(time.monotonic()-started)*1000;kind=header['kind'];events.setdefault(kind,elapsed)
            if kind=='audio':
                digest.update(payload);segment=segments.setdefault(str(header['segment_id']),dict(first_ms=elapsed,samples=0));segment['samples']+=len(payload)//2
            if kind=='end':end.update(header)
        channel=VoiceChannel('192.168.50.1')
        try:result=channel.exchange(meta,pcm,receive)
        finally:channel.close()
        assert result['network_complete'] and not result['playback_verified'] and result['sample_count']>0
        assert result['pcm_sha256']==digest.hexdigest()
        if args.require_uncached:assert end['tts_cache_hits']==0,'This acceptance requires actual uncached synthesis'
        state=health();stats=state.get('gpu_coordination',{})
        report['checks'].append(dict(label=entry['label'],status='PASS',first_pcm_ms=round(events['audio'],2),
          total_ms=round((time.monotonic()-started)*1000,2),output_samples=result['sample_count'],output_sha256=result['pcm_sha256'],
          reply_characters=len(result['reply_text']),tts_cache_hits=end['tts_cache_hits'],clauses=end['clauses'],segments=segments,
          timing={k:v for k,v in end.get('timing',{}).items() if k not in ('first_clause_text','conversation_context')},
          gpu=stats))
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({key:report['checks'][-1][key] for key in ('label','status','first_pcm_ms','total_ms','tts_cache_hits','clauses')}),flush=True)
    report['status']='PASS'
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
finally:
    stop.set();worker.join(timeout=1)
    report['device_samples']=samples
    report['observed_min_free_mib']=min((s['free_mib'] for s in samples),default=None)
    report['observed_max_used_mib']=max((s['used_mib'] for s in samples),default=None)
    report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report.get(k) for k in ('status','phase','observed_min_free_mib','observed_max_used_mib','error')}),flush=True)
raise SystemExit(0 if report['status']=='PASS' else 1)
