"""Explicit numeric reasoning route and actual pipeline-clip content screens."""
import json
from pathlib import Path
import sys
import time

BASE=Path(__file__).resolve().parent
OUT=BASE/'selected-pipeline'
ROOT=BASE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.dialogue_stream import OllamaReplyStream
from common.thinking_policy import route
from probe_cuda_variants import transcribe,normalize,distance

def main():
    # The earlier Chinese-number math sample routed to chat. Do not count it
    # as proof of native reasoning; explicitly verify this distinct route.
    text='请帮我认真计算，58乘3等于多少？说明推理过程和结果。'
    plan=route(text);assert plan['mode']=='reasoning',plan
    stream=OllamaReplyStream('http://127.0.0.1:11435','aura-qwen3.8-27b-abliterated:iq4_xs',[],text,120,think=True,num_predict=768,reply_first=True,compact_grammar=True)
    report={'input':text,'route':plan,'actual_27b':True,'actual_tts':False,'native_thinking':True,'num_predict':768,'feedback_not_counted':True}
    start=time.perf_counter()
    for kind,value in stream:
        if kind=='text':report.setdefault('first_answer_text_ms',round((time.perf_counter()-start)*1000,2))
        elif kind=='speech_ready':report['spoken_field_ready_ms']=round((time.perf_counter()-start)*1000,2)
        elif kind=='complete':report['reply']=value
    report['total_ms']=round((time.perf_counter()-start)*1000,2);report['metrics']=stream.metrics
    (OUT/'complex_llm.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    pipeline=json.loads((OUT/'pipeline.json').read_text(encoding='utf-8'))
    checks=[]
    for row in pipeline['cases']:
        recognized=transcribe(row['tts']['wav']);expected=row['reply']['reply_text']
        checks.append({'expected':expected,'asr_text':recognized,'character_error_rate_raw':distance(normalize(expected),normalize(recognized))/len(normalize(expected)),'note':'Digits versus spoken Chinese numerals may require semantic review.'})
    (OUT/'pipeline_content.json').write_text(json.dumps({'cases':checks},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'reasoning_first_text_ms':report.get('first_answer_text_ms'),'reasoning_spoken_ready_ms':report.get('spoken_field_ready_ms'),'reply':report.get('reply'),'pipeline_content':checks},ensure_ascii=True))

if __name__=='__main__':main()
