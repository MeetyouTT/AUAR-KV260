"""Actual per-request thinking capability test; no production settings changed.

Stores only final answers and reasoning-presence counts, never reasoning text.
This is not a test of automatic routing, feedback audio or board playback.
"""
import http.client
import json
from pathlib import Path
import re
import socket
import sys
import threading
import time
from urllib.parse import urlsplit

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.dialogue_host_ollama import chat_body,fast_system_prompt

def main():
    config=json.loads((ROOT/'aura/config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
    target=urlsplit(config['ollama_host'])
    question='一件商品原价240元，先打八折，再减30元，最后加12元运费，实付多少钱？请给出金额和一句简短核对。'
    results=[]
    for thinking in (False,True):
        body=chat_body(config['model'],fast_system_prompt(),question,fast=True)
        body.update(stream=True,think=thinking)
        body['options'].update(num_predict=512,temperature=0,seed=42)
        conn=http.client.HTTPConnection(target.hostname,target.port,timeout=90)
        timer=None
        row={'thinking_enabled':thinking,'model':config['model'],'question':question,
             'expected_amount':174,'first_content_ms':None,'first_thinking_ms':None,'thinking_characters':0}
        content=''
        started=time.monotonic()
        try:
            conn.connect()
            connected=conn.sock
            def expire(sock=connected):
                try:sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            timer=threading.Timer(90,expire);timer.daemon=True;timer.start()
            conn.request('POST','/api/chat',json.dumps(body).encode(),{'Content-Type':'application/json'})
            response=conn.getresponse()
            if response.status!=200:raise RuntimeError('Ollama HTTP '+str(response.status))
            while True:
                raw=response.readline(32769)
                if not raw or len(raw)>32768:raise ValueError('Incomplete/oversized Ollama packet')
                packet=json.loads(raw)
                if packet.get('error'):raise RuntimeError(str(packet['error'])[:160])
                message=packet.get('message') or {}
                thought=message.get('thinking') or ''
                text=message.get('content') or ''
                elapsed=round((time.monotonic()-started)*1000,2)
                if thought:
                    if row['first_thinking_ms'] is None:row['first_thinking_ms']=elapsed
                    row['thinking_characters']+=len(thought)
                if text:
                    if row['first_content_ms'] is None:row['first_content_ms']=elapsed
                    content+=text
                if packet.get('done'):
                    row.update({key:packet.get(key) for key in ('done_reason','load_duration','prompt_eval_duration',
                               'prompt_eval_count','eval_duration','eval_count')})
                    break
            row['final_json']=json.loads(content)
            answer=str(row['final_json'].get('reply_text',''))
            row['amount_correct']=bool(re.search(r'(?<!\d)174(?!\d)',answer))
            row['status']='PASS_NATIVE_CAPABILITY' if row['amount_correct'] and (not thinking or row['thinking_characters']>0) else 'FAIL'
        except Exception as exc:
            row.update(status='FAIL',error=type(exc).__name__+': '+str(exc)[:200],final_output=content)
        finally:
            if timer:timer.cancel()
            conn.close()
        row['total_ms']=round((time.monotonic()-started)*1000,2)
        results.append(row)
        print(json.dumps(row,ensure_ascii=True),flush=True)
        (HERE/'native_thinking.json').write_text(json.dumps({'production_configuration_changed':False,
            'automatic_routing_tested':False,'feedback_audio_tested':False,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()

