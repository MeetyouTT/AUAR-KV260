"""Unchanged live 27B -> independent streaming voice; excludes ASR/playback."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import time
from probe_streaming import request

BASE=Path(__file__).resolve().parent
HERE=Path(os.environ.get('AURA_TTS_TRIAL_DIR',str(BASE)))
ROOT=BASE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from common.thinking_policy import route
from tools.dialogue_stream import OllamaReplyStream

def main():
    report={'status':'RUNNING','actual_27b':True,'actual_tts':True,'actual_asr':False,'actual_playback':False,'cases':[]}
    inputs=('你好汐蓝，今天过得怎么样','今天比较开心，陪我聊聊','请帮我算一下，三件商品每件58元，一共多少钱？')
    with ThreadPoolExecutor(max_workers=1) as executor:
        for index,text in enumerate(inputs):
            plan=route(text);opts={'think':True,'num_predict':768} if plan['mode']=='reasoning' else {}
            stream=OllamaReplyStream('http://127.0.0.1:11435','aura-qwen3.8-27b-abliterated:iq4_xs',[],text,120,reply_first=True,compact_grammar=True,**opts)
            start=time.perf_counter();spoken='';future=None;row={'input':text,'route':plan}
            for kind,value in stream:
                if kind=='text':
                    row.setdefault('first_text_ms',round((time.perf_counter()-start)*1000,2));spoken+=value
                elif kind=='speech_ready':
                    row['spoken_field_ready_ms']=round((time.perf_counter()-start)*1000,2)
                    future=executor.submit(request,spoken,chunk_tokens=25,name=f'pipeline-{index}')
                elif kind=='complete':row['reply']=value
            row['llm_complete_ms']=round((time.perf_counter()-start)*1000,2)
            assert future is not None and row['reply']['reply_text']==spoken
            row['tts']=future.result();row['llm_metrics']=dict(stream.metrics)
            row['first_pcm_from_input_ms']=round(row['spoken_field_ready_ms']+row['tts']['first_pcm_ms'],2)
            row['continuous_start_from_input_ms']=round(row['spoken_field_ready_ms']+row['tts']['earliest_no_underflow_start_ms'],2)
            report['cases'].append(row)
            (HERE/'pipeline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in row.items() if k not in ('tts','llm_metrics')},ensure_ascii=True),flush=True)
    report['status']='COMPLETE_EXCLUDES_ASR_AND_PLAYBACK'
    (HERE/'pipeline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
