"""Board persona/config/contract checks with public handwritten fixtures only."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
AURA = ROOT.parents[2] / 'aura'
sys.path[:0] = [str(ROOT), str(AURA)]
from board_persona_candidate import (BASELINE_BYTES, BASELINE_SHA256,
    PersonaCandidateRejected, load_candidate, require_active_pair)
from tools.dialogue_host_ollama import fast_system_prompt
from common.device_policy import MODEL_HINT
from common.spoken_input import SPEECH_INPUT_HINT, prepare_spoken_input
from board.runtime.board_memory_policy import BoardContextBuilder, BoardMemoryCommands, message_cost
from board.runtime.board_dialogue import ReplyRejected, validate_model_reply, split_sentences


CONFIG = ROOT / 'persona.xuefei.candidate.json'
VERSION = 'xuefei-yuki-board-v1-candidate'


def accepted():
    return fast_system_prompt() + MODEL_HINT


def load(path=CONFIG, *, version=VERSION, baseline=None):
    return load_candidate(path, expected_config_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          expected_profile_version=version,
                          accepted_system_prompt=accepted() if baseline is None else baseline)


class CandidateChecks(unittest.TestCase):
    def changed_config(self, transform):
        value = json.loads(CONFIG.read_text(encoding='utf-8'))
        transform(value)
        with tempfile.TemporaryDirectory(prefix='aura-persona-public-') as temporary:
            path = Path(temporary) / 'candidate.json'
            path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            return load(path)

    def test_current_accepted_loader_and_full_safeguard_bytes_remain_exact(self):
        old, candidate = accepted(), load()
        self.assertEqual(len(old.encode('utf-8')), BASELINE_BYTES)
        self.assertEqual(hashlib.sha256(old.encode('utf-8')).hexdigest(), BASELINE_SHA256)
        self.assertEqual(candidate.system_prompt.count(SPEECH_INPUT_HINT), 1)
        self.assertTrue(candidate.system_prompt.endswith(MODEL_HINT))
        self.assertLessEqual(len(candidate.system_prompt.encode('utf-8')), len(old.encode('utf-8')))
        self.assertIn('雪妃', candidate.system_prompt)
        self.assertNotIn('汐蓝', candidate.system_prompt)

    def test_changed_baseline_or_config_fingerprint_fails_closed(self):
        with self.assertRaises(PersonaCandidateRejected):
            load(baseline=accepted() + ' changed')
        with self.assertRaises(PersonaCandidateRejected):
            load_candidate(CONFIG, expected_config_sha256='0' * 64,
                           expected_profile_version=VERSION, accepted_system_prompt=accepted())

    def test_more_prompt_text_cannot_consume_additional_context(self):
        with self.assertRaisesRegex(PersonaCandidateRejected, 'UTF8 prompt budget'):
            self.changed_config(lambda v: v.update(prompt_prefix=v['prompt_prefix'] + '额外背景。' * 60))

    def test_bundle_version_change_requires_joint_review(self):
        with self.assertRaises(PersonaCandidateRejected):
            load(version='other-profile-v1')

    def test_emotion_action_and_length_contract_changes_rejected(self):
        for key, value in [('emotions', ['neutral', 'friendly', 'happy', 'sad', 'shy']),
                           ('avatar_actions', ['', 'ack_nod']),
                           ('prompt_target_max_characters', 80),
                           ('existing_validator_max_characters', 48),
                           ('existing_validator_min_characters', True)]:
            with self.subTest(key=key), self.assertRaises(PersonaCandidateRejected):
                self.changed_config(lambda v: v['reply_contract'].update({key: value}))

    def test_ready_image_and_persona_must_have_identical_profile_version_and_pin(self):
        candidate = load()
        actual = dict(profile_version=VERSION, render_profile_id=candidate.render_profile_id,
                      render_source_profile_sha256=candidate.render_source_profile_sha256,
                      render_ready=True)
        self.assertEqual(require_active_pair(candidate, **actual), candidate.system_prompt)
        for change in ({'profile_version': 'old-profile'}, {'render_profile_id': 'old-character'},
                       {'render_source_profile_sha256': '0' * 64}, {'render_ready': False},
                       {'render_ready': 1}):
            with self.subTest(change=change), self.assertRaises(PersonaCandidateRejected):
                require_active_pair(candidate, **dict(actual, **change))

    def test_existing_2048_budget_and_summary_residual_are_preserved_or_improved(self):
        candidate = load()
        old, new = BoardContextBuilder(accepted()), BoardContextBuilder(candidate.system_prompt)
        self.assertEqual((new.maximum, new.reserve), (2048, 120))
        self.assertGreaterEqual(new.continuity_capacity(), old.continuity_capacity())
        text = '请接着说。'
        current = dict(role='user', content=text)
        messages = new(dict(messages=[dict(role='user', content='上一轮。'),
                                      dict(role='assistant', content='我们先核对数据。')],
                            facts=[], summaries=[]), text)
        self.assertEqual(messages[-1], current)
        self.assertEqual(new.metrics['recent_messages'], 2)
        self.assertLessEqual(message_cost(messages, 120), 2048)

    def test_history_empty_and_cross_boundary_limits_stay_visible(self):
        builder = BoardContextBuilder(load().system_prompt)
        messages = builder(dict(messages=[], facts=[], summaries=[]), '昨天做了什么？',
                           dict(items=[], status=dict(boundary_incomplete=True, result_limited=True)))
        text = ''.join(row['content'] for row in messages)
        self.assertIn('未返回资料不代表事情没有发生', text)
        self.assertIn('有摘要跨越查询时间边界', text)
        self.assertIn('结果达到条数上限', text)
        self.assertEqual(builder.metrics['history_items'], 0)
        self.assertLessEqual(message_cost(messages, 120), 2048)

    def test_persona_cannot_enable_personal_memory_or_rewrite_literal_user_name(self):
        class ForbiddenStore:
            def context(self, *args, **kwargs):
                raise AssertionError('Unauthorized private lookup must not happen')
        reply = BoardMemoryCommands(ForbiddenStore())('查看我的长期记忆', {'kind': 'conversation'},
                    turn_id='public-persona-fixture', generation=1, user_event_id=1)
        self.assertIn('授权个人档案', reply.text)
        text = '我叫西兰，名字不要改。'
        self.assertEqual(prepare_spoken_input(text)['text'], text)


class ExistingReplyContractChecks(unittest.TestCase):
    def test_handwritten_samples_satisfy_real_board_validator_and_prompt_target(self):
        data = json.loads((ROOT / 'reply_samples.json').read_text(encoding='utf-8'))
        self.assertEqual(data['profile_version'], VERSION)
        for row in data['samples']:
            with self.subTest(user=row['user']):
                reply = validate_model_reply(json.dumps(row['reply'], ensure_ascii=False), row['user'])
                self.assertLessEqual(len(reply.text), 48)
                self.assertEqual(reply.avatar_action, '')
                self.assertTrue(all(len(chunk) <= 220 for chunk in split_sentences(reply.text)))

    def test_real_validator_rejects_extra_keys_unapproved_actions_emotions_and_empty_text(self):
        base = dict(reply_text='我们先核对资料。', emotion='friendly', avatar_action='')
        variants = [dict(base, grant=True), dict(base, emotion='shy'),
                    dict(base, avatar_action='ack_nod'), dict(base, reply_text=''),
                    dict(base, reply_text='<think>内容'), dict(base, reply_text='第一行\n第二行')]
        for row in variants:
            with self.subTest(row=row), self.assertRaises(ReplyRejected):
                validate_model_reply(json.dumps(row, ensure_ascii=False), '')

    def test_existing_hard_500_limit_is_distinct_from_48_character_style_target(self):
        for size, allowed in ((1, True), (48, True), (49, True), (500, True), (501, False)):
            raw = json.dumps(dict(reply_text='字' * size, emotion='neutral', avatar_action=''))
            with self.subTest(size=size):
                if allowed:
                    self.assertEqual(len(validate_model_reply(raw, '').text), size)
                else:
                    with self.assertRaises(ReplyRejected):
                        validate_model_reply(raw, '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
