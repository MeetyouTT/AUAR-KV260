"""Public board-side network/model probe; stdin execution, no media or DB IO.

CONTRACT_SOURCES and EXPECTED_BOOT are supplied by the pinned host entry point.
No payload, model text, PCM or executable file is written on the board.
"""
import base64
import hashlib
import http.client
import json
import sys
import time
import types
import uuid

common = types.ModuleType('common')
common.__path__ = []
sys.modules['common'] = common
for name in ('inference_output_contract', 'model_inference_wire'):
    module = types.ModuleType('common.' + name)
    sys.modules[module.__name__] = module
    exec(compile(base64.b64decode(CONTRACT_SOURCES[name]), '<production-' + name + '>', 'exec'), module.__dict__)
wire = sys.modules['common.model_inference_wire']


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def request(path, payload=None):
    connection = http.client.HTTPConnection('192.168.50.1', 8797, timeout=130 if payload else 5)
    try:
        raw = json.dumps(payload, ensure_ascii=False).encode() if payload else None
        connection.request('POST' if payload else 'GET', path, raw, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(wire.MAX_RESPONSE + 1)
        require(response.status == 200 and len(raw) <= wire.MAX_RESPONSE, 'public_inference_http_failed')
        return json.loads(raw)
    finally:
        connection.close()


def main():
    with open('/proc/sys/kernel/random/boot_id', encoding='ascii') as stream:
        boot = stream.read().strip()
    require(boot == EXPECTED_BOOT, 'board_boot_changed')
    health = request('/health')
    require(health.get('ok') is True and health.get('protocol_version') == 1
            and health.get('role') == 'model_inference_only' and health.get('active') is False
            and health.get('pending') == 0 and health.get('backend', {}).get('tts_ready') is True,
            'board_network_health_not_ready')
    owner = dict(protocol_version=1, board_boot_id=boot, session_id='public-lan-' + uuid.uuid4().hex,
                 generation=1, budget_ms=120000)
    llm = dict(owner, request_id='public-lan-llm-' + uuid.uuid4().hex, task='dialogue',
               options={'think': False, 'num_predict': 48},
               messages=[{'role': 'system', 'content': '这是公开的专用网口联调，请简短回答。'},
                         {'role': 'user', 'content': '请说模型已经准备好了。'}])
    wire.validate_request('llm', llm)
    began = time.monotonic()
    response = request('/v1/inference/llm', llm)
    wire.validate_response(response, wire.Owner.from_dict(llm), 'llm')
    require(response.get('ok') is True and response['result']['text'], 'public_llm_rejected')
    llm_result = dict(request_id=llm['request_id'], characters=len(response['result']['text']),
                      seconds=round(time.monotonic() - began, 3))
    response = None
    nonce = str(uuid.uuid4().int % 1000000).zfill(6)
    tts = dict(owner, request_id='public-lan-tts-' + uuid.uuid4().hex,
               text='你好，专用网口模型联调成功。公开校验编号' + nonce + '。')
    wire.validate_request('tts', tts)
    began = time.monotonic()
    response = request('/v1/inference/tts', tts)
    wire.validate_response(response, wire.Owner.from_dict(tts), 'tts')
    require(response.get('ok') is True, 'public_tts_rejected')
    pcm, rate = wire.decode_audio(response['result']['audio'])
    require(rate == 24000 and len(pcm) > 0 and any(pcm), 'public_pcm_invalid')
    tts_result = dict(request_id=tts['request_id'], samples=len(pcm) // 2, sample_rate=rate,
                      sha256=hashlib.sha256(pcm).hexdigest(), seconds=round(time.monotonic() - began, 3),
                      unique_public_text=True)
    pcm = response = None
    after = request('/health')
    require(after.get('ok') is True and after.get('role') == 'model_inference_only'
            and after.get('active') is False and after.get('pending') == 0
            and after.get('backend', {}).get('tts_ready') is True, 'after_probe_health_not_ready')
    return dict(status='PUBLIC_BOARD_LLM_AND_TTS_RAM_ONLY_PASS', board_boot_id=boot,
                endpoint='http://192.168.50.1:8797', llm=llm_result, tts=tts_result,
                production_wire_sha256=hashlib.sha256(base64.b64decode(CONTRACT_SOURCES['model_inference_wire'])).hexdigest(),
                inference_output_contract_sha256=hashlib.sha256(base64.b64decode(CONTRACT_SOURCES['inference_output_contract'])).hexdigest(),
                audio_device_opened=False, audio_played=False, microphone_opened=False,
                business_database_opened=False, board_file_modified=False, response_text_or_pcm_archived=False)


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False))
