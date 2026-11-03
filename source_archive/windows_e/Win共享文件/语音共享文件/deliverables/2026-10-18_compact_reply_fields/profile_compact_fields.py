"""Paired real-27B probe; no running service config or model is modified."""
import http.client
import json
from pathlib import Path
import statistics
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'aura'))
from tools.dialogue_stream import ReplyDecoder
from tools.dialogue_host_ollama import chat_body, fast_system_prompt

MODEL = json.loads((ROOT / 'aura/config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))['model']
COMPACT = {'a': 'reply_text', 'b': 'emotion', 'c': 'avatar_action'}
LEGACY = {'a_reply_text': 'reply_text', 'b_emotion': 'emotion', 'c_avatar_action': 'avatar_action'}


def get(url):
    with urllib.request.urlopen(url, timeout=4) as r:
        return json.load(r)


def measure(text, history, compact):
    assert not get('http://192.168.50.1:8792/health')['busy'], 'Live user request active'
    body = chat_body(MODEL, fast_system_prompt(), text, history, fast=True)
    body.update(stream=True, think=False)
    body['options']['seed'] = 42
    fields = COMPACT if compact else LEGACY
    properties = body['format']['properties']
    body['format']['properties'] = {key: properties[value] for key, value in fields.items()}
    body['format']['required'] = list(fields)
    for key, value in fields.items():
        body['messages'][0]['content'] = body['messages'][0]['content'].replace(value, key)
    decoder = ReplyDecoder(field_names=fields)
    connection = http.client.HTTPConnection('127.0.0.1', 11435, timeout=90)
    start = time.perf_counter()
    result = {'variant': 'compact' if compact else 'current', 'input': text}
    try:
        connection.request('POST', '/api/chat', json.dumps(body, ensure_ascii=False).encode(), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        assert response.status == 200, response.read(2000)
        while True:
            raw = response.readline(32769)
            assert raw and len(raw) <= 32768, 'Invalid response packet'
            packet = json.loads(raw)
            assert not packet.get('error'), packet.get('error')
            delta = packet.get('message', {}).get('content') or ''
            spoken = decoder.feed(delta)
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            if spoken and 'first_reply_ms' not in result:
                result['first_reply_ms'] = elapsed
            if 'reply_text' in decoder.values and 'speech_ready_ms' not in result:
                result['speech_ready_ms'] = elapsed
            if packet.get('done'):
                result['reply'] = decoder.finish()
                result['total_ms'] = elapsed
                result['metrics'] = {key: packet.get(key) for key in ('prompt_eval_count', 'eval_count', 'prompt_eval_duration', 'eval_duration')}
                result['memory_correct'] = not history or all(word in result['reply']['reply_text'] for word in ('小林', '蓝色'))
                result['spoken_characters'] = len(result['reply']['reply_text'])
                return result
    finally:
        connection.close()


def main():
    history = [{'role': 'user', 'content': '我叫小林，喜欢蓝色。'},
               {'role': 'assistant', 'content': '小林，我记住啦，你喜欢蓝色。'}]
    report = {'model': MODEL, 'seed': 42, 'actual_models': True, 'actual_playback': False, 'deployed': False,
              'loaded_model': get('http://127.0.0.1:11435/api/ps'), 'cases': []}
    for text, prior, order in [('你好汐蓝，今天过得怎么样', [], (False, True, True, False)),
                               ('我叫什么名字，喜欢什么颜色？', history, (True, False, False, True))]:
        for compact in order:
            case = measure(text, prior, compact)
            report['cases'].append(case)
            (HERE / 'paired_profile.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(case, ensure_ascii=True), flush=True)
    report['summary'] = {variant: {metric: round(statistics.median(row[metric] for row in report['cases'] if row['variant'] == variant), 2)
                                   for metric in ('first_reply_ms', 'speech_ready_ms', 'total_ms')}
                         for variant in ('current', 'compact')}
    report['all_memory_checks_passed'] = all(row['memory_correct'] for row in report['cases'])
    (HERE / 'paired_profile.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'summary': report['summary'], 'all_memory_checks_passed': report['all_memory_checks_passed']}))


if __name__ == '__main__':
    main()
