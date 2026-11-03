"""Reply-first serialization must preserve semantics, history and exact text."""
import io
import json
from pathlib import Path
import tempfile
import threading
from tools.dialogue_stream import ReplyDecoder,REPLY_FIRST_FIELDS,stream_body
from tools.voice_channel_source import ClauseBuffer,channel_frames
from common.voice_channel import read_frame
from tests.framework.test_voice_channel import owner


def test_reply_first_preserves_model_context_history_sampling_and_all_fields():
    history=[{'role':'user','content':'我叫小林'},{'role':'assistant','content':'记住啦。'}]
    before=stream_body('same-27b',history,'我叫什么')
    after=stream_body('same-27b',history,'我叫什么',reply_first=True)
    assert after['model']==before['model'] and after['options']==before['options']
    assert after['messages'][1:]==before['messages'][1:]
    assert after['think']==before['think'] is False
    assert after['format']['required']==list(REPLY_FIRST_FIELDS)
    assert after['format']['properties']['b_emotion']==before['format']['properties']['emotion']
    assert after['format']['properties']['c_avatar_action']==before['format']['properties']['avatar_action']


def test_aliases_stream_unicode_text_and_return_canonical_reply():
    expected={'reply_text':'小林，你的预算是240元。🐳','emotion':'friendly','avatar_action':''}
    raw=json.dumps({key:expected[value] for key,value in REPLY_FIRST_FIELDS.items()},ensure_ascii=True)
    for width in (1,2,7,31):
        decoder=ReplyDecoder(field_names=REPLY_FIRST_FIELDS)
        text=''.join(decoder.feed(raw[i:i+width]) for i in range(0,len(raw),width))
        assert text==expected['reply_text'] and decoder.finish()==expected


def test_short_complete_sentence_is_released_but_fillers_and_numeric_fragments_wait():
    buffer=ClauseBuffer(early_sentence=True)
    assert buffer.feed('你好呀！')==['你好呀！']
    assert buffer.feed('我想想。')==[]
    assert buffer.feed('答案是174元。')==['我想想。答案是174元。']
    buffer=ClauseBuffer(early_sentence=True)
    assert buffer.feed('价格是3.14')==[]
    assert buffer.feed('元，运费另算。')==['价格是3.14元，','运费另算。']
    legacy=ClauseBuffer()
    assert legacy.feed('你好呀！')==[]
    assert legacy.finish()==['你好呀！']


def test_optimized_short_answer_enters_tts_before_later_metadata_without_changing_history():
    from tests.framework.test_voice_channel import VoiceChannelTests
    helper=VoiceChannelTests()
    with tempfile.TemporaryDirectory() as directory:
        models=helper.fixture_models(Path(directory));models.latency_options={'reply_first':True,'early_sentence':True}
        calls={}
        tts_started=threading.Event();generate=models.voice.generate
        def synthesize(text):
            tts_started.set();return generate(text)
        models.voice.generate=synthesize
        class Stream:
            metrics={'first_raw_content_ms':1,'first_reply_text_ms':2}
            def __iter__(self):
                yield 'text','你好呀！'
                assert tts_started.wait(2)
                yield 'complete',{'reply_text':'你好呀！','emotion':'friendly','avatar_action':''}
            def cancel(self):pass
        def factory(*args,**kwargs):calls.update(kwargs);return Stream()
        packets=list(channel_frames(models,owner(),'你好',4,model='same-27b',host='fixture',stream_factory=factory))
        headers=[read_frame(io.BytesIO(packet))[0] for packet in packets]
        assert calls=={'reply_first':True} and headers[-1]['kind']=='end'
        assert models.voice.calls==['你好呀！']
        assert headers[-1]['timing']['first_clause_text']=='你好呀！'
        assert headers[-1]['timing']['llm']==Stream.metrics
        assert models.histories=={} and ''.join(row.get('text','') for row in headers if row['kind']=='text')=='你好呀！'


def test_short_chat_coalesces_into_one_tts_call_before_metadata_finishes():
    from tests.framework.test_voice_channel import VoiceChannelTests
    helper=VoiceChannelTests()
    with tempfile.TemporaryDirectory() as directory:
        models=helper.fixture_models(Path(directory))
        models.latency_options={'reply_first':True,'early_sentence':True,'coalesce_chat':True}
        ready=threading.Event();generate=models.voice.generate
        def synthesize(text):ready.set();return generate(text)
        models.voice.generate=synthesize
        text='你好呀！今天过得很开心，你呢？'
        class Stream:
            def __iter__(self):
                yield 'text','你好呀！'
                yield 'text','今天过得很开心，你呢？'
                yield 'speech_ready',None
                assert ready.wait(2)
                yield 'complete',{'reply_text':text,'emotion':'friendly','avatar_action':''}
            def cancel(self):pass
        packets=list(channel_frames(models,owner(),'你好',4,model='same-27b',host='fixture',
                                   stream_factory=lambda *a,**kw:Stream(),feedback=True))
        headers=[read_frame(io.BytesIO(packet))[0] for packet in packets]
        assert headers[-1]['kind']=='end' and headers[-1]['clauses']==1
        assert models.voice.calls==[text] and headers[-1]['reply_text']==text
