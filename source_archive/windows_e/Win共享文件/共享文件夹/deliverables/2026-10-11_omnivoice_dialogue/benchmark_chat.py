"""Small same-prompt latency and conversation-memory probe, not a quality score."""
import argparse
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'aura'))
from tools.dialogue_host_ollama import build_response,LAST_TIMINGS
parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);parser.add_argument('--output',required=True)
args=parser.parse_args();rows=[];history=[]
sys.stdout.reconfigure(encoding='utf-8')
for text in ['我给小实验起名叫蓝鲸，你记住就好。','刚才的小实验叫什么名字？','今天调试总是失败，有点烦。']:
    started=time.perf_counter()
    response=build_response({'transcript':text,'allowed_emotions':['neutral','friendly','happy','sad']},
        'ollama',args.model,history=history,strict=True,fast=True)
    rows.append(dict(input=text,reply=response['reply_text'],seconds=time.perf_counter()-started,timings=dict(LAST_TIMINGS)))
    history.extend([dict(role='user',content=text),dict(role='assistant',content=response['reply_text'])])
    print(json.dumps(rows[-1],ensure_ascii=False),flush=True)
(HERE/args.output).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
