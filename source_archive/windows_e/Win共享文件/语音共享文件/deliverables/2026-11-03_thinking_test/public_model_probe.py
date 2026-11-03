from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

TASK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('board_transport', TASK.parent/'2026-10-18_board_dialogue/board_ssh.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
source = '''import http.client,json,time,uuid
from pathlib import Path
def request(method,path,payload=None):
    c=http.client.HTTPConnection('192.168.50.1',8797,timeout=120)
    try:
        c.request(method,path,body=json.dumps(payload,ensure_ascii=False).encode() if payload else None,headers={'Content-Type':'application/json'})
        r=c.getresponse();raw=r.read(1000000);assert r.status==200,(r.status,raw[:100])
        return json.loads(raw)
    finally:c.close()
health=request('GET','/health');assert health['ok'] and not health['active'] and health['pending']==0
assert health['backend']['model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
payload=dict(protocol_version=1,request_id='public-thinking-'+uuid.uuid4().hex,
    board_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    session_id='public-thinking-test',generation=1,budget_ms=120000,task='dialogue',
    messages=[dict(role='system',content='你是测试助手。只返回JSON，字段reply_text为一句简短中文回答、emotion为friendly、avatar_action为空字符串。'),
              dict(role='user',content='请计算58乘以3，告诉我结果。')],options=dict(think=True,num_predict=192))
started=time.monotonic();response=request('POST','/v1/inference/llm',payload)
assert response['ok'],response
reply=json.loads(response['result']['text']);assert '174' in reply['reply_text'],reply
assert set(reply)=={'reply_text','emotion','avatar_action'}
print(json.dumps(dict(status='PUBLIC_THINKING_REQUEST_PASSED',elapsed_seconds=round(time.monotonic()-started,3),
    request_options=payload['options'],reply=reply,metrics=response['result'].get('metrics'),
    private_store_reads=0,tts_calls=0,playback_calls=0)))
'''
record = dict(host_utc=datetime.now(timezone.utc).isoformat(), public_inputs_only=True)
try:
    record['board_result'] = json.loads(transport.ssh('python3 -B -', source, timeout=130))
except Exception as error:
    record.update(status='FAILED', error_class=type(error).__name__, detail=str(error)[:1500])
(TASK/'PUBLIC_MODEL_PROBE.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(record, ensure_ascii=False))
if 'board_result' not in record: raise SystemExit(1)
