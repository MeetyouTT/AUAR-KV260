"""ABBA native-27B experiment: program restores the already-fixed empty action."""
import http.client,json,sys,time,urllib.request,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.dialogue_stream import stream_body
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'
report={'actual_llm':True,'actual_tts':False,'actual_playback':False,'deployed':False,'cases':[]}
questions=['你好汐蓝今天过得怎么样','今天比较开心，陪我聊聊']
for variant in ('three_fields','two_fields','two_fields','three_fields'):
    for text in questions:
        with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as r:assert not json.load(r)['busy']
        body=stream_body(MODEL,[],text,reply_first=True)
        body['options']['seed']=42
        if variant=='two_fields':
            del body['format']['properties']['c'];body['format']['required'].remove('c')
            body['messages'][0]['content']=body['messages'][0]['content'].replace('，c为空字符串','')
        conn=http.client.HTTPConnection('127.0.0.1',11435,timeout=90)
        row={'variant':variant,'input':text,'seed':42,'request':body};raw_json=''
        start=time.perf_counter()
        try:
            conn.request('POST','/api/chat',json.dumps(body).encode(),{'Content-Type':'application/json'})
            response=conn.getresponse();assert response.status==200,response.read(2000)
            while True:
                line=response.readline(32769);assert line and len(line)<=32768
                packet=json.loads(line);assert not packet.get('error'),packet
                raw_json+=packet.get('message',{}).get('content') or ''
                elapsed=round((time.perf_counter()-start)*1000,2)
                # Locate the end of the first JSON string value without assuming
                # pretty/compact whitespace, punctuation or escaped characters.
                colon=raw_json.find(':')
                if colon>=0 and 'speech_ready_ms' not in row:
                    try:
                        spoken,end=json.JSONDecoder().raw_decode(raw_json[colon+1:].lstrip())
                        if isinstance(spoken,str):row.update(reply_text=spoken,speech_ready_ms=elapsed)
                    except json.JSONDecodeError:pass
                if packet.get('done'):
                    parsed=json.loads(raw_json)
                    assert set(parsed)==({'a','b'} if variant=='two_fields' else {'a','b','c'})
                    assert parsed['b'] in {'neutral','friendly','happy','sad'}
                    if variant=='three_fields':assert parsed['c']==''
                    row.update(raw_reply=raw_json,reply=parsed,total_ms=elapsed,
                               metrics={k:packet.get(k) for k in ('prompt_eval_count','eval_count','prompt_eval_duration','eval_duration')})
                    break
        finally:conn.close()
        report['cases'].append(row)
        (HERE/'native_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:row[k] for k in ('variant','input','reply','speech_ready_ms','total_ms')},ensure_ascii=True),flush=True)
report['summary']={v:{k:round(statistics.median(c[k] for c in report['cases'] if c['variant']==v),2) for k in ('speech_ready_ms','total_ms')} for v in ('three_fields','two_fields')}
(HERE/'native_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report['summary']),flush=True)
