"""Seeded baseline/candidate greeting check; never plays or commits history."""
import json, sys, time, urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'aura'))
from tools.dialogue_stream import stream_body
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'
report={'actual_llm':True,'actual_playback':False,'cases':[]}
for seed in (42,7,123):
    for variant in ('baseline','direct_answer'):
        body=stream_body(MODEL,[],'你好汐蓝今天过得怎么样',reply_first=True)
        if variant=='direct_answer':
            body['messages'][0]['content']+='直接回答对方的问题，不把对方的话当成需要校对或改写的句子。'
        body['stream']=False
        body['options']['seed']=seed
        with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as r:
            assert not json.load(r)['busy']
        start=time.perf_counter()
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11435/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=90) as r:
            result=json.load(r)
        reply=json.loads(result['message']['content'])['a']
        item={'seed':seed,'variant':variant,'reply':reply,'elapsed_ms':round((time.perf_counter()-start)*1000,2),'prompt_tokens':result['prompt_eval_count']}
        report['cases'].append(item)
        (HERE/'greeting_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(item,ensure_ascii=True),flush=True)
