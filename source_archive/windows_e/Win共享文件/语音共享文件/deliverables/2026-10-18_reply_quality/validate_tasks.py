"""Actual guarded 27B: four-round recall, explicit transforms and seeded repair."""
import json,sys,time,urllib.request
from pathlib import Path
from unittest.mock import patch
from probe_quality import GUIDANCE
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools import dialogue_stream
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'
report={'actual_llm':True,'actual_playback':False,'turns':[],'extra_tasks':[]}

def run(text,history=None,seed=42,known_bad_candidate=False):
    with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as response:
        assert not json.load(response)['busy'],'User voice active; stop diagnostics'
    original=dialogue_stream.stream_body
    def seeded(*args,**kwargs):
        body=original(*args,**kwargs);body['options']['seed']=seed
        if known_bad_candidate:
            from common.spoken_input import SPEECH_INPUT_HINT
            body['messages'][0]['content']=body['messages'][0]['content'].replace(SPEECH_INPUT_HINT,SPEECH_INPUT_HINT+GUIDANCE).replace('不复述用户','不机械复述用户')
        return body
    stream=dialogue_stream.OllamaReplyStream('http://127.0.0.1:11435',MODEL,history or [],text,90,reply_first=True)
    record={'input':text,'seed':seed,'history_messages':len(history or []),'known_bad_candidate_fixture':known_bad_candidate}
    start=time.perf_counter();emitted=''
    with patch.object(dialogue_stream,'stream_body',seeded):
        for kind,value in stream:
            elapsed=round((time.perf_counter()-start)*1000,2)
            if kind=='text':
                emitted+=value
                record.setdefault('first_delivered_ms',elapsed)
            elif kind=='speech_ready':record['speech_ready_ms']=elapsed
            elif kind=='complete':record.update(reply=value,raw_reply=stream.raw_reply,metrics=stream.metrics,total_ms=elapsed)
    assert emitted==record['reply']['reply_text']
    return record

questions=['我叫小林，喜欢蓝色，请记住。','我现在改成喜欢绿色了，不喜欢红色。',
           '今天想聊些轻松的事情。','我说的数字是十五，不是五十。',
           '我叫什么，喜欢什么颜色，说过的数字是多少？']
history=[]
def save():
    (HERE/'task_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for question in questions:
    row=run(question,history);report['turns'].append(row)
    history=(history+[{'role':'user','content':question},{'role':'assistant','content':row['raw_reply']}])[-8:]
    save();print(json.dumps({'turn':len(report['turns']),'reply':row['reply'],'retries':row['metrics']['quality_retry_count']},ensure_ascii=True),flush=True)
answer=report['turns'][-1]['reply']['reply_text']
report['four_round_memory_correct']='小林' in answer and '绿' in answer and ('十五' in answer or '15' in answer)
for text,expected in [('请原样复述这句话：你好汐蓝今天过得怎么样？','你好汐蓝今天过得怎么样'),
                      ('请把“我今天很开新”改成正确写法。','开心')]:
    row=run(text);row['expected_content_present']=expected in row['reply']['reply_text']
    report['extra_tasks'].append(row);save()
    print(json.dumps({'task':text,'reply':row['reply'],'expected':row['expected_content_present'],'retries':row['metrics']['quality_retry_count']},ensure_ascii=True),flush=True)
row=run('你好汐蓝今天过得怎么样',seed=3,known_bad_candidate=True)
report['seeded_repair']=row
report['seeded_repair_triggered']=row['metrics']['quality_retry_count']==1
report['all_checks_pass']=report['four_round_memory_correct'] and all(r['expected_content_present'] and r['metrics']['quality_retry_count']==0 for r in report['extra_tasks']) and report['seeded_repair_triggered'] and not row['metrics']['possible_question_echo']
save();print(json.dumps({'all_checks_pass':report['all_checks_pass'],'repair':row},ensure_ascii=True),flush=True)
