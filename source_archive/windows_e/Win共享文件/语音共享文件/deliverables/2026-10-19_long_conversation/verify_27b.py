"""50 actual 27B text turns; controlled ACK simulation, never board listening."""
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'aura'))
from common.conversation_store import ConversationStore
from common.conversation_context import build_context
from tools.dialogue_stream import OllamaReplyStream
from tools.board_model_host import MODEL, OLLAMA_HOST
from tests.framework.test_voice_channel import owner

questions = {
    1: '我叫小林，叫我小林就好。',
    2: '请记住，我最喜欢绿色。',
    3: '我的项目叫海风，是一个陪伴玩偶。',
    4: '我计划周六去图书馆还书。',
    15: '我叫什么名字？',
    25: '我的项目叫什么？',
    35: '我最喜欢什么颜色？',
    40: '纠正一下，之后叫我小周，不要再叫小林。',
    45: '现在应该怎么称呼我？',
    50: '我计划周六去哪里做什么？',
}
checks = {15: ['小林'], 25: ['海风'], 35: ['绿色'], 45: ['小周'], 50: ['图书馆', '还书']}
topics = ['今天散步感觉很舒服，陪我聊一句吧。', '窗外的云很漂亮。',
          '我刚喝了杯温水。', '今天想听你说一句鼓励的话。', '聊聊安静的夜晚吧。']
cid = 'e' * 32
path = HERE / 'probe_conversations.sqlite3'
if path.exists():
    raise SystemExit('Probe database already exists; retain evidence and use a new run directory')
store = ConversationStore(path)
rows = []
for index in range(1, 51):
    health = json.load(urllib.request.urlopen('http://192.168.50.1:8792/health', timeout=4))
    if health['busy']:
        raise RuntimeError('Production foreground became busy; probe stopped')
    text = questions.get(index, topics[index % len(topics)])
    meta = owner('actual27b-%d' % index, index)
    store.begin(cid, meta, text, text)
    history, metrics = build_context(MODEL, store.records(cid, exclude=meta['request_id']), text)
    started = time.monotonic()
    stream = OllamaReplyStream(OLLAMA_HOST, MODEL, history, text, 90, reply_first=True)
    reply = None
    try:
        for kind, value in stream:
            if kind == 'complete':
                reply = value['reply_text']
    finally:
        stream.cancel()
    if reply is None:
        raise RuntimeError('No complete model reply')
    store.generated(meta, reply, 480, '0' * 64)
    store.played(meta, 480, '0' * 64)  # Explicit simulation: no TTS or acoustic claim.
    expected = checks.get(index)
    row = {'turn': index, 'input': text, 'reply': reply, 'context': metrics,
           'actual_model_metrics': stream.metrics, 'elapsed_seconds': time.monotonic() - started,
           'expected': expected, 'passed': None if expected is None else all(word in reply for word in expected)}
    rows.append(row)
    (HERE / 'actual_27b_turns.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    if index % 5 == 0 or expected:
        print(json.dumps({'turn': index, 'check': row['passed'], 'reply': reply}, ensure_ascii=True), flush=True)
    # Reopen to prove the next turn does not rely on an in-memory chat cache.
    store = ConversationStore(path)
summary = {'actual_model_turns': 50, 'checks': sum(row['expected'] is not None for row in rows),
           'passed': all(row['passed'] is not False for row in rows),
           'playback_ack': 'controlled_simulation_no_audio', 'board_listening_acceptance': False,
           'model': MODEL, 'context_limit': 2048, 'restart_store_each_turn': True}
(HERE / 'actual_27b_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary), flush=True)
