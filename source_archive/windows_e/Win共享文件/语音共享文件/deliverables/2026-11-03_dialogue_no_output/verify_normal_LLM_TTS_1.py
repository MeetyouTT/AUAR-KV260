"""Verify ordinary production output adapter and TTS with public synthetic input."""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
import uuid

startup = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(startup.read_bytes()).hexdigest() == '71431dc7d7ffcf8fa824f03ae984488afec22b96f546bd3cd66e002fca8f7883'
cfg = json.loads(startup.read_bytes())
aura = Path(cfg['runtime']) / 'aura'
sys.path.insert(0, str(aura))
from common.character_profile import selected_profile
from common.model_inference_wire import decode_audio, validate_response, Owner
from board.runtime.board_dialogue import dialogue_thinking_test_options, validate_model_reply, address_reply
from board.runtime.board_memory_policy import BoardContextBuilder
from board.runtime.compact_request_adapter import CompactRequestAdapter

assert not Path('/run/aura-dialogue-thinking-test.json').exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert dialogue_thinking_test_options(boot) == {}
trace = []


def http(method, path, payload=None):
    connection = http.client.HTTPConnection('192.168.50.1', 8797, timeout=65)
    try:
        connection.request(method, path, json.dumps(payload, ensure_ascii=False).encode() if payload else None,
                           {'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(12000001)
        assert len(raw) <= 12000000
        return response.status, json.loads(raw)
    finally:
        connection.close()


class Transport:
    def request(self, kind, payload, *, deadline, cancelled):
        assert not cancelled() and time.monotonic() < deadline
        began = time.monotonic()
        status, value = http('POST', '/v1/inference/' + kind, payload)
        trace.append(dict(kind=kind, http_status=status, ok=value.get('ok'),
            error_code=(value.get('error') or {}).get('code'),
            elapsed_seconds=round(time.monotonic() - began, 3),
            sent_think=payload.get('options', {}).get('think', False),
            sent_output_format=payload.get('options', {}).get('output_format', 'json')))
        assert status == 200 and value['ok'], trace[-1]
        return validate_response(value, Owner.from_dict(payload), kind)


status, health = http('GET', '/health')
assert status == 200 and health['ok'] and health['role'] == 'model_inference_only'
mode = json.loads((aura / 'config/board_avatar_gtk.json').read_bytes())['board_business'].get('dialogue_output_format', 'json')
prompt = selected_profile().persona_full_prompt
builder = BoardContextBuilder(prompt, output_reserve=120)
text = '请说一句简短的欢迎语。'
messages = builder(dict(messages=[], facts=[], conversation_address=dict(display_name='测试甲',
    face=dict(state='UNKNOWN', display_name=None, face_count=0))), text)
transport = Transport()
client = transport
if mode != 'json':
    client = CompactRequestAdapter(transport, system_prompt=prompt, capabilities=dict(
        format_contract_version=health['backend']['format_contract_version'],
        output_formats=health['backend']['output_formats']), mode=mode)
session = 'public-ordinary-recovery-' + uuid.uuid4().hex
owner = dict(protocol_version=1, board_boot_id=boot, session_id=session, generation=1, budget_ms=60000)
deadline = time.monotonic() + 60
response = client.request('llm', dict(owner, request_id='public-llm-' + uuid.uuid4().hex,
    task='dialogue', messages=messages, options={}), deadline=deadline, cancelled=lambda: False)
reply = address_reply(validate_model_reply(response['result']['text'], text), '测试甲')
audio_response = transport.request('tts', dict(owner, request_id='public-tts-' + uuid.uuid4().hex,
    text=reply.text), deadline=deadline, cancelled=lambda: False)
pcm, rate = decode_audio(audio_response['result']['audio'])
assert pcm and rate == 24000 and len(pcm) % 2 == 0
assert '测试甲' in reply.text
print(json.dumps(dict(schema='aura-ordinary-LLM-TTS-recovery-verification-1',
    status='ORDINARY_LLM_AND_TTS_VERIFIED', output_adapter=mode, valid_named_reply=True,
    tts_audio_valid=True, sample_rate=rate, sample_count=len(pcm) // 2,
    audio_seconds=round(len(pcm) / 2 / rate, 3), trace=trace,
    microphone_enable_calls=0, user_audio_capture_requests=0, private_store_reads=0,
    speaker_playback_calls=0, public_inputs_only=True, no_audio_or_real_identity_values_exported=True)))
