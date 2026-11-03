"""Read-only planning and pure canonical-gate checks using sealed metadata."""
import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import update_stability_docs as docs


class StabilityDocsTests(unittest.TestCase):
    def setUp(self):
        self.bundle = docs.read_bundle()

    def test_current_seal_yields_exact_twelve_paused_documents(self):
        plan = docs.build_plan(self.bundle)
        self.assertEqual(12, len(plan['updates']))
        self.assertEqual(docs.seal.EXPECTED_STARTUP, plan['observation']['startup_sha256'])
        self.assertIs(plan['observation']['listening']['enabled'], False)
        self.assertEqual('PAUSED', plan['observation']['listening']['state'])
        status = json.loads(plan['updates']['dialogue_STATUS'])
        self.assertIs(status['automatic_listening_restored'], False)
        self.assertIs(status['user_manual_pause_preserved'], True)
        self.assertIs(status['current_revision_acceptance']['full_physical_dialogue_acceptance'], False)

    def test_new_process_memory_does_not_inherit_old_counts_or_reason(self):
        observation = docs.build_plan(self.bundle)['observation']
        self.assertEqual(0, observation['memory']['worker']['completed'])
        self.assertEqual(5, observation['memory']['worker']['discarded'])
        self.assertIs(observation['memory']['specific_failure_reason_available'], False)
        self.assertEqual(0, observation['passive_observation']['armed'])
        self.assertIs(observation['pending']['m03_date_delete_deployed'], False)

    def test_uncommitted_or_superseded_canonical_is_rejected(self):
        raws = self.bundle['raws']
        marker = dict(phase='COMMITTED', spec_sha256=docs.seal.common.sha(raws['spec.json']),
                      ready_sha256=docs.seal.common.sha(raws['ready.json']))
        current = {'spec.json': raws['spec.json'], 'actual_ready.json': raws['ready.json']}
        docs.require_committed(raws, marker, current)
        for changed in (dict(marker, phase='PREPARED'), dict(marker, spec_sha256='0'*64)):
            with self.assertRaises(ValueError):
                docs.require_committed(raws, changed, current)
        with self.assertRaises(ValueError):
            docs.require_committed(raws, marker, dict(current, **{'spec.json': b'newer-publication'}))

    def test_previous_plaintext_suffixes_are_byte_exact(self):
        plan = docs.build_plan(self.bundle)
        old_note = (docs.REPAIR / 'docs_state_v18_minor/current_note.txt').read_bytes()
        for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
            self.assertEqual(plan['originals'][key][len(old_note):],
                             plan['updates'][key][len(plan['note'].encode('utf-8')):])

    def test_originals_and_prior_snapshot_are_unchanged_by_planning(self):
        before = docs.reference(docs.PRIOR)
        plan = docs.build_plan(self.bundle)
        self.assertEqual(before, docs.reference(docs.PRIOR))
        for key, path in plan['targets'].items():
            self.assertEqual(plan['originals'][key], path.read_bytes())

    def test_default_cli_never_applies_documents(self):
        with patch('sys.argv', ['update_stability_docs.py']), \
                patch.object(docs, 'apply_plan', side_effect=AssertionError('document mutation attempted')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            docs.main()
        self.assertIn('NO_WRITES', output.getvalue())


if __name__ == '__main__':
    unittest.main()
