import copy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from name_semantics import assess_name
from direct_logic import abba,model_messages,QUESTION


def validate(raw,question):
    value=json.loads(raw)
    if set(value)!={'reply_text','emotion','avatar_action'} or not value['reply_text']:
        raise ValueError('invalid_complete_reply')
    if value['emotion'] not in {'neutral','friendly','happy','sad'} or value['avatar_action']!='':
        raise ValueError('invalid_metadata')
    return types.SimpleNamespace(text=value['reply_text'])


def decode(raw,arm):
    value=json.loads(raw)
    if arm=='B':
        if set(value)!={'a','b','c'}: raise ValueError('wrong_compact_contract')
        value={'reply_text':value['a'],'emotion':value['b'],'avatar_action':value['c']}
    return json.dumps(value,ensure_ascii=False)


class NameTests(unittest.TestCase):
    def test_normal_names_are_accepted_without_exact_phrase_whitelist(self):
        for text in ('我叫雪妃。','我是雪妃，很高兴见到你！','我的名字是雪妃。',
                     '我叫御笠雪妃，你可以叫我雪妃。','你可以叫我雪妃哦。','叫我雪妃就好。',
                     '雪妃。','我是你的桌面伙伴，雪妃。','我叫“雪妃”。',
                     'My name is Yuki Mikasa.','YUKI MIKASA。'):
            with self.subTest(text=text): self.assertEqual(assess_name(text)['semantic_check'],'PASS')

    def test_other_self_names_are_not_accepted(self):
        for text in ('我叫汐蓝。','我的名字是小林。','我叫小林，雪妃是你。'):
            self.assertEqual(assess_name(text)['semantic_check'],'FAIL')

    def test_negated_name_is_not_accepted(self):
        for text in ('我不是雪妃。','我不叫雪妃。','我并非御笠雪妃。'):
            self.assertEqual(assess_name(text)['semantic_check'],'FAIL')

    def test_another_speaker_or_quoted_claim_does_not_pass(self):
        for text in ('她叫雪妃。','雪妃是她的名字。','她说：“我叫雪妃。”','你是雪妃。'):
            self.assertEqual(assess_name(text)['semantic_check'],'UNKNOWN')

    def test_hypothetical_and_reported_claims_are_unknown(self):
        for text in ('如果我叫雪妃，你会怎样？','听说我叫雪妃。','你说我是雪妃。','我是不是雪妃？'):
            self.assertEqual(assess_name(text)['semantic_check'],'UNKNOWN')

    def test_conflicting_claims_do_not_pass(self):
        for text in ('我是雪妃，但我不叫雪妃。','我叫雪妃，我的名字是小林。'):
            self.assertEqual(assess_name(text)['semantic_check'],'UNKNOWN')

    def test_name_prefix_is_not_exact_identity(self):
        for text in ('我是雪妃的朋友。','我叫雪妃二号。'):
            self.assertNotEqual(assess_name(text)['semantic_check'],'PASS')

    def test_empty_unknown_and_echo_stay_unknown(self):
        for text in ('',None,'今天天气很好。',QUESTION):
            self.assertEqual(assess_name(text)['semantic_check'],'UNKNOWN')

    def test_reason_outputs_never_contain_input_text(self):
        raw='PRIVATE arbitrary input'
        result=assess_name(raw)
        self.assertEqual(set(result),{'semantic_check','semantic_reason'})
        self.assertNotIn('PRIVATE',repr(result))


class MessageTests(unittest.TestCase):
    def test_only_static_contract_changes_for_b(self):
        messages=[{'role':'system','content':'canonical'}, {'role':'user','content':'reply_text不得改这个用户原文'}]
        original=copy.deepcopy(messages)
        self.assertEqual(model_messages('json',messages,'canonical','compact'),messages)
        changed=model_messages('dialogue_abc_v1',messages,'canonical','compact')
        self.assertEqual(changed[0]['content'],'compact')
        self.assertEqual(changed[1:],messages[1:]);self.assertEqual(messages,original)

    def test_unknown_mode_or_static_mismatch_rejected(self):
        for mode in ('other',True):
            with self.assertRaises(ValueError):model_messages(mode,[{'role':'system','content':'canonical'}],'canonical','compact')
        with self.assertRaises(ValueError):model_messages('json',[{'role':'system','content':'wrong'}],'canonical','compact')


class TrialTests(unittest.TestCase):
    def run_trial(self,b_text='我叫雪妃。',bad_b=False):
        calls=[]; guards=[]
        messages=[{'role':'system','content':'canonical'},{'role':'user','content':QUESTION}]
        def infer(mode,selected):
            calls.append((mode,copy.deepcopy(selected)))
            if mode=='json':value={'reply_text':'我叫雪妃。','emotion':'friendly','avatar_action':''}
            elif bad_b:value={'reply_text':b_text,'emotion':'friendly','avatar_action':''}
            else:value={'a':b_text,'b':'friendly','c':''}
            return {'text':json.dumps(value,ensure_ascii=False),'metrics':{'eval_count':12,'raw':'DO_NOT_SAVE'}}
        study=abba(infer,lambda:guards.append(True),messages=messages,candidate='dialogue_abc_v1',
                   validate_reply=validate,decode_reply=decode)
        return study,calls,guards

    def test_four_calls_no_warmups_and_same_public_input(self):
        study,calls,guards=self.run_trial()
        self.assertEqual([mode for mode,_ in calls],['json','dialogue_abc_v1','dialogue_abc_v1','json'])
        self.assertEqual(len(guards),8);self.assertEqual(len(study['trials']),4)
        self.assertTrue(all(row['semantic_check']=='PASS' for row in study['trials']))
        self.assertTrue(study['all_cross_arm_speech_identical'])

    def test_reply_length_change_is_explicit_even_when_names_both_pass(self):
        study,_,_=self.run_trial('我是雪妃，很高兴见到你。')
        self.assertTrue(all(row['semantic_check']=='PASS' for row in study['trials']))
        self.assertFalse(study['all_cross_arm_speech_identical'])
        self.assertTrue(all(row['same_speech_length'] is False for row in study['speech_comparisons']))

    def test_raw_text_or_hash_is_not_returned(self):
        study,_,_=self.run_trial()
        serialized=json.dumps(study,ensure_ascii=False)
        self.assertNotIn('我叫雪妃',serialized);self.assertNotIn('DO_NOT_SAVE',serialized)
        self.assertNotIn('sha256',serialized);self.assertNotIn('reply_text',serialized)

    def test_wrong_b_contract_is_not_accepted_as_canonical(self):
        study,_,_=self.run_trial(bad_b=True)
        for row in study['trials']:
            if row['arm']=='B':self.assertFalse(row['complete_json'])
        self.assertFalse(study['all_cross_arm_speech_identical'])

    def test_safety_guard_failure_prevents_all_model_calls(self):
        calls=[]
        def guard():raise RuntimeError('synthetic guard rejection')
        with self.assertRaises(RuntimeError):
            abba(lambda *args:calls.append(args),guard,messages=[],candidate='dialogue_abc_v1',validate_reply=validate,decode_reply=decode)
        self.assertEqual(calls,[])

    def test_invalid_cycle_cannot_expand_pilot_matrix(self):
        with self.assertRaises(ValueError):
            abba(lambda *args:None,lambda:None,messages=[],candidate='dialogue_abc_v1',validate_reply=validate,decode_reply=decode,cycles=2)


if __name__=='__main__':unittest.main()
