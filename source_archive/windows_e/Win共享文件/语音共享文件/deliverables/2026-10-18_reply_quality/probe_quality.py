"""Real-model task disambiguation probes; no audio, history commits or retries."""
import argparse,http.client,json,re,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.dialogue_stream import ReplyDecoder,REPLY_FIRST_FIELDS
from common.spoken_input import SPEECH_INPUT_HINT
TEMPLATE=json.loads((ROOT/'deliverables/2026-10-18_history_reuse/benchmark_template.json').read_text(encoding='utf-8'))['body']
GUIDANCE='语音转写是对方此刻对你说的话，理解意图后直接接话或解答；只有明确要求复述、转写或改写时才执行这些任务。'

def measure(text,variant,seed,history=None):
    with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as r:
        assert not json.load(r)['busy'],'User voice request active; stop diagnostics'
    body=json.loads(json.dumps(TEMPLATE))
    system=body['messages'][0]['content']
    if variant=='guidance':system=system.replace(SPEECH_INPUT_HINT,SPEECH_INPUT_HINT+GUIDANCE).replace('不复述用户','不机械复述用户')
    elif variant=='without_speech_hint':system=system.replace(SPEECH_INPUT_HINT,'')
    body['messages']=[{'role':'system','content':system},*(history or []),{'role':'user','content':text}]
    if seed is not None:body['options']['seed']=seed
    result={'input':text,'variant':variant,'seed':seed,'history_messages':len(history or []),'request':body}
    decoder=ReplyDecoder(field_names=REPLY_FIRST_FIELDS)
    conn=http.client.HTTPConnection('127.0.0.1',11435,timeout=90)
    start=time.perf_counter()
    try:
        conn.request('POST','/api/chat',json.dumps(body).encode(),{'Content-Type':'application/json'})
        response=conn.getresponse();assert response.status==200,response.read(2000)
        while True:
            raw=response.readline(32769);assert raw and len(raw)<=32768
            packet=json.loads(raw);assert not packet.get('error'),packet
            delta=packet.get('message',{}).get('content') or ''
            spoken=decoder.feed(delta);elapsed=round((time.perf_counter()-start)*1000,2)
            if spoken and 'first_reply_ms' not in result:result['first_reply_ms']=elapsed
            if 'reply_text' in decoder.values and 'speech_ready_ms' not in result:result['speech_ready_ms']=elapsed
            if packet.get('done'):
                result.update(reply=decoder.finish(),raw_reply=decoder.buffer,total_ms=elapsed)
                result['metrics']={k:packet.get(k) for k in ('prompt_eval_count','eval_count','prompt_eval_duration','eval_duration')}
                # A narrow observation for this greeting, not a production filter.
                norm=lambda t:re.sub(r'[\W_]+','',t)
                result['greeting_echo']=norm(result['reply']['reply_text']) in {'汐蓝今天过得怎么样','你好汐蓝今天过得怎么样'}
                return result
    finally:conn.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--variant',default='baseline',choices=['baseline','guidance','without_speech_hint'])
    parser.add_argument('--seeds',nargs='+',default=['random','random','0','1','2','3','4','5'])
    parser.add_argument('--text',default='你好汐蓝今天过得怎么样')
    parser.add_argument('--output',default='baseline.json')
    args=parser.parse_args();report={'actual_llm':True,'actual_playback':False,'cases':[]}
    for item in args.seeds:
        row=measure(args.text,args.variant,None if item=='random' else int(item))
        report['cases'].append(row)
        (HERE/args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:row[k] for k in ('variant','seed','reply','greeting_echo','speech_ready_ms')},ensure_ascii=True),flush=True)
if __name__=='__main__':main()
