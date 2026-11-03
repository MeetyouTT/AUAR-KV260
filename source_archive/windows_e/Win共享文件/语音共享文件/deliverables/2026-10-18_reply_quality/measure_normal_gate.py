"""Small ABBA real-model comparison, identical seeds and unchanged chat bodies."""
import json,sys,time,urllib.request
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools import dialogue_stream as module
report={'actual_llm':True,'actual_tts':False,'actual_playback':False,'cases':[],'not_a_statistical_latency_guarantee':True}
for seed,variant in [(0,'unchecked'),(0,'guarded'),(42,'guarded'),(42,'unchecked')]:
    with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as r:assert not json.load(r)['busy']
    original=module.stream_body
    def seeded(*args,**kwargs):
        body=original(*args,**kwargs);body['options']['seed']=seed;return body
    cls=module.OllamaReplyStream if variant=='guarded' else module._OllamaReplyAttempt
    stream=cls('http://127.0.0.1:11435','aura-qwen3.8-27b-abliterated:iq4_xs',[],'你好汐蓝今天过得怎么样',90,reply_first=True)
    row={'seed':seed,'variant':variant};start=time.perf_counter()
    with patch.object(module,'stream_body',seeded):
        for kind,value in stream:
            elapsed=round((time.perf_counter()-start)*1000,2)
            if kind=='text':row.setdefault('first_text_ms',elapsed)
            if kind=='speech_ready':row['speech_ready_ms']=elapsed
            if kind=='complete':row.update(reply=value,total_ms=elapsed,metrics=stream.metrics)
    report['cases'].append(row)
    (HERE/'normal_gate_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(row,ensure_ascii=True),flush=True)
report['same_seed_same_replies']=all(next(c for c in report['cases'] if c['seed']==seed and c['variant']=='guarded')['reply']==next(c for c in report['cases'] if c['seed']==seed and c['variant']=='unchecked')['reply'] for seed in (0,42))
report['normal_guarded_no_retry']=all(c['metrics']['quality_retry_count']==0 for c in report['cases'] if c['variant']=='guarded')
(HERE/'normal_gate_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
