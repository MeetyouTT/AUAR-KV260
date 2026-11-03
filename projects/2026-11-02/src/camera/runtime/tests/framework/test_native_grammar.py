"""Same reply contract on native SSE; identity failures fall back before output."""
import io,json,threading,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
import pytest
from tools import native_grammar as native
from tools.dialogue_stream import OllamaReplyStream,stream_body


def response_for(raw,native_sse=False):
    packet={'content':raw,'stop':True,'timings':{'cache_n':150,'prompt_n':16,'prompt_ms':200.,'predicted_n':24,'predicted_ms':2100.}} if native_sse else {'message':{'content':raw},'done':True}
    response=io.BytesIO((('\n' if native_sse else '')+('data: ' if native_sse else '')+json.dumps(packet)+'\n\n').encode())
    response.status=200;connection=MagicMock();connection.getresponse.return_value=response
    return connection


def test_native_sse_keeps_exact_text_metadata_and_json_history():
    text='你好呀，“小林”！🐳'
    raw=json.dumps({'a':text,'b':'happy','c':''},ensure_ascii=False,separators=(',',':'))
    connection=response_for(raw,True)
    with patch('tools.native_grammar.prepare',return_value=('http://127.0.0.1:45678',{'prompt':'verified','grammar':native.GRAMMAR},{'backend':'llama_native_compact'})),patch('tools.dialogue_stream.http.client.HTTPConnection',return_value=connection):
        stream=OllamaReplyStream('http://127.0.0.1:11435','same-27b',[],'你好',4,reply_first=True,compact_grammar=True)
        events=list(stream)
    assert ''.join(value for kind,value in events if kind=='text')==text
    assert events[-1][1]=={'reply_text':text,'emotion':'happy','avatar_action':''}
    assert stream.raw_reply==raw and stream.metrics['backend']=='llama_native_compact'
    assert stream.metrics['prompt_eval_count']==166 and stream.metrics['eval_count']==24
    assert stream.metrics['eval_duration_ms']==2100.
    assert connection.request.call_args.args[1]=='/completion'
    assert connection.request.call_count==1 and stream.metrics['quality_retry_count']==0


def test_unavailable_native_runner_uses_unchanged_original_request_before_output():
    history=[{'role':'user','content':'我喜欢绿色'},{'role':'assistant','content':'记住啦。'}]
    raw=json.dumps({'a':'你喜欢绿色呀。','b':'friendly','c':''})
    connection=response_for(raw)
    with patch('tools.native_grammar.prepare',side_effect=ValueError('Unverified model')),patch('tools.dialogue_stream.http.client.HTTPConnection',return_value=connection):
        stream=OllamaReplyStream('http://127.0.0.1:11435','same-27b',history,'我喜欢什么颜色',4,reply_first=True,compact_grammar=True)
        list(stream)
    assert connection.request.call_args.args[1]=='/api/chat'
    assert json.loads(connection.request.call_args.args[2])==stream_body('same-27b',history,'我喜欢什么颜色',reply_first=True)
    assert stream.metrics['backend']=='ollama' and 'Unverified model' in stream.metrics['compact_grammar_fallback']
    assert connection.request.call_count==1


def test_native_preparation_cancellation_never_starts_inference():
    with patch('tools.native_grammar.prepare',side_effect=InterruptedError('Cancelled')),patch('tools.dialogue_stream.http.client.HTTPConnection') as connect:
        stream=OllamaReplyStream('http://127.0.0.1:11435','same-27b',[],'你好',4,reply_first=True,compact_grammar=True)
        with pytest.raises(InterruptedError):list(stream)
    connect.assert_not_called()


def test_reasoning_retains_original_route_and_generation_budget():
    connection=response_for(json.dumps({'a':'结果是174。','b':'neutral','c':''}))
    with patch('tools.native_grammar.prepare') as prepare,patch('tools.dialogue_stream.http.client.HTTPConnection',return_value=connection):
        stream=OllamaReplyStream('http://127.0.0.1:11435','same-27b',[],'仔细算',4,think=True,num_predict=768,reply_first=True,compact_grammar=True)
        list(stream)
    prepare.assert_not_called()
    body=json.loads(connection.request.call_args.args[2])
    assert body['think'] and body['options']['num_predict']==768
    assert connection.request.call_args.args[1]=='/api/chat'


@pytest.mark.parametrize('field,value',[('model_path','other-model.gguf'),('build_info','unverified-build'),('total_slots',2),('chat_template','other-template'),('default_generation_settings',{'n_ctx':4096})])
def test_wrong_native_identity_context_or_build_is_rejected(field,value,tmp_path):
    expected=(tmp_path/'sha256-fixture').resolve()
    props={'model_path':str(expected),'build_info':native.VERIFIED_BUILD,'total_slots':1,
           'chat_template':'same','default_generation_settings':{'n_ctx':2048}}
    props[field]=value
    with patch.object(native,'_json',return_value=props):
        with pytest.raises(ValueError):native._validate({'base':'http://127.0.0.1:45678','model_path':str(expected)},{'template':'same'},expected,time.monotonic()+3,threading.Event())


def test_discovery_accepts_only_one_project_owned_runner():
    rows=[{'ProcessId':123,'ExecutablePath':'llama-server.exe','CommandLine':'llama-server.exe --model "D:\\AIModels\\Ollama-AURA\\blobs\\sha256-test" --port 45678 --host 127.0.0.1'}]
    with patch.object(native.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(rows))):
        endpoint=native._discover(time.monotonic()+3)
    assert endpoint['base']=='http://127.0.0.1:45678' and endpoint['pid']==123
    with patch.object(native.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(rows*2))):
        with pytest.raises(ValueError):native._discover(time.monotonic()+3)


def test_native_request_keeps_human_prompt_history_and_sampling(tmp_path):
    body=stream_body('same-27b',[{'role':'user','content':'我喜欢绿色'}],'我喜欢什么颜色',reply_first=True)
    model=tmp_path/'blobs'/'sha256-test';template='same'
    expected_prompt='preserved user/history\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
    replies=[{'done':True,'response':''},{'modelfile':'FROM '+str(model),'template':template},
             {'model_path':str(model),'build_info':native.VERIFIED_BUILD,'total_slots':1,'default_generation_settings':{'n_ctx':2048},'chat_template':template},
             {'prompt':expected_prompt}]
    endpoint={'base':'http://127.0.0.1:45678','model_path':str(model),'pid':123}
    storage=json.dumps({'ollama_directory':str(tmp_path)})
    with patch.object(native,'_cache',{}),patch.object(native,'_discover',return_value=endpoint),patch.object(native,'_json',side_effect=replies) as calls,patch.object(Path,'read_text',return_value=storage):
        base,request,metrics=native.prepare('http://127.0.0.1:11435',body,4,threading.Event())
    assert base==endpoint['base'] and request['prompt']==expected_prompt
    assert request['temperature']==body['options']['temperature'] and request['n_predict']==120
    assert request['grammar']==native.GRAMMAR and request['min_p']==0.
    assert calls.call_args_list[-1].args[2]['messages']==body['messages']
    assert metrics['backend']=='llama_native_compact'


def test_native_timing_normalization_preserves_error_and_limit():
    assert native.normalize_packet({'error':'failure'})['error']=='failure'
    packet=native.normalize_packet({'content':'','stop':True,'stopped_limit':True,'timings':{'cache_n':10,'prompt_n':3,'prompt_ms':1.5,'predicted_n':24,'predicted_ms':10.25}})
    assert packet['prompt_eval_count']==13 and packet['eval_count']==24
    assert packet['total_duration']==11_750_000 and packet['done_reason']=='length'
