"""Real original-27B checks; synthetic text probes are not microphone accuracy."""
import json
from pathlib import Path
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'aura'))
from common.spoken_input import prepare_spoken_input
from tools.dialogue_stream import OllamaReplyStream

config = json.loads((ROOT / 'aura/config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
report = {'actual_27b': True, 'actual_asr': False, 'actual_playback': False, 'cases': []}
for text in ('你好西兰今天过得怎么样', '我喜欢吃西兰花', '我朋友叫西兰不是汐蓝', '十五还是五十我刚才没说清'):
    with urllib.request.urlopen('http://192.168.50.1:8792/health', timeout=3) as r:
        assert not json.load(r)['busy'], 'Live user voice request active'
    interpreted = prepare_spoken_input(text)
    stream = OllamaReplyStream(config['ollama_host'], config['model'], [], interpreted['text'], 90, reply_first=True)
    reply = None
    try:
        for kind, value in stream:
            if kind == 'complete':
                reply = value
    finally:
        stream.cancel()
    assert reply is not None
    result = dict(interpreted, reply=reply, metrics=stream.metrics)
    report['cases'].append(result)
    (HERE / 'interpretation_probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True), flush=True)
