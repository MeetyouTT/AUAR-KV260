"""Replay the same first-turn requests through before/current stream classes."""
import hashlib,importlib.util,json,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'aura'))
from tools import dialogue_stream as current
spec=importlib.util.spec_from_file_location('before_stream',HERE/'before/aura__tools__dialogue_stream.py')
before=importlib.util.module_from_spec(spec);spec.loader.exec_module(before)
model='aura-qwen3.8-27b-abliterated:iq4_xs'
question='你好汐蓝今天过得怎么样'
body=current.stream_body(model,[],question,reply_first=True)
assert body==before.stream_body(model,[],question,reply_first=True)
report={'actual_llm':True,'actual_playback':False,'body_equal_before':True,
        'request_body_sha256':hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest(),'cases':[]}
# Patch only the experiment modules to attach an identical reproducible seed.
for seed in (42,123):
    row={'seed':seed}
    for name,module in (('before',before),('current',current)):
        with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as r:
            assert not json.load(r)['busy']
        original=module.stream_body
        def seeded(*args,**kwargs):
            request=original(*args,**kwargs);request['options']['seed']=seed;return request
        module.stream_body=seeded
        stream=module.OllamaReplyStream('http://127.0.0.1:11435',model,[],question,90,reply_first=True)
        start=time.perf_counter()
        try:
            for kind,value in stream:
                if kind=='complete':row[name]={'reply':value,'elapsed_ms':round((time.perf_counter()-start)*1000,2)}
        finally:
            stream.cancel();module.stream_body=original
    row['same_reply']=row['before']['reply']==row['current']['reply']
    report['cases'].append(row)
    (HERE/'first_turn_equivalence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(row,ensure_ascii=True),flush=True)
