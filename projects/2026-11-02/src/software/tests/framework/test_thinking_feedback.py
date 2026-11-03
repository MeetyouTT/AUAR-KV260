"""Routing, one-shot feedback and playback-confirmed history boundaries."""
import hashlib
import io
import threading
import time
import unittest

from common.thinking_policy import route,FeedbackGate
from common.voice_channel import read_frame
from tools.board_model_host import ModelHost
from tools.voice_channel_source import channel_frames
from tests.framework.test_voice_channel import owner


class ThinkingTests(unittest.TestCase):
    def test_math_and_explicit_reasoning_route_without_extra_model(self):
        self.assertEqual(route('240元先八折减30元加12元运费，实付多少？')['mode'],'reasoning')
        self.assertEqual(route('仔细想想，比较这两个方案')['mode'],'reasoning')
        for text in ('你好','我想你了','我今天有点累，陪我聊聊','我叫什么名字'):
            self.assertEqual(route(text)['mode'],'chat')

    def test_feedback_is_once_and_cancelled_if_answer_or_cancel_arrives_first(self):
        gate=FeedbackGate({'feedback_after_ms':1500})
        self.assertFalse(gate.due(1499));self.assertTrue(gate.due(1500));self.assertFalse(gate.due(9000))
        for method in ('ready','cancel'):
            gate=FeedbackGate({'feedback_after_ms':0});getattr(gate,method)();self.assertFalse(gate.due(9999))

    def test_comparative_adverbs_and_topic_nouns_remain_casual(self):
        for text in ('今天比较开心', '我比较喜欢蓝色', '你比较喜欢蓝色还是红色',
                     '今天比较累，陪我聊聊', '这个对比鲜明，让我很开心', '我今天比较忙',
                     '我想选个比较好的方案', '我看了一个对比视频', '我们比较了两个方案',
                     '我喜欢推理小说', '我的计算机今天开不了机', '我认真想你了',
                     '我逐步开心起来了', '不用仔细想，陪我聊聊', '不用比较两个方案，我们先聊天'):
            with self.subTest(text=text):
                plan=route(text)
                self.assertEqual(plan['mode'],'chat')
                self.assertFalse(FeedbackGate(plan).due(120000))

    def test_actual_comparison_and_deliberation_requests_still_think(self):
        for text in ('比较这两个方案', '请比较咖啡和茶', '对比小米和华为',
                     '给我做个比较', 'A与B对比有什么区别', '汐蓝请帮我对比这两个模型',
                     '仔细想想这个问题', '请认真思考', '逐步解释这个证明',
                     '不用比较两个方案，计算240减30加12', '不用仔细想，比较这两个方案'):
            with self.subTest(text=text):
                plan=route(text)
                self.assertEqual(plan['mode'],'reasoning')
                self.assertTrue(FeedbackGate(plan).due(0))

    def test_casual_chat_never_inserts_cached_thinking_phrase_even_when_slow(self):
        for text in ('你好汐蓝今天过得怎么样','我今天有点累陪我聊聊','说一个笑话','我叫什么名字'):
            plan=route(text);self.assertEqual(plan['mode'],'chat')
            self.assertFalse(FeedbackGate(plan).due(120000))
        plan=route('计算240打八折减30加12运费')
        self.assertEqual(plan['mode'],'reasoning');self.assertTrue(FeedbackGate(plan).due(0))

    def test_complex_channel_emits_one_hint_and_requests_native_thinking(self):
        import tempfile
        from pathlib import Path
        from tests.framework.test_voice_channel import VoiceChannelTests
        helper=VoiceChannelTests()
        with tempfile.TemporaryDirectory() as directory:
            models=helper.fixture_models(Path(directory));received={}
            def factory(*args,**kwargs):received.update(kwargs);return helper.fake_stream(*args)
            packets=list(channel_frames(models,owner(),'计算240减30再加12',4,model='fixture',host='fixture',feedback=True,stream_factory=factory))
            kinds=[read_frame(io.BytesIO(p))[0]['kind'] for p in packets]
            self.assertEqual(kinds.count('thinking'),1)
            self.assertLess(kinds.index('thinking'),kinds.index('audio'))
            self.assertEqual(received,{'think':True,'num_predict':768})
            self.assertEqual(kinds[-1],'end')

    def test_history_commits_only_after_matching_full_playback_ack(self):
        models=ModelHost.__new__(ModelHost)
        models.meta_lock=threading.Lock();models.pending_streams={};models.latest_generations={};models.histories={}
        meta=owner();models.register_stream(meta)
        digest=hashlib.sha256(b'example').hexdigest()
        models.complete_stream(meta,'我叫小林','我记住了。',480,digest)
        self.assertEqual(models.histories,{})
        ack={'context':meta,'voice_sample_count':480,'pcm_sha256':digest}
        with self.assertRaises(ValueError):models.acknowledge_stream(dict(ack,voice_sample_count=479))
        self.assertTrue(models.acknowledge_stream(ack)['committed'])
        self.assertEqual(models.histories[(meta['board_boot_id'],meta['session_id'])][-1]['content'],'我记住了。')
        with self.assertRaises(ValueError):models.acknowledge_stream(ack)

    def test_cancelled_generation_cannot_commit_old_stream(self):
        models=ModelHost.__new__(ModelHost)
        models.meta_lock=threading.Lock();models.pending_streams={};models.latest_generations={};models.histories={}
        meta=owner();models.register_stream(meta);models.complete_stream(meta,'问题','回答',1,'a'*64)
        models.register_stream(owner('new-turn',2))
        with self.assertRaises(ValueError):models.acknowledge_stream({'context':meta,'voice_sample_count':1,'pcm_sha256':'a'*64})
        self.assertEqual(models.histories,{})
