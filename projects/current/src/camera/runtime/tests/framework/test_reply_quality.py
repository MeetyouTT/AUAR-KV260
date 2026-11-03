"""Echo diagnostics distinguish a copied question from valid brief answers."""
import pytest
import hashlib,io,json
from unittest.mock import MagicMock,patch
from common.reply_quality import possible_question_echo
from tools.dialogue_stream import OllamaReplyStream,stream_body


@pytest.mark.parametrize('user,reply,flag',[
    ('你好汐蓝今天过得怎么样','汐蓝今天过得怎么样',True),
    ('你好，汐蓝，今天过得怎么样？','你好汐蓝今天过得怎么样',True),
    ('你今天为什么一直没有回答我','你今天为什么一直没有回答我？',True),
    ('你好汐蓝今天过得怎么样','还好呀，你呢？',False),
    ('你今天开心吗','开心。',False),
    ('你好汐蓝今天过得怎么样','你今天过得怎么样？',False),
    ('我今天比较开心陪我聊聊','我今天比较开心陪我聊聊',False),
    ('请原样复述：你好汐蓝今天过得怎么样','你好汐蓝今天过得怎么样',False),
    ('请改写这句话：你好汐蓝今天过得怎么样','你好汐蓝今天过得怎么样',False),
    ('不要复述，今天过得怎么样呀','不要复述今天过得怎么样呀',True),
    ('我喜欢什么颜色','你喜欢绿色呀。',False),
    ('我说的是十五不是五十你听清了吗','是十五，不是五十。',False),
])
def test_only_near_complete_question_copies_are_diagnostic(user,reply,flag):
    assert possible_question_echo(user,reply) is flag


def test_stream_records_exact_input_identity_without_changing_normal_answer():
    reply='还好呀，你呢？'
    user='你好汐蓝今天过得怎么样'
    raw=json.dumps({'a':reply,'b':'friendly','c':''},ensure_ascii=False)
    response=io.BytesIO((json.dumps({'message':{'content':raw},'done':True})+'\n').encode())
    response.status=200
    connection=MagicMock();connection.getresponse.return_value=response
    with patch('tools.dialogue_stream.http.client.HTTPConnection',return_value=connection):
        stream=OllamaReplyStream('http://localhost','same-27b',[],user,3,reply_first=True)
        events=list(stream)
    assert events[-1]==('complete',{'reply_text':reply,'emotion':'friendly','avatar_action':''})
    assert stream.raw_reply==raw
    assert stream.metrics['possible_question_echo'] is False
    assert stream.metrics['quality_retry_count']==0
    assert stream.metrics['input_sha256']==hashlib.sha256(user.encode()).hexdigest()
    prompt=stream_body('same-27b',[],user,reply_first=True)['messages'][0]['content']
    assert stream.metrics['system_prompt_sha256']==hashlib.sha256(prompt.encode()).hexdigest()
    assert connection.request.call_count==1  # No automatic second inference.


def connection_for(reply):
    raw=json.dumps({'a':reply,'b':'friendly','c':''},ensure_ascii=False)
    # Split inside the copied prefix to exercise incremental buffering.
    packets=[{'message':{'content':char},'done':False} for char in raw]
    packets.append({'message':{'content':''},'done':True})
    response=io.BytesIO(b''.join(json.dumps(row).encode()+b'\n' for row in packets));response.status=200
    connection=MagicMock();connection.getresponse.return_value=response
    return connection,raw


def test_copied_question_is_repaired_before_text_speech_or_history_can_escape():
    bad,_=connection_for('汐蓝今天过得怎么样')
    good,raw=connection_for('我挺好的呀，你呢？')
    with patch('tools.dialogue_stream.http.client.HTTPConnection',side_effect=[bad,good]) as requests:
        stream=OllamaReplyStream('http://localhost','same-27b',[],'你好汐蓝今天过得怎么样',3,reply_first=True)
        events=list(stream)
    assert ''.join(value for kind,value in events if kind=='text')=='我挺好的呀，你呢？'
    assert sum(kind=='speech_ready' for kind,_ in events)==1
    assert stream.raw_reply==raw and stream.metrics['quality_retry_count']==1
    assert stream.metrics['rejected_question_echo'] and len(stream.metrics['quality_attempts'])==2
    assert requests.call_count==2
    body=json.loads(good.request.call_args.args[2])
    assert len(body['messages'])==2 and body['messages'][-1]['content']=='你好汐蓝今天过得怎么样'
    assert '刚才的台词只复制了用户的问题' in body['messages'][0]['content']


