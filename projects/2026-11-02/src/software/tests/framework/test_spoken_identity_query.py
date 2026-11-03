"""Fresh camera identity queries, no enrollment/history writes, real HTTP routing."""
import copy,io,tempfile,threading,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from common import voice_enrollment as speech
from board.identity.spoken_query import answer_current_face
from board.identity.voice_enrollment import VoiceEnrollment


def snapshot():
    from tests.framework.test_simple_enrollment import snapshot as base
    value=base();key=copy.deepcopy(value['modules']['target']['selected'])
    value['modules']['identity'].update(state='KNOWN',person_id='person-one',display_name='小林',db_version=1,
        target_kind='face',face_count=1,face_target=key,face_targets=[{'key':key,'label':'face'}],target=key,
        source_frame_id=10,source_mono_ms=950,
        face_preview={'target':key,'frame_id':10,'captured_mono_ms':950,'ttl_ms':3000},
        people=[{'person_id':'person-one','display_name':'小林'}])
    return value


class SpokenIdentityQueryTests(unittest.TestCase):
    def setUp(self):
        self.current=snapshot();self.start=copy.deepcopy(self.current)

    def answer(self):return answer_current_face(self.current,self.start,'boot',1000)

    def test_named_answer_is_scoped_to_observed_face_not_authenticated_speaker(self):
        self.assertEqual(self.answer(),speech.result('identity_seen','小林'))
        self.assertIn('镜头前',speech.render(self.answer()))
        self.assertNotIn('你是',speech.render(self.answer()))

    def test_unknown_result_never_uses_gallery_or_last_enrollment_name(self):
        self.current['modules']['identity'].update(state='UNKNOWN',person_id='',display_name='',
            last_operation={'action':'identity_enroll','state':'COMMITTED','detail':'已登记小林'})
        self.assertEqual(self.answer(),speech.result('identity_unknown'))

    def test_target_loss_many_faces_and_camera_epoch_change_never_name_person(self):
        for mutation in (lambda i:i.update(face_count=2),lambda i:i.update(face_count=0,face_target=None),
                         lambda i:i['face_target'].update(track_generation=9),
                         lambda i:i['face_target'].update(camera_epoch='different')):
            self.setUp();mutation(self.current['modules']['identity'])
            self.assertNotEqual(self.answer()['code'],'identity_seen')

    def test_stale_wrong_owner_future_or_missing_source_is_refused(self):
        for change in ({'source_mono_ms':-2000},{'source_mono_ms':1001},{'source_mono_ms':None},
                       {'source_frame_id':True},{'source_frame_id':0},{'target':None}):
            self.setUp();self.current['modules']['identity'].update(change)
            self.assertEqual(self.answer()['code'],'identity_unavailable')

    def test_shorter_preview_expiry_also_limits_named_answer(self):
        self.current['modules']['identity'].update(source_mono_ms=500)
        self.current['modules']['identity']['face_preview'].update(captured_mono_ms=500,ttl_ms=100)
        self.assertEqual(self.answer()['code'],'identity_unavailable')

    def test_service_revision_person_or_registry_change_is_refused(self):
        mutations=(lambda v:v.update(service_epoch='new-service'),
          lambda v:v['modules']['identity'].update(db_version=2),
          lambda v:v['modules']['identity'].update(person_id='other-person'),
          lambda v:v['modules']['identity'].update(people=[]),
          lambda v:v['modules']['identity'].update(display_name='小明'),
          lambda v:v['modules']['camera'].update(state='ERROR'))
        for mutation in mutations:
            self.setUp();mutation(self.current);self.assertNotEqual(self.answer()['code'],'identity_seen')

    def test_fixture_or_absent_capture_snapshot_cannot_answer_name(self):
        self.start=None;self.assertEqual(self.answer()['code'],'identity_unavailable')
        self.setUp();self.start['source_kind']='fixture';self.assertEqual(self.answer()['code'],'identity_unavailable')

    def test_unknown_at_capture_then_current_match_can_answer_only_same_face(self):
        self.start['modules']['identity'].update(state='UNKNOWN',person_id='',display_name='')
        self.assertEqual(self.answer()['code'],'identity_seen')

    def test_read_only_query_does_not_authorize_or_cancel_registration(self):
        command=Mock(side_effect=AssertionError('Query must never issue database commands'))
        flow=VoiceEnrollment('boot',lambda:copy.deepcopy(self.current),command,now_ms=lambda:1000,simple=True)
        self.assertEqual(flow.handle('我是谁',self.start),speech.result('identity_seen','小林'))
        self.assertEqual(flow.public(),{'stage':'idle','active':False});command.assert_not_called()
        flow.stage='authorize';epoch=flow.epoch
        self.assertEqual(flow.handle('我是谁',self.start),speech.result('identity_busy'))
        self.assertEqual(flow.epoch,epoch);self.assertEqual(flow.stage,'authorize');command.assert_not_called()

    def test_cancelled_or_network_failed_query_has_no_stale_name_fallback(self):
        flow=VoiceEnrollment('boot',lambda:copy.deepcopy(self.current),Mock(),now_ms=lambda:1000,simple=True)
        with self.assertRaises(InterruptedError):flow.handle('我是谁',self.start,is_current=lambda:False)
        flow.snapshot=Mock(side_effect=OSError('camera unavailable'))
        self.assertEqual(flow.handle('我是谁',self.start),speech.result('identity_unavailable'))

    def test_direct_intents_only_not_quotations_negations_or_assistant_identity(self):
        for text in ('我是谁','汐蓝，你知道我是谁吗？','你还认得我吗','我叫什么名字'):
            self.assertTrue(speech.identity_query_requested(text),text)
        for text in ('你是谁','不要回答我是谁','他说我是谁','“我是谁”','如果我问我是谁','我是谁然后删除身份','我叫小林'):
            self.assertFalse(speech.identity_query_requested(text),text)

    def test_known_vocatives_need_no_comma_and_questions_allow_natural_particles(self):
        for name in ('汐蓝',)+speech.ALIASES:
            for question in ('我是谁','我是谁呀','我叫什么名字啊','你知道我是谁',
                             '你还认识我吗','能认出我了吗','你知道我的名字吗'):
                for raw in (name+question,name+'，'+question+'？','你好'+name+question):
                    self.assertTrue(speech.identity_query_requested(raw),raw)

    def test_expanded_query_grammar_never_rewrites_personal_names_or_raw_speech(self):
        from common.spoken_input import prepare_spoken_input
        for raw in ('西兰花我是谁','西来我是谁','我朋友叫夕蓝','夕蓝说我是谁','夕蓝我叫小林',
                    '夕蓝别回答我是谁','夕蓝如果我问我是谁','夕蓝你是谁','夕蓝“我是谁”',
                    '夕蓝我是谁然后删除身份','夕蓝我叫什么名字你不要回答',None,{},'我是谁'*30):
            self.assertFalse(speech.identity_query_requested(raw),raw)
        raw='夕蓝我叫什么名字啊'
        self.assertEqual(prepare_spoken_input(raw)['raw_text'],raw)
        self.assertTrue(speech.identity_query_requested(raw))
        self.assertIsNone(speech.spoken_name(raw))

    def test_routing_diagnostic_survives_subtitle_clear_without_retaining_private_text(self):
        from board.runtime.audio.channel_jobs import ChannelConversationJobs
        jobs=object.__new__(ChannelConversationJobs)
        jobs.condition=threading.Condition();jobs.closed=False;jobs.generation=3
        jobs.capture_owners={'capture':self.start};jobs.last_voice_route=None
        meta={'generation':3,'capture_id':'capture'}
        jobs._record_voice_route(meta,{'text':'夕蓝我是谁呀','identity_request':'token'},'identity_seen')
        diagnostic=jobs.last_voice_route
        self.assertTrue(diagnostic['direct_identity_question'])
        self.assertTrue(diagnostic['board_identity_route'])
        self.assertEqual(diagnostic['reply_code'],'identity_seen')
        self.assertNotIn('小林',str(diagnostic));self.assertNotIn('夕蓝',str(diagnostic))
        jobs._record_voice_route(dict(meta,generation=2),{'text':'我叫小林'})
        self.assertEqual(jobs.last_voice_route,diagnostic)
        jobs._record_voice_route(meta,{'text':'我叫小林'})
        self.assertFalse(jobs.last_voice_route['direct_identity_question'])
        self.assertNotIn('小林',str(jobs.last_voice_route))


