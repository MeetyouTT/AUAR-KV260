"""Exclusive same-text LLM/TTS scheduling benchmark; no actual board playback.

The original JSON schema is constrained to the same short reply only for this
experiment. It is NOT a free-generation or fixed-answer production change.
"""
import hashlib,json,sys,time,statistics,wave
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.selected_voice_service import VoiceWorker
from tools import dialogue_stream as module
TEXT='还好呀，就是有点想你。你那边怎么样？'
report={'actual_llm':True,'actual_tts':True,'actual_playback':False,'fixed_reply_for_experiment':TEXT,'production_prompt_changed':False,'cases':[]}
worker=VoiceWorker(HERE/'benchmark_voice',python=sys.executable,model_path=ROOT/'aura/models/tts/OmniVoice',engine='omnivoice')
original=module.stream_body
def controlled(*args,**kwargs):
    body=original(*args,**kwargs);body['options']['seed']=42
    body['format']['properties']['a']={'type':'string','const':TEXT}
    return body

def generate_uncached():
    key,_=worker.synth.identity(TEXT)
    for suffix in ('.wav','.json'):
        target=worker.cache/(key+suffix)
        assert target.resolve().parent==worker.cache.resolve()
        if target.exists():target.unlink()  # Only this new benchmark's own cache.
    start=time.perf_counter();result=worker.generate(TEXT)
    assert not result['cache_hit']
    return result,round((time.perf_counter()-start)*1000,2)

try:
    worker.warmup();assert worker.ready,worker.error
    for index,mode in enumerate(('overlap','serial','serial','overlap')):
        stream=module.OllamaReplyStream('http://127.0.0.1:11435','aura-qwen3.8-27b-abliterated:iq4_xs',[],'你好汐蓝今天过得怎么样',90,reply_first=True)
        row={'mode':mode};start=time.perf_counter();spoken=''
        with patch.object(module,'stream_body',controlled):
            for kind,value in stream:
                if kind=='text':spoken+=value
                if kind=='speech_ready':
                    row['speech_ready_ms']=round((time.perf_counter()-start)*1000,2)
                    assert spoken==TEXT
                    if mode=='overlap':
                        audio,tts_ms=generate_uncached()
                        row.update(tts_ms=tts_ms,first_pcm_ms=round((time.perf_counter()-start)*1000,2))
                if kind=='complete':row.update(llm=stream.metrics,reply=value)
        row['llm_observed_ms']=round((time.perf_counter()-start)*1000,2)
        if mode=='serial':
            audio,tts_ms=generate_uncached()
            row.update(tts_ms=tts_ms,first_pcm_ms=round((time.perf_counter()-start)*1000,2))
        assert row['reply']['reply_text']==TEXT
        data=Path(audio['path']).read_bytes()
        output=HERE/(str(index)+'-'+mode+'.wav');output.write_bytes(data)
        row.update(audio_sha256=hashlib.sha256(data).hexdigest(),audio_duration_seconds=audio['duration_seconds'],audio_path=str(output))
        report['cases'].append(row)
        (HERE/'pipeline_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(row,ensure_ascii=True),flush=True)
    report['summary']={mode:{key:round(statistics.median(r[key] for r in report['cases'] if r['mode']==mode),2) for key in ('speech_ready_ms','tts_ms','first_pcm_ms')} for mode in ('overlap','serial')}
    report['audio_bit_identical']=len({r['audio_sha256'] for r in report['cases']})==1
    (HERE/'pipeline_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'summary':report['summary'],'audio_bit_identical':report['audio_bit_identical']}),flush=True)
finally:worker.close()