def test_second_copy_fails_without_unbounded_retry_or_outgoing_wrong_text():
    first,_=connection_for('汐蓝今天过得怎么样');second,_=connection_for('汐蓝今天过得怎么样')
    events=[]
    with patch('tools.dialogue_stream.http.client.HTTPConnection',side_effect=[first,second]) as requests:
        stream=OllamaReplyStream('http://localhost','same-27b',[],'你好汐蓝今天过得怎么样',3,reply_first=True)
        with pytest.raises(ValueError,match='换个说法'):
            for event in stream:events.append(event)
    assert not events and stream.raw_reply is None and requests.call_count==2


def test_explicit_repetition_remains_one_inference_and_preserves_requested_words():
    connection,raw=connection_for('你好汐蓝今天过得怎么样')
    with patch('tools.dialogue_stream.http.client.HTTPConnection',return_value=connection):
        stream=OllamaReplyStream('http://localhost','same-27b',[],'请原样复述：你好汐蓝今天过得怎么样',3,reply_first=True)
        events=list(stream)
    assert events[-1][1]['reply_text']=='你好汐蓝今天过得怎么样'
    assert stream.raw_reply==raw and stream.metrics['quality_retry_count']==0
    assert connection.request.call_count==1


def test_normal_answer_with_shared_question_prefix_is_released_unmodified():
    connection,_=connection_for('汐蓝今天过得挺开心呀，你呢？')
    with patch('tools.dialogue_stream.http.client.HTTPConnection',return_value=connection):
        stream=OllamaReplyStream('http://localhost','same-27b',[],'你好汐蓝今天过得怎么样',3,reply_first=True)
        events=list(stream)
    assert ''.join(value for kind,value in events if kind=='text')=='汐蓝今天过得挺开心呀，你呢？'
    assert stream.metrics['quality_retry_count']==0 and connection.request.call_count==1


def test_cancel_after_rejection_prevents_a_second_request():
    first,_=connection_for('汐蓝今天过得怎么样')
    from tools.dialogue_stream import _OllamaReplyAttempt
    original=_OllamaReplyAttempt.__iter__
    def cancel_on_complete(instance):
        for kind,value in original(instance):
            if kind=='complete':instance.cancel()
            yield kind,value
    with patch('tools.dialogue_stream.http.client.HTTPConnection',return_value=first) as requests,patch.object(_OllamaReplyAttempt,'__iter__',cancel_on_complete):
        stream=OllamaReplyStream('http://localhost','same-27b',[],'你好汐蓝今天过得怎么样',3,reply_first=True)
        with pytest.raises(InterruptedError):list(stream)
    assert requests.call_count==1
    assert stream.raw_reply is None


@pytest.mark.parametrize('repair_succeeds',[True,False])
def test_channel_synthesizes_and_prepares_memory_only_for_an_accepted_reply(tmp_path,repair_succeeds):
    from tests.framework import test_voice_channel as fixture
    from tools.voice_channel_source import channel_frames
    from common.voice_channel import read_frame
    models=fixture.VoiceChannelTests().fixture_models(tmp_path)
    models.latency_options={'reply_first':True,'early_sentence':True,'coalesce_chat':True,'reuse_history':True}
    models.complete_stream=MagicMock()
    models.voice.generate=MagicMock(wraps=models.voice.generate)
    first,_=connection_for('汐蓝今天过得怎么样')
    second,raw=connection_for('我挺好的呀，你呢？' if repair_succeeds else '汐蓝今天过得怎么样')
    with patch('tools.dialogue_stream.http.client.HTTPConnection',side_effect=[first,second]):
        packets=list(channel_frames(models,fixture.owner(),'你好汐蓝今天过得怎么样',4,model='same-27b',host='http://localhost',feedback=True))
    headers=[read_frame(io.BytesIO(packet))[0] for packet in packets]
    if repair_succeeds:
        assert headers[-1]['kind']=='end' and headers[-1]['reply_text']=='我挺好的呀，你呢？'
        models.voice.generate.assert_called_once_with('我挺好的呀，你呢？')
        assert models.complete_stream.call_args.kwargs['wire_reply']==raw
    else:
        assert headers[-1]['kind']=='error'
        assert not any(h['kind'] in {'text','audio','end'} for h in headers)
        models.voice.generate.assert_not_called();models.complete_stream.assert_not_called()