class SpokenIdentityQueryHTTPTests(unittest.TestCase):
    def test_query_requires_client_capability_and_plain_chat_keeps_original_route(self):
        from tools.voice_channel_source import serve_channel
        from tests.framework.test_voice_channel import owner
        for enabled,text,expected in ((False,'我是谁',False),(True,'我是谁',True),(True,'你是谁',False),
                                     (True,'夕蓝我是谁呀',True),(True,'西兰我叫什么名字啊',True),
                                     (True,'夕蓝你是谁',False),(True,'夕蓝不要回答我是谁',False)):
            headers={'X-Aura-Identity':'enrollment-v1'}
            if enabled:headers['X-Aura-Identity-Query']='current-face-v1'
            models=SimpleNamespace(open_identity_exchange=Mock(return_value=SimpleNamespace(cancel=Mock())))
            handler=SimpleNamespace(headers=headers,connection=Mock(),send_response=Mock(),send_header=Mock(),
                end_headers=Mock(),wfile=io.BytesIO(),server=SimpleNamespace(models=models))
            with patch('tools.voice_channel_source.channel_frames',side_effect=lambda *a,**kw:(v for v in ())) as frames:
                serve_channel(handler,owner(),text,5)
            self.assertEqual(models.open_identity_exchange.called,expected)
            self.assertEqual(frames.call_args.kwargs['identity_exchange'] is not None,expected)

    def test_actual_http_asr_board_query_original_voice_and_no_chat_history(self):
        from tools.asr_server import AsrServer
        from tools.board_model_host import ModelHandler
        from board.runtime.audio.voice_channel import VoiceChannel
        from tests.framework.test_history_reuse import host
        from tests.framework.test_voice_channel import owner,PCM,VoiceChannelTests
        with tempfile.TemporaryDirectory() as directory:
            models=host();models.voice=VoiceChannelTests().fixture_models(__import__('pathlib').Path(directory)).voice
            models.lock=threading.Lock();models.latency_options={'reply_first':True,'coalesce_chat':True,'reuse_history':True}
            class Engine:
                model_id='TEST_ONLY';calls=0
                def transcribe(self,pcm):self.calls+=1;return '我是谁'
            engine=Engine();server=AsrServer(('127.0.0.1',0),engine,handler=ModelHandler);server.models=models
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            channel=VoiceChannel('127.0.0.1',server.server_port,identity_query=True)
            current=snapshot();flow=VoiceEnrollment('boot',lambda:copy.deepcopy(current),
                Mock(side_effect=AssertionError('no writes')),now_ms=lambda:1000,simple=True)
            observed=[]
            try:
                for index,expected in enumerate(('identity_seen','identity_unknown'),1):
                    if index==2:current['modules']['identity'].update(state='UNKNOWN',person_id='',display_name='')
                    start=copy.deepcopy(current);meta=owner('query-'+str(index),index);end={}
                    def receive(header,pcm):
                        if header['kind']=='transcript':
                            reply=flow.handle(header['text'],start);observed.append(reply['code'])
                            channel.identity_result(meta,header['identity_request'],reply)
                        if header['kind']=='end':end.update(header)
                    reply=channel.exchange(meta,PCM,receive,enrollment_state=False)
                    self.assertEqual(observed[-1],expected)
                    self.assertEqual(end['timing']['llm']['backend'],'board_identity_workflow')
                    self.assertEqual(reply['reply_text'],speech.render(speech.result(expected,'小林' if index==1 else '')))
                    models.acknowledge_stream({'context':meta,'voice_sample_count':end['sample_count'],'pcm_sha256':end['pcm_sha256']})
                self.assertEqual(engine.calls,2);self.assertEqual(models.histories,{})
                self.assertEqual(models.wire_histories,{});self.assertEqual(models.pending_streams,{})
            finally:channel.close();server.shutdown();server.server_close();worker.join(2)


if __name__=='__main__':unittest.main()
