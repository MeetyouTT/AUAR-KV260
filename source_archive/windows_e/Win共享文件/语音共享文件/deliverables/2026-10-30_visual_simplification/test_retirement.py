import hashlib,http.client,importlib.util,io,json,threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
from http.server import ThreadingHTTPServer

from common.visual_policy import RETIRED_VISUAL_REPLY
from tools.device_hub import Handler as HubHandler
from tools.memory_timeline_host import live_context
from common.device_memory import ObservationStore

def test_retired_image_endpoint_never_reads_or_decodes_the_image():
    handler=HubHandler.__new__(HubHandler)
    handler.path='/v1/observations';handler.allowed=lambda:True
    handler.rfile=MagicMock();handler.reply=MagicMock()
    handler.rfile.read.side_effect=AssertionError('Retired endpoint read an image')
    HubHandler.do_POST(handler)
    assert handler.reply.call_args.args[0]==410
    handler.rfile.read.assert_not_called()
    assert handler.close_connection

def test_legacy_archive_survives_but_cannot_be_injected_as_current_sight(tmp_path):
    now=[100.]
    store=ObservationStore(tmp_path/'observations.db',clock=lambda:now[0])
    try:
        frame={'board_boot_id':'fixture','camera_epoch':'camera','frame_id':1}
        store.add(frame,'历史模型描述',100.)
        before=store.db.execute('SELECT * FROM observations').fetchall()
        with patch('tools.device_client.call',side_effect=AssertionError('Live recall must be retired')):
            assert live_context(object(),{'board_boot_id':'fixture'},'你好') is None
        assert store.recall('fixture',history=True)
        assert before==store.db.execute('SELECT * FROM observations').fetchall()
    finally:store.close()

def test_board_observer_cannot_restart_image_upload_or_a_background_worker():
    path=Path(__file__).parent/'board/device_observer.py'
    spec=importlib.util.spec_from_file_location('retired_board_observer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with patch('threading.Thread',side_effect=AssertionError('Uploader started a worker')):
        observer=module.DeviceObserver('fixture')
        observer.enabled=True;observer.run()
        state=observer.public();observer.close()
    assert state['enabled'] is False and state['image_upload_enabled'] is False
    assert state['sent']==0 and state['structured_visual_timeline_deployed'] is False

def test_spoken_visual_question_returns_explicit_boundary_without_llm_or_camera(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_long_conversation import host
    from tests.framework import test_voice_channel as wire
    from tools.voice_channel_source import channel_frames
    model=host(tmp_path);model.lock=threading.Lock();model.latency_options={}
    model.voice=wire.VoiceChannelTests().fixture_models(tmp_path).voice
    class Engine:
        model_id='TEST_ONLY'
        def transcribe(self,pcm):return '这是什么东西'
    server=AsrServer(('127.0.0.1',0),Engine(),handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    ch=VoiceChannel('127.0.0.1',server.server_port,visual_question=True);events=[]
    def forbidden(*a,**kw):raise AssertionError('Removed VLM route called the LLM')
    def source(*a,**kw):return channel_frames(*a,**kw,stream_factory=forbidden)
    pcm=b'\xe8\x03'*3200
    m=dict(wire.owner(),sample_count=len(pcm)//2,pcm_sha256=hashlib.sha256(pcm).hexdigest())
    try:
        with (patch('tools.device_client.call',side_effect=OSError('Synthetic test has no production Hub')),
              patch('tools.voice_channel_source.channel_frames',source)):
            result=ch.exchange(m,pcm,lambda h,p:events.append(h))
        assert result['network_complete']
        assert not any(event.get('visual_request') for event in events)
        assert events[-1]['reply_text']==RETIRED_VISUAL_REPLY
    finally:ch.close();server.shutdown();server.server_close();thread.join(2)

def test_frame_upload_route_returns_gone_before_parsing_payload():
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    engine=SimpleNamespace(model_id='TEST_ONLY')
    server=AsrServer(('127.0.0.1',0),engine,handler=ModelHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
    try:
        c.request('POST','/v1/voice/visual/frame',b'invalid image body')
        response=c.getresponse();value=json.loads(response.read())
        assert response.status==410 and value['image_upload_enabled'] is False
    finally:c.close();server.shutdown();server.server_close();thread.join(2)
