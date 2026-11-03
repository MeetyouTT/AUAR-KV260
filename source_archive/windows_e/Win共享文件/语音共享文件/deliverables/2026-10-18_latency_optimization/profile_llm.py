"""Profile the existing 27B without changing its weights, prompt or output budget."""
import argparse
import http.client
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.dialogue_host_ollama import chat_body,fast_system_prompt
from tools.dialogue_stream import ReplyDecoder
MODEL=json.loads((ROOT/'aura/config/board_dialogue_model.json').read_text(encoding='utf-8'))['model']

def get(url):
    with urllib.request.urlopen(url,timeout=4) as response:return json.load(response)

def measure(text,*,variant='baseline',history=None):
    if get('http://192.168.50.1:8792/health')['busy']:raise RuntimeError('User voice request active; benchmark stopped')
    body=chat_body(MODEL,fast_system_prompt(),text,history or [],fast=True)
    body['stream']=True;body['options']['seed']=42
    if variant=='text_only_probe':
        # Diagnostic only; this is never activated as the application protocol.
        body.pop('format',None)
        body['messages'][0]['content']=fast_system_prompt().split('输出JSON')[0]+'仅输出说出口的台词。'
    if variant=='reply_schema':
        body['format']={'type':'object','properties':{'reply_text':{'type':'string'}},
                        'required':['reply_text'],'additionalProperties':False}
    if variant=='reply_first_keys':
        mapping={'a_reply_text':'reply_text','b_emotion':'emotion','c_avatar_action':'avatar_action'}
        body['format']['properties']={key:body['format']['properties'][value] for key,value in mapping.items()}
        body['format']['required']=list(mapping)
        for key,value in mapping.items():body['messages'][0]['content']=body['messages'][0]['content'].replace(value,key)
    else:mapping=None
    decoder=ReplyDecoder(field_names=mapping);raw_text='';first_packet=first_delta=first_reply=None
    count=0;started=time.perf_counter();conn=http.client.HTTPConnection('127.0.0.1',11435,timeout=100)
    try:
        conn.request('POST','/api/chat',json.dumps(body,ensure_ascii=False).encode(),{'Content-Type':'application/json'})
        response=conn.getresponse()
        if response.status!=200:raise RuntimeError(response.read(2000).decode())
        while True:
            raw=response.readline(65537)
            if not raw or len(raw)>65536:raise ValueError('Invalid model stream')
            packet=json.loads(raw);elapsed=(time.perf_counter()-started)*1000
            if first_packet is None:first_packet=elapsed
            delta=(packet.get('message') or {}).get('content','')
            if delta:
                if first_delta is None:first_delta=elapsed
                raw_text+=delta;count+=1
                if variant=='text_only_probe':
                    if first_reply is None:first_reply=elapsed
                else:
                    spoken=decoder.feed(delta)
                    if spoken and first_reply is None:first_reply=elapsed
            if packet.get('done'):break
        if variant in ('baseline','reply_first_keys'):decoder.finish()
        keys=list(json.loads(raw_text)) if variant!='text_only_probe' else []
        return {'variant':variant,'text':text,'first_packet_ms':round(first_packet,2),
                'first_raw_content_ms':round(first_delta,2),'first_reply_text_ms':round(first_reply,2),
                'elapsed_ms':round((time.perf_counter()-started)*1000,2),'reply_json':raw_text,
                'output_key_order':keys,'content_packets':count,
                'ollama':{key:packet.get(key) for key in ('load_duration','prompt_eval_count','prompt_eval_duration',
                            'eval_count','eval_duration','total_duration','done_reason')}}
    finally:conn.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variants',nargs='+',default=['baseline'])
    parser.add_argument('--rounds',type=int,default=1);parser.add_argument('--output',default='llm_profile.json')
    args=parser.parse_args()
    report={'model':MODEL,'version':get('http://127.0.0.1:11435/api/version'),
            'loaded_before':get('http://127.0.0.1:11435/api/ps'),'seed':42,'cases':[]}
    gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True)
    report['gpu_before']=gpu.stdout.strip()
    path=HERE/args.output
    for index in range(args.rounds):
        for text in ('你猜猜我是谁啊','我今天有点累，陪我聊聊'):
            for variant in args.variants:
                case=measure(text,variant=variant);case['round']=index;report['cases'].append(case)
                path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                print(json.dumps(case,ensure_ascii=True),flush=True)
    report['loaded_after']=get('http://127.0.0.1:11435/api/ps')
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
