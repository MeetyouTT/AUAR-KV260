"""Public-input model diagnostics with fixed HTTP/error metadata; no user context."""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
import uuid

STARTUP = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(STARTUP.read_bytes()).hexdigest() == '71431dc7d7ffcf8fa824f03ae984488afec22b96f546bd3cd66e002fca8f7883'
cfg = json.loads(STARTUP.read_bytes())
sys.path.insert(0, str(Path(cfg['runtime']) / 'aura'))
from common.character_profile import selected_profile
from board.runtime.board_memory_policy import BoardContextBuilder, message_cost
from board.runtime.board_dialogue import validate_model_reply, address_reply


def request(method, path, payload=None):
    connection = http.client.HTTPConnection('192.168.50.1', 8797, timeout=65)
    try:
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        connection.request(method, path, body, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(1048577)
        assert len(raw) <= 1048576
        return response.status, json.loads(raw)
    finally:
        connection.close()


boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
session = 'public-no-output-' + uuid.uuid4().hex
question = '你好，先和我打个招呼吧。'
rows = []
for generation, (label, thinking, reserve) in enumerate((
        ('THINK_192', True, 192), ('THINK_120', True, 120), ('NORMAL_120', False, 120)), 1):
    status, health = request('GET', '/health')
    assert status == 200 and health['ok']
    was_busy = bool(health['active'] or health['pending'])
    builder = BoardContextBuilder(selected_profile().persona_full_prompt, output_reserve=reserve)
    messages = builder(dict(messages=[], facts=[], conversation_address=dict(display_name='测试甲',
        face=dict(state='UNKNOWN', display_name=None, face_count=0))), question)
    payload = dict(protocol_version=1, request_id='public-no-output-' + uuid.uuid4().hex,
        board_boot_id=boot, session_id=session, generation=generation, budget_ms=60000,
        task='dialogue', messages=messages,
        options=dict(think=thinking, num_predict=reserve))
    from common.model_inference_wire import validate_request
    validate_request('llm', payload)
    began = time.monotonic()
    status, response = request('POST', '/v1/inference/llm', payload)
    row = dict(case=label, http_status=status, ok=response.get('ok'), host_busy_at_submission=was_busy,
        elapsed_seconds=round(time.monotonic() - began, 3), context_upper_bound=message_cost(messages, reserve),
        options=payload['options'])
    if response.get('ok'):
        result = response['result']
        try:
            reply = address_reply(validate_model_reply(result['text'], question), '测试甲')
            row.update(valid_final_reply=True, contains_selected_name='测试甲' in reply.text,
                       reply_characters=len(reply.text))
        except Exception as error:
            row.update(valid_final_reply=False, validation_error_class=type(error).__name__)
        row['metrics'] = result.get('metrics')
    else:
        row['error'] = response.get('error')
    rows.append(row)
print(json.dumps(dict(schema='aura-public-thinking-no-output-diagnostics-1', status='PUBLIC_MODEL_COMPARISON_FINISHED',
    checks=rows, model_requests_issued=sum('http_status' in row for row in rows),
    private_store_reads=0, microphone_enable_calls=0, TTS_calls=0, playback_calls=0,
    device_or_flag_mutations=0, public_inputs_only=True)))
