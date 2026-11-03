"""Capture current accepted route without playback, history commits or config edits."""
import json
from pathlib import Path
import sys
import time
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.dialogue_stream import OllamaReplyStream

report={'actual_llm':True,'actual_tts':False,'actual_playback':False,'cases':[]}
for text in ('你好汐蓝，今天过得怎么样','今天比较开心，陪我聊聊','今天有点累，想和你说说话'):
    with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as response:
        health=json.load(response)
    assert health['ready'] and not health['busy']
    started=time.perf_counter()
    stream=OllamaReplyStream('http://127.0.0.1:11435','aura-qwen3.8-27b-abliterated:iq4_xs',[],text,90,reply_first=True,compact_grammar=True)
    row={'input':text}
    for kind,value in stream:
        if kind=='speech_ready':row['speech_ready_ms']=round((time.perf_counter()-started)*1000,2)
        if kind=='complete':row['reply']=value
    row.update(total_ms=round((time.perf_counter()-started)*1000,2),metrics=stream.metrics,raw_reply=stream.raw_reply)
    report['cases'].append(row)
    (HERE/'original_baseline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(row,ensure_ascii=True),flush=True)
