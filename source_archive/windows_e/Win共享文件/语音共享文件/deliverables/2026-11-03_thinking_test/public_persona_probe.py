"""Two public model-only checks using the selected live persona and test option."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

TASK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('board_transport', TASK.parent/'2026-10-18_board_dialogue/board_ssh.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
source = '''import http.client,json,sys,time,uuid
from pathlib import Path
startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
sys.path.insert(0,str(Path(json.loads(startup.read_bytes())['runtime'])/'aura'))
from common.character_profile import selected_profile
from board.runtime.board_dialogue import dialogue_thinking_test_options,validate_model_reply,address_reply
from board.runtime.board_memory_policy import BoardContextBuilder,message_cost
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
session='public-persona-thinking-'+uuid.uuid4().hex
options=dialogue_thinking_test_options(boot);assert options==dict(think=True,num_predict=192)
def request(method,path,payload=None):
    c=http.client.HTTPConnection('192.168.50.1',8797,timeout=120)
    try:
        c.request(method,path,body=json.dumps(payload,ensure_ascii=False).encode() if payload else None,headers={'Content-Type':'application/json'})
        r=c.getresponse();raw=r.read(1000000)
        if r.status!=200:raise RuntimeError('model_http_'+str(r.status)+'_'+raw[:512].decode('utf-8','replace'))
        return json.loads(raw)
    finally:c.close()
results=[]
for generation,text in enumerate(('请计算58乘以3，告诉我结果。','今天有点累，陪我轻松聊一句。'),1):
    health=request('GET','/health');assert health['ok'] and not health['active'] and health['pending']==0
    builder=BoardContextBuilder(selected_profile().persona_full_prompt,output_reserve=192)
    context=dict(messages=[],facts=[],conversation_address=dict(display_name='测试甲',face=dict(state='UNKNOWN',display_name=None,face_count=0)))
    messages=builder(context,text);cost=message_cost(messages,192);assert cost<=2048
    payload=dict(protocol_version=1,request_id='public-persona-thinking-'+uuid.uuid4().hex,board_boot_id=boot,
        session_id=session,generation=generation,budget_ms=120000,task='dialogue',messages=messages,options=options)
    started=time.monotonic();response=request('POST','/v1/inference/llm',payload);assert response['ok'],response
    reply=address_reply(validate_model_reply(response['result']['text'],text),'测试甲')
    if generation==1:assert '174' in reply.text
    assert '测试甲' in reply.text
    results.append(dict(question=text,reply=reply.text,options=options,context_upper_bound=cost,
        metrics=response['result'].get('metrics'),elapsed_seconds=round(time.monotonic()-started,3)))
print(json.dumps(dict(status='LIVE_PERSONA_THINKING_MODEL_CHECKS_PASSED',public_inputs_only=True,
    private_store_reads=0,tts_calls=0,playback_calls=0,checks=results)))
'''
record = dict(host_utc=datetime.now(timezone.utc).isoformat())
try:
    record['board_result'] = json.loads(transport.ssh('python3 -B -', source, timeout=260))
except Exception as error:
    record.update(status='FAILED', error_class=type(error).__name__, detail=str(error)[:1500])
(TASK/'PUBLIC_PERSONA_PROBE.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(record, ensure_ascii=False))
if 'board_result' not in record: raise SystemExit(1)
