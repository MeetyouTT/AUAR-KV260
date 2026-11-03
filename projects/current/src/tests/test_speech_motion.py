import unittest
from common.speech_motion import SpeechMotionPlan, clause_motion


class SpeechMotionTests(unittest.TestCase):
    def test_semantic_materials(self):
        cases = [('好的，我记住了。', 'ack_nod'), ('抱歉，我不能这样做。', 'deny_shake'),
                 ('哇，太棒了！', 'emo_surprised'), ('我没听清，你能再说一遍吗？', 'emo_puzzled')]
        for text, action in cases:
            with self.subTest(text=text):
                self.assertEqual(clause_motion(text)[1], action)

    def test_quoted_hypothetical_and_plain_speech_do_not_gesture(self):
        for text in ('“好的”是一个词。', '如果不能完成就告诉我。', '例如太棒了这样的表达。', '明天可能会下雨。'):
            self.assertEqual(clause_motion(text)[1], '')

    def test_no_random_repeat_or_gesture_on_every_packet(self):
        plan = SpeechMotionPlan()
        self.assertEqual(plan.cue('好的。', 0)['action'], 'ack_nod')
        self.assertEqual(plan.cue('抱歉。', 24000)['action'], '')
        self.assertEqual(plan.cue('好的。', 120000)['action'], '')
        self.assertEqual(plan.cue('抱歉。', 120000)['action'], 'deny_shake')
        self.assertEqual(plan.cue('哇！', 240000)['action'], '')

    def test_explicit_action_and_emotion_take_precedence(self):
        self.assertEqual(SpeechMotionPlan().cue('普通回复。', 0, emotion='happy', action='ack_nod'),
                         dict(emotion='happy', action='ack_nod', at_sample=0))
        self.assertEqual(SpeechMotionPlan().cue('普通回复。', 0, action='shell')['action'], '')

    def test_new_turn_has_independent_budget(self):
        for _ in range(2):
            self.assertEqual(SpeechMotionPlan().cue('好的。', 0)['action'], 'ack_nod')


if __name__ == '__main__':
    unittest.main()
