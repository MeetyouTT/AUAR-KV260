"""Native same-model ABBA: original JSON schema vs compact equivalent grammar."""
import http.client,json,sys,time,urllib.request,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.dialogue_stream import ReplyDecoder,REPLY_FIRST_FIELDS,stream_body
GRAMMAR=r'''root ::= "{\"a\":" string ",\"b\":" emotion ",\"c\":\"\"}"
string ::= "\"" ([^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4}))* "\""
emotion ::= "\"neutral\"" | "\"friendly\"" | "\"happy\"" | "\"sad\""
'''
report={'actual_llm':True,'actual_tts':False,'actual_playback':False,'deployed':False,'cases':[],'native_port':51742}
def post(path,data):
    request=urllib.request.Request('http://127.0.0.1:51742'+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=10) as r:return json.load(r)
for variant in ('schema','compact','compact','schema'):
    for text in ('你好汐蓝今天过得怎么样','今天比较开心，陪我聊聊'):
        with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as r:assert not json.load(r)['busy']
        original=stream_body('aura-qwen3.8-27b-abliterated:iq4_xs',[],text,reply_first=True)
        prompt=post('/apply-template',{'messages':original['messages'],'chat_template_kwargs':{'enable_thinking':False},'enable_thinking':False,'add_generation_prompt':True})['prompt']
        body={'prompt':prompt,'stream':True,'n_predict':120,'temperature':.6,'top_k':20,'top_p':.95,'min_p':0.,'repeat_penalty':1.,'seed':42,'cache_prompt':True,'n_keep':4}
        if variant=='compact':body['grammar']=GRAMMAR
        else:body['json_schema']=original['format']
        decoder=ReplyDecoder(field_names=REPLY_FIRST_FIELDS);row={'variant':variant,'input':text,'request':body}
        conn=http.client.HTTPConnection('127.0.0.1',51742,timeout=90);start=time.perf_counter()
        try:
            conn.request('POST','/completion',json.dumps(body).encode(),{'Content-Type':'application/json'})
            response=conn.getresponse();assert response.status==200,response.read(2000)
            while True:
                line=response.readline(32769);assert line and len(line)<=32768
                if not line.startswith(b'data:'):continue
                packet=json.loads(line[5:]);assert not packet.get('error'),packet
                spoken=decoder.feed(packet.get('content') or '');elapsed=round((time.perf_counter()-start)*1000,2)
                if spoken:row.setdefault('first_reply_ms',elapsed)
                if 'reply_text' in decoder.values:row.setdefault('speech_ready_ms',elapsed)
                if packet.get('stop'):
                    row.update(reply=decoder.finish(),raw_reply=decoder.buffer,total_ms=elapsed,timings=packet.get('timings'),tokens_predicted=packet.get('tokens_predicted'))
                    break
        finally:conn.close()
        report['cases'].append(row)
        (HERE/'grammar_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:row[k] for k in ('variant','input','reply','speech_ready_ms','total_ms','tokens_predicted')},ensure_ascii=True),flush=True)
report['summary']={v:{k:round(statistics.median(c[k] for c in report['cases'] if c['variant']==v),2) for k in ('first_reply_ms','speech_ready_ms','total_ms','tokens_predicted')} for v in ('schema','compact')}
(HERE/'grammar_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report['summary']),flush=True)
