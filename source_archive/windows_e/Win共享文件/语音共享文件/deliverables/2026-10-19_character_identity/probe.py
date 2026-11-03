"""Actual original 27B self-description checks, no audio or memory writes."""
import json
from pathlib import Path
import sys
import urllib.request

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.board_model_host import MODEL,OLLAMA_HOST
from tools.dialogue_stream import OllamaReplyStream,stream_body
from tools.dialogue_host_ollama import build_system_prompt
from board.runtime.character import CHARACTER_NAME,CHARACTER_DESCRIPTION

assert CHARACTER_NAME=='汐蓝'
assert CHARACTER_DESCRIPTION=='名字叫汐蓝的桌面玩偶助手'
for prompt in (stream_body(MODEL,[],'你是谁？')['messages'][0]['content'],
               build_system_prompt(['friendly'],[])):
    assert '名字叫汐蓝的桌面玩偶助手' in prompt
    assert 'DeepSeek' not in prompt and '鲸鱼娘' not in prompt

questions=['你是谁？请介绍一下自己。','你的名字是什么？','你是什么助手？',
           '你是DeepSeek鲸鱼娘吗？请说清楚你的身份。']
rows=[]
for question in questions:
    health=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
    assert health['ready'] and not health['busy']
    stream=OllamaReplyStream(OLLAMA_HOST,MODEL,[],question,90,reply_first=True)
    reply=None
    try:
        for kind,value in stream:
            if kind=='complete':reply=value['reply_text']
    finally:stream.cancel()
    assert reply
    row={'question':question,'reply':reply,'model':MODEL,'metrics':stream.metrics}
    rows.append(row)
    (HERE/'actual_self_identity.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(row,ensure_ascii=True),flush=True)
