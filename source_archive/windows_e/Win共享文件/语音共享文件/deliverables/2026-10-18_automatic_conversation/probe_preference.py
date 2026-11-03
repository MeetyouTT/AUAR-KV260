"""Replay confirmed transcript fixtures, then let the original 27B freely recall.

This is a PC text probe, not a new microphone/board-playback acceptance.
"""
import hashlib,json,sys,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.board_model_host import ModelHost,MODEL,OLLAMA_HOST
from tools.dialogue_stream import OllamaReplyStream,wire_history_within_budget
from tests.framework.test_voice_channel import owner

model=ModelHost.__new__(ModelHost)
model.meta_lock=threading.Lock();model.histories={};model.wire_histories={}
model.pending_streams={};model.latest_generations={};model.preference_memories={}
digest=hashlib.sha256(b'controlled-probe-only').hexdigest()
counter=0
def commit(user,reply):
    global counter
    counter+=1;meta=owner('memory-probe%d'%counter,counter)
    raw=json.dumps({'a':reply,'b':'friendly','c':''},ensure_ascii=False,separators=(',',':'))
    model.register_stream(meta);model.complete_stream(meta,user,reply,480,digest,wire_reply=raw,reuse_previous_wire=True)
    model.acknowledge_stream({'context':meta,'voice_sample_count':480,'pcm_sha256':digest})
    return meta

observed=json.loads((HERE/'live_automatic_initial.json').read_text(encoding='utf-8'))
confirmed=[row for row in observed['rounds'].values() if row.get('ack',{}).get('committed') and row.get('turn',{}).get('audio_complete')]
for row in confirmed:meta=commit(row['transcript'],row['turn']['text'])
assert len(confirmed)>=5
cases=[]
for expected in ('绿色','蓝色','绿色'):
    if expected=='蓝色':
        meta=commit('我喜欢蓝色','记住啦。')
        for index in range(5):meta=commit('我们继续聊聊吧','好呀，今天过得怎么样？')
    elif cases:
        recent=json.loads((HERE/'live_memory_first_retest.json').read_text(encoding='utf-8'))
        row=next(row for row in recent['rounds'].values() if row.get('turn',{}).get('audio_complete') and '我喜欢绿色' in row.get('transcript',''))
        meta=commit(row['transcript'],row['turn']['text'])
        assert model.preference_memories[(meta['board_boot_id'],meta['session_id'])]['color']=='绿色'
        for index in range(5):meta=commit('今天继续聊吧','好的，我在听。')
    plain,wire=model.history_for_stream(meta)
    history=model.history_with_preferences(meta,wire,wire=True)
    assert len(plain)==8 and len(history)==10 and wire_history_within_budget(MODEL,history,'我喜欢什么颜色？')
    assert not any(expected in row['content'] for row in plain)
    stream=OllamaReplyStream(OLLAMA_HOST,MODEL,history,'我喜欢什么颜色？',120,reply_first=True,compact_grammar=True)
    start=time.monotonic();reply=None
    try:
        for kind,value in stream:
            if kind=='complete':reply=value;break
    finally:stream.cancel()
    cases.append({'expected':expected,'reply':reply,'seconds':round(time.monotonic()-start,3),
                  'metrics':stream.metrics,'history_messages':len(history),'recent_window_messages':len(plain),
                  'preference_aged_out_of_recent_window':True,
                  'passed':bool(reply and expected in reply['reply_text'])})
report={'status':'PASS_ORIGINAL_27B_AGED_OUT_PREFERENCE_RECALL' if all(row['passed'] for row in cases) else 'FAIL',
        'model':MODEL,'synthetic_history_ack_replay':True,'observed_confirmed_rounds_replayed':len(confirmed),
        'actual_27b_generation':True,'tts_or_board_playback':False,'cases':cases}
(HERE/'preference_27b_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
assert report['status'].startswith('PASS')
