"""Original-API call-through orchestration with synthetic adapter test doubles.

No original Native validator or C library is executed by this local test file.
"""
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'candidate'))
import original_history_gate as bridge
import recovery_rules as rules
import boot_recovery as runtime
spec = importlib.util.spec_from_file_location('history_gate_public_helpers', HERE / 'tests/test_boot_recovery.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def history_fixture():
    head = dict(archive_path='/public/archive/older.json', archive_sha256='1' * 64,
                source_boot='bbbbbbbb-cccc-4ddd-8eee-ffffffffffff', source_checkpoint_sha256='2' * 64,
                history_is_lower_bound=True, scope='public historical metadata')
    row = dict(path=head['archive_path'], sha256=head['archive_sha256'], current_boot=helpers.PREVIOUS,
               source_boot=head['source_boot'], source_checkpoint_sha256=head['source_checkpoint_sha256'], history_is_lower_bound=True)
    return dict(head=head, archive_count=1, archives=[row], legacy_pin=dict(path='/public/legacy.json', sha256='3' * 64))


class FakeAdapter:
    CHECKPOINT = Path('/public/final.json')
    SOURCE_UNIT = '4' * 64

    def __init__(self, request):
        self.calls = []
        self.history = copy.deepcopy(request['history_expected'])
        self.document = json.loads(helpers.final_fixture())
        self.document['seed']['source_manifest_sha256'] = '5' * 64
        self.document['source_unit_sha256'] = self.SOURCE_UNIT
        self.document['previous_kernel_history'] = self.history['head']
        self.expected = dict(boot_id=helpers.BOOT, checkpoint_pin=request.get('checkpoint_pin'), camera_owner=helpers.OWNER,
                             history=dict(self.history, provenance_pin=dict(path='/public/provenance.json', sha256='6' * 64)))
        self.stop_bounds_validated = True
        outer = self
        class Snapshot:
            def pinned(self, pin):
                outer.calls.append('pinned:' + pin['path'])
                return outer.document if Path(pin['path']) == outer.CHECKPOINT else outer.expected
            def unchanged(self):
                outer.calls.append('unchanged')
        self.Snapshot = Snapshot

    def original_modules(self, snapshot):
        self.calls.append('original_modules')
        outer = self
        def sealed(document):
            outer.calls.append('_sealed_source')
            return document['seed'], {}
        return object(), types.SimpleNamespace(_sealed_source=sealed,
                                               marker_paths=lambda directory, boot: (Path(directory), Path(directory) / ('kernel-boot-' + boot + '.consumed')))

    def optional_shape(self, auxiliary, protection):
        self.calls.append('original_optional_shape')

    def validate_chain(self, document, history, snapshot, protection, boot_module):
        self.calls.append('original_validate_chain')
        if document['previous_kernel_history'] != self.history['head'] or history != self.history:
            raise ValueError('Original chain rejected changed head/order/bytes')
        return self.history['archives']

    def main(self):
        self.calls.append('original_same_boot_complete_main')
        if not self.stop_bounds_validated:
            raise ValueError('Original current-final stop/bounds validation failed')
        print(json.dumps(dict(schema='aura-fresh-final-history-validation-1', status='ORIGINAL_CURRENT_FINAL_AND_COMPLETE_HISTORY_VERIFIED',
                              checkpoint_pin=self.expected['checkpoint_pin'], source_owner=helpers.OWNER,
                              expected_sha256='7' * 64, original_load_business_checkpoint_called=True,
                              complete_ordered_history_verified=True, all_required_current_boot_cumulative_lower_bounds_checked=True,
                              archives=self.history['archives'])))


def request_fixture(kind='cold_predecessor'):
    result = dict(schema='aura-original-history-gate-request-1', boot_id=helpers.BOOT, kind=kind,
                  history_expected=history_fixture(), checkpoint_pin=dict(path='/public/final.json', sha256='8' * 64),
                  source_owner=helpers.OWNER, source_boot=helpers.PREVIOUS, source_manifest_sha256='5' * 64,
                  new_boot_marker_directory='/public/kernel-history')
    if kind == 'same_boot_resume':
        result.update(source_boot=helpers.BOOT, normal_stop_expected_pin=dict(path='/public/expected.json', sha256='7' * 64))
    if kind == 'running_archive_chain':
        result.pop('checkpoint_pin')
    return result


class OriginalHistoryCallThroughTests(unittest.TestCase):
    def execute(self, adapter, request):
        with patch.object(bridge.os.path, 'lexists', return_value=False):
            return bridge.execute_request(adapter, request, '9' * 64, helpers.BOOT)

    def test_cold_uses_original_archive_validator_without_same_boot_reader(self):
        request = request_fixture()
        adapter = FakeAdapter(request)
        result = self.execute(adapter, request)
        self.assertIn('_sealed_source', adapter.calls)
        self.assertIn('original_validate_chain', adapter.calls)
        self.assertNotIn('original_same_boot_complete_main', adapter.calls)
        self.assertFalse(result['checkpoint_or_marker_written'])

    def test_final_without_accepted_history_head_is_refused(self):
        request = request_fixture()
        adapter = FakeAdapter(request)
        adapter.document.pop('previous_kernel_history')
        with self.assertRaises((KeyError, ValueError)):
            self.execute(adapter, request)

    def test_changed_ordered_archive_manifest_is_not_approved(self):
        request = request_fixture()
        adapter = FakeAdapter(request)
        request['history_expected']['archives'][0]['sha256'] = 'a' * 64
        with self.assertRaises(ValueError):
            self.execute(adapter, request)

    def test_same_boot_calls_original_complete_guard(self):
        request = request_fixture('same_boot_resume')
        adapter = FakeAdapter(request)
        result = self.execute(adapter, request)
        self.assertIn('original_same_boot_complete_main', adapter.calls)
        self.assertNotIn('original_modules', adapter.calls)
        self.assertTrue(result['original_same_boot_result']['all_required_current_boot_cumulative_lower_bounds_checked'])

    def test_same_boot_wrong_final_is_rejected_before_original_main(self):
        request = request_fixture('same_boot_resume')
        adapter = FakeAdapter(request)
        adapter.expected['checkpoint_pin'] = dict(path='/public/final.json', sha256='b' * 64)
        with self.assertRaises(ValueError):
            self.execute(adapter, request)
        self.assertNotIn('original_same_boot_complete_main', adapter.calls)

    def test_same_boot_original_bounds_failure_is_not_converted_to_approval(self):
        request = request_fixture('same_boot_resume')
        adapter = FakeAdapter(request)
        adapter.stop_bounds_validated = False
        with self.assertRaisesRegex(ValueError, 'stop/bounds'):
            self.execute(adapter, request)

    def test_running_chain_header_never_calls_sealed_source_on_a_fake_current_final(self):
        request = request_fixture('running_archive_chain')
        adapter = FakeAdapter(request)
        result = self.execute(adapter, request)
        self.assertIn('original_validate_chain', adapter.calls)
        self.assertNotIn('_sealed_source', adapter.calls)
        self.assertFalse(result['native_context_created'])
        self.assertNotIn('pinned:/public/final.json', adapter.calls)

    def test_wrong_request_boot_is_refused_before_any_original_call(self):
        request = request_fixture()
        request['boot_id'] = helpers.PREVIOUS
        adapter = FakeAdapter(request)
        with self.assertRaises(ValueError):
            self.execute(adapter, request)
        self.assertEqual(adapter.calls, [])

    def test_prepare_history_failure_stops_before_any_original_client(self):
        temporary = helpers.tempfile.TemporaryDirectory(dir=HERE / 'test_work')
        try:
            recovery = helpers.FakeRecovery(temporary.name)
            def no_history(*args):
                raise rules.Hold('EXACT_FINAL_OR_ORIGINAL_COMPLETE_HISTORY_NOT_VERIFIED')
            recovery.check_prestart_history = no_history
            with patch.object(runtime, 'regular', recovery.read):
                with self.assertRaisesRegex(rules.Hold, 'COMPLETE_HISTORY_NOT_VERIFIED'):
                    recovery.prepare()
            self.assertEqual(recovery.events, ['verify_original_release'])
        finally:
            helpers.checked_cleanup(temporary)

    def test_new_boot_extends_only_original_commit_edge_and_preserves_all_old_rows(self):
        previous = history_fixture()
        gate = dict(predecessor=dict(boot_id=helpers.PREVIOUS), checkpoint_sha256='8' * 64)
        head = dict(archive_path='/public/archive/new.json', archive_sha256='c' * 64, source_boot=helpers.PREVIOUS,
                    source_checkpoint_sha256='8' * 64, history_is_lower_bound=False, scope='actual original live metadata')
        handoff = dict(previous_kernel_history=head, archive_path=head['archive_path'], archive_sha256=head['archive_sha256'])
        updated = rules.next_history_expected(previous, gate, handoff, helpers.BOOT)
        self.assertEqual(updated['archive_count'], 2)
        self.assertEqual(updated['archives'][1:], previous['archives'])
        self.assertEqual(updated['legacy_pin'], previous['legacy_pin'])
        handoff['archive_sha256'] = 'd' * 64
        with self.assertRaises(rules.Hold):
            rules.next_history_expected(previous, gate, handoff, helpers.BOOT)


if __name__ == '__main__':
    (HERE / 'test_work').mkdir(exist_ok=True)
    unittest.main(verbosity=2)
