"""Counterbalanced original-27B trials of exact assistant history serialization.

Only experiments: the running host's history and configuration are untouched.
"""
import http.client
import argparse
import json
from pathlib import Path
import statistics
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'aura'))
from tools.dialogue_stream import ReplyDecoder, REPLY_FIRST_FIELDS, stream_body

MODEL = json.loads((ROOT / 'aura/config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))['model']
QUESTIONS = ('我叫小林，喜欢蓝色。请记住。',
             '我改主意了，现在更喜欢绿色，请更新。',
             '我叫什么名字，现在更喜欢什么颜色？')
TEMPLATE = json.loads((HERE / 'benchmark_template.json').read_text(encoding='utf-8'))


def measure(text, history, *, compact_output=False):
    with urllib.request.urlopen('http://192.168.50.1:8792/health', timeout=3) as r:
        assert not json.load(r)['busy'], 'User voice request active'
    body = json.loads(json.dumps(TEMPLATE['body']))
    assert body['model'] == MODEL
    body['messages'] = [body['messages'][0], *history, {'role': 'user', 'content': text}]
    if compact_output:
        body['messages'][0]['content'] += 'JSON用单行紧凑格式。'
    body['options']['seed'] = 42
    connection = http.client.HTTPConnection('127.0.0.1', 11435, timeout=90)
    decoder = ReplyDecoder(field_names=TEMPLATE['field_mapping'])
    raw_json = ''
    result = {'input': text, 'history_messages': len(history)}
    started = time.perf_counter()
    try:
        connection.request('POST', '/api/chat', json.dumps(body, ensure_ascii=False).encode(), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        assert response.status == 200, response.read(2000)
        while True:
            raw = response.readline(32769)
            assert raw and len(raw) <= 32768
            packet = json.loads(raw)
            assert not packet.get('error'), packet.get('error')
            delta = packet.get('message', {}).get('content') or ''
            raw_json += delta
            spoken = decoder.feed(delta)
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            if spoken and 'first_reply_ms' not in result:
                result['first_reply_ms'] = elapsed
            if 'reply_text' in decoder.values and 'speech_ready_ms' not in result:
                result['speech_ready_ms'] = elapsed
            if packet.get('done'):
                result.update(reply=decoder.finish(), raw_reply_json=raw_json, total_ms=elapsed)
                result['metrics'] = {key: packet.get(key) for key in ('prompt_eval_count', 'eval_count', 'prompt_eval_duration', 'eval_duration')}
                return result
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variants', nargs='+', default=['plain', 'exact_json', 'exact_json', 'plain'],
                        choices=['plain', 'exact_json', 'plain_compact_output'])
    parser.add_argument('--output', default='history_profile.json')
    args = parser.parse_args()
    path = HERE / args.output
    report = {'model': MODEL, 'seed': 42, 'actual_llm': True, 'actual_asr': False,
              'actual_playback': False, 'deployed': False, 'traces': []}
    for variant in args.variants:
        history = []
        trace = {'variant': variant, 'turns': []}
        for question in QUESTIONS:
            turn = measure(question, history, compact_output=variant == 'plain_compact_output')
            trace['turns'].append(turn)
            assistant = turn['raw_reply_json'] if variant == 'exact_json' else turn['reply']['reply_text']
            history = (history + [{'role': 'user', 'content': question},
                                  {'role': 'assistant', 'content': assistant}])[-8:]
            print(json.dumps({'variant': variant, 'turn': len(trace['turns']), **turn}, ensure_ascii=True), flush=True)
        last = trace['turns'][-1]['reply']['reply_text']
        trace['memory_update_correct'] = '小林' in last and '绿' in last
        report['traces'].append(trace)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        assert trace['memory_update_correct'], last
    report['summary'] = {}
    for variant in dict.fromkeys(args.variants):
        turns = [turn for trace in report['traces'] if trace['variant'] == variant for turn in trace['turns'][1:]]
        report['summary'][variant] = {key: round(statistics.median(turn[key] for turn in turns), 2)
                                      for key in ('first_reply_ms', 'speech_ready_ms', 'total_ms')}
        report['summary'][variant]['prefill_ms'] = round(statistics.median(turn['metrics']['prompt_eval_duration'] / 1e6 for turn in turns), 2)
        report['summary'][variant]['count'] = len(turns)
    report['all_memory_updates_correct'] = all(trace['memory_update_correct'] for trace in report['traces'])
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'summary': report['summary'], 'all_memory_updates_correct': report['all_memory_updates_correct']}))


if __name__ == '__main__':
    main()
