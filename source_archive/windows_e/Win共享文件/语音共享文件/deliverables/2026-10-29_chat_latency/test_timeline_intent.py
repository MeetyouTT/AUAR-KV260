"""Ordinary dated conversation stays ordinary; explicit history remains scoped recall."""
import io
from pathlib import Path
from unittest.mock import patch
import pytest
from common.timeline import historical,recall_requested,query
from tools.device_client import recalling_history
from tools.voice_channel_source import channel_frames
from common.voice_channel import read_frame
from tests.framework import test_voice_channel as fixtures
@pytest.mark.parametrize('text',[
 '我今天有点累，陪我聊聊','你好，今天想和我聊什么','今天过得怎么样','今天聊什么',
 '今天天气真好','我昨天画了一幅画，鼓励我一下','昨天我很累，今天想休息',
 '我上周开始学画画，给我点建议','上次你提到画画，我今天开始练习了',
 '我去年开始工作，现在想调整作息','我今天准备聊聊旅行','昨天我去公园了',
 '你觉得我今天该做什么','我昨晚没睡好，陪我聊聊','今早精神不好，给我点建议',
 '昨天北京下雨了吗','去年世界杯冠军是谁','今天想和我聊什么',
 '不要回忆昨天，陪我聊聊','不用查看昨天的记录','回忆录怎么写','记忆力怎么提高',
 '周末想轻松一下，帮我想一个小活动','我正在学画画，鼓励我一下',
 '我昨天心情不好，你能陪我聊聊吗','我昨天很累，你有什么建议'] )
def test_regular_temporal_chat_does_not_start_archive_lookup(text):
 assert recall_requested(text) is False
 assert recalling_history(text) is False
@pytest.mark.parametrize('text',[
 '昨天我们聊了什么','今天我们聊了什么','刚才看到了什么','昨天下午杯子在哪',
 '上次我们聊到哪里了','之前那个是什么','回忆一下昨天','查询昨天',
 '总结今天发生的事','昨天看见了什么','今早我说过什么','我不记得昨天说了什么',
 '还记得昨天的杯子吗','接着上次的话题','上周我们讨论了哪些事','查看今天的对话记录',
 '我昨天吃了什么','我上周买了什么'] )
def test_actual_memory_requests_keep_history_routing(text):
 assert recall_requested(text) is True
 assert recalling_history(text) is True
def test_explicit_date_filter_and_delete_calendar_semantics_are_unchanged():
 assert historical('昨天') and not recall_requested('昨天')
 q=query('昨天',now=1793270000)
 assert q['historical'] and q['start']<q['end'] and q['error'] is None
@pytest.mark.parametrize('text,wants_history',[('我今天有点累，陪我聊聊',False),('昨天我们聊了什么',True)])
def test_actual_channel_uses_only_the_intended_context_provider(tmp_path,text,wants_history):
 models=fixtures.VoiceChannelTests().fixture_models(Path(tmp_path))
 captured=[]
 def factory(host,model,history,user,*args,**kwargs):
  captured.append(history);return fixtures.VoiceChannelTests.fake_stream()
 source={'role':'user','content':'【过去资料】昨天讨论了画画。'}
 with patch('tools.memory_timeline_host.memory_context',return_value=source) as memory,patch('tools.memory_timeline_host.live_context',return_value=None) as live:
  packets=list(channel_frames(models,fixtures.owner(),text,5,model='fixture',host='fixture',stream_factory=factory))
 assert memory.call_count==int(wants_history) and live.call_count==int(not wants_history)
 assert captured==[[source]] if wants_history else captured==[[]]
 assert read_frame(io.BytesIO(packets[-1]))[0]['kind']=='end'
