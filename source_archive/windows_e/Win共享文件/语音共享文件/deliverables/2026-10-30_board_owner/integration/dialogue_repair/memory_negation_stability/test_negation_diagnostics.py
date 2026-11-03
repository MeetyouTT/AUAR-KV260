import json
import unittest

from negation_diagnostics import negation_diagnostics
from replay_public_negation import STORE


def source(text, **metadata):
    return dict(include_in_summary=True,text=text,metadata=metadata)


class NegationDiagnosticsTests(unittest.TestCase):
    def test_alternative_question_forms_are_counts_without_a_semantic_decision(self):
        result=negation_diagnostics([source('你会不会唱歌？')],'用户询问唱歌能力。',STORE.NEGATION)
        self.assertEqual(result['source_regex_matches'],1)
        self.assertEqual(result['source_guard_matches_in_alternative_forms'],1)
        self.assertEqual(result['source_guard_matches_outside_alternative_forms'],0)
        self.assertEqual(result['candidate_regex_matches'],0)
        self.assertNotIn('accepted',result)

    def test_explicit_negative_and_metadata_are_distinct(self):
        result=negation_diagnostics([source('声纹尚未校准，不能确认身份。',negated=True)],
            '声纹未校准，无法确认身份。',STORE.NEGATION)
        self.assertEqual(result['source_metadata_negated'],1)
        self.assertEqual(result['source_guard_matches_outside_alternative_forms'],2)
        self.assertEqual(result['candidate_regex_matches'],0)
        self.assertEqual(result['candidate_form_counts']['inability'],1)
        self.assertEqual(result['candidate_form_counts']['pending_or_unperformed'],1)

    def test_source_values_and_identifiers_never_appear(self):
        row=source('PUBLIC_PRIVATE_TEXT不会公开',names=['PUBLIC_PRIVATE_NAME'])
        row.update(event_id='PUBLIC_PRIVATE_ID',source='PUBLIC_PRIVATE_SOURCE')
        result=negation_diagnostics([row],'PUBLIC_PRIVATE_SUMMARY无法处理',STORE.NEGATION)
        encoded=json.dumps(result)
        self.assertNotIn('PUBLIC_PRIVATE',encoded)
        self.assertTrue(all(type(value) in (int,bool,dict) for value in result.values()))

    def test_bounds_and_wrong_shapes_are_explicit(self):
        result=negation_diagnostics([source('没有')]*70,'未曾',STORE.NEGATION)
        self.assertEqual(result['source_events'],64)
        self.assertEqual(result['truncated_sources'],6)
        invalid=negation_diagnostics([None,source('x'*32769)],object(),STORE.NEGATION)
        self.assertEqual(invalid['invalid_sources'],2)
        self.assertTrue(invalid['invalid_candidate'])

    def test_current_regex_is_not_changed_by_diagnostics(self):
        pattern=STORE.NEGATION.pattern
        negation_diagnostics([source('不会')],'无法',STORE.NEGATION)
        self.assertEqual(STORE.NEGATION.pattern,pattern)
        self.assertIsNone(STORE.NEGATION.search('无法'))
        self.assertIsNotNone(STORE.NEGATION.search('不会'))


if __name__=='__main__':
    unittest.main(verbosity=2)
