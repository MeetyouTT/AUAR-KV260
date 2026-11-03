"""Numeric legacy evidence + explicitly fake kernels; no device/model access."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from board.vision import native_boot, native_startup
from board.vision.native_binding import Seed, Recovery
from board.vision.native_protection import make_native_seed
import test_native_new_boot as exact_tests


NEW = '22222222-2222-4222-8222-222222222222'


class LegacyBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.state_dir=self.root/'kernel-state'
        self.source=self.root/'prefix.json'
        self.document=json.loads((Path(__file__).parent/'fixtures/legacy-boot-archive.json').read_text())
        self.old=self.document['source_boot']
        self.pin=self.pin_document(self.document)
        kernel=patch.object(native_boot,'current_boot',return_value=NEW)
        self.kernel=kernel.start();self.addCleanup(kernel.stop)
        clock=patch('time.monotonic_ns',return_value=100_000_000)
        clock.start();self.addCleanup(clock.stop)

    def pin_document(self, document, path=None):
        path=self.source if path is None else path
        raw=json.dumps(document,sort_keys=True).encode();path.write_bytes(raw)
        return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}

    def resign_payload(self):
        self.document['legacy_payload_sha256']=hashlib.sha256(
            native_boot._canonical(self.document['legacy_payload'])).hexdigest()
        self.pin=self.pin_document(self.document)

    def load(self, pin=None, allow=True, boot=NEW):
        return native_boot.load_new_boot_checkpoint(pin or self.pin,boot_id=boot,
            marker_directory=self.state_dir,allow_legacy=allow)

    def config(self):
        config, root=exact_tests.NewBootTests.config(self)
        native=config['native_execution']
        native['allow_legacy_new_kernel_boot']=True
        native['source_unit_sha256']=self.document['source_unit_sha256']
        return config,root

    def test_real_numeric_prefix_is_preserved_as_lower_bound_only(self):
        loaded=self.load()
        self.assertTrue(loaded['archive_counters']['history_is_lower_bound'])
        self.assertTrue(loaded['archive_counters']['unknown_tail'])
        self.assertEqual(loaded['archive_counters']['overruns'],[0,5,3])
        self.assertEqual(loaded['seed']['overruns'],[0,0,0])
        self.assertGreater(loaded['archive_seed']['captured_mono_ns'],loaded['seed']['captured_mono_ns'])
        self.assertEqual(make_native_seed(loaded['seed'],Seed,Recovery).checkpoint_kind,0)
        native_boot.commit_new_boot(loaded)
        archived=json.loads(Path(loaded['archive_path']).read_text())
        self.assertEqual(archived['checkpoint'],self.document)
        self.assertTrue(archived['history_is_lower_bound']);self.assertTrue(archived['unknown_tail'])

    def test_same_kernel_cannot_unlock_legacy_LATCHED(self):
        self.kernel.return_value=self.old
        with self.assertRaisesRegex(ValueError,'Same-boot'):
            self.load(boot=self.old)
        config,root=self.config()
        with self.assertRaisesRegex(ValueError,'Legacy health-only'):
            native_startup.preflight(config,boot_id=self.old,root=root)
        self.assertFalse(self.state_dir.exists())

    def test_separate_legacy_opt_in_is_mandatory(self):
        with self.assertRaisesRegex(ValueError,'separate opt-in'):self.load(allow=False)
        config,root=self.config();config['native_execution'].pop('allow_legacy_new_kernel_boot')
        with self.assertRaisesRegex(ValueError,'separate opt-in'):
            native_startup.preflight(config,boot_id=NEW,root=root)

    def test_both_opt_ins_must_be_booleans_and_enabled(self):
        config,_=self.config();config['native_execution']['allow_new_kernel_boot']=False
        with self.assertRaises(ValueError):native_startup.configuration(config)
        config,_=self.config();config['native_execution']['allow_legacy_new_kernel_boot']=1
        with self.assertRaises(ValueError):native_startup.configuration(config)

    def test_boot_argument_cannot_impersonate_the_kernel(self):
        with self.assertRaisesRegex(ValueError,'running kernel'):self.load(boot=self.old)

    def test_unknown_owner_rejected_even_with_resigned_payload(self):
        self.document['legacy_payload']['schedule']['owner_fenced']=True;self.resign_payload()
        with self.assertRaisesRegex(ValueError,'Unknown legacy'):self.load()

    def test_unconfirmed_fault_rejected(self):
        self.document['legacy_payload']['schedule']['optional_diagnostics']['fault_events'][0]['native_status']=1
        self.resign_payload()
        with self.assertRaisesRegex(ValueError,'completion was not proven'):self.load()

    def test_missing_fault_evidence_rejected(self):
        self.document['legacy_payload']['schedule']['optional_diagnostics']['fault_events'].pop()
        self.resign_payload()
        with self.assertRaisesRegex(ValueError,'evidence count differs'):self.load()

    def test_code_manifest_and_payload_hashes_are_checked(self):
        name=next(iter(self.document['source_manifest']))
        self.document['source_manifest'][name]='0'*64
        self.pin=self.pin_document(self.document)
        with self.assertRaisesRegex(ValueError,'manifest hash differs'):self.load()

    def test_duplicate_provenance_must_match(self):
        self.document['source_birth_ticks']+=1;self.pin=self.pin_document(self.document)
        with self.assertRaisesRegex(ValueError,'provenance differs'):self.load()

    def test_fault_must_lie_inside_its_source_clock_prefix(self):
        event=self.document['legacy_payload']['schedule']['optional_diagnostics']['fault_events'][0]
        event['lease_release_decision_mono_ns']=self.document['captured_mono_ns']+1
        self.resign_payload()
        with self.assertRaisesRegex(ValueError,'completion was not proven'):self.load()

    def test_marker_blocks_another_prefix_in_the_same_new_boot(self):
        loaded=self.load();native_boot.commit_new_boot(loaded)
        other=copy.deepcopy(self.document)
        other['captured_mono_ns']+=1;other['legacy_payload']['captured_mono_ns']+=1
        other['legacy_payload_sha256']=hashlib.sha256(native_boot._canonical(other['legacy_payload'])).hexdigest()
        pin=self.pin_document(other,self.root/'other-prefix.json')
        with self.assertRaisesRegex(ValueError,'already consumed'):self.load(pin)

    def test_archive_failure_precedes_native_context_creation(self):
        loaded=self.load();config,_=self.config()
        self.state_dir.mkdir(mode=0o700)
        (self.state_dir/'archive').symlink_to(self.root,target_is_directory=True)
        with patch.object(native_startup,'NativeContext') as factory:
            with self.assertRaises(ValueError):native_startup.attach(config,SimpleNamespace(),object(),loaded)
        factory.assert_not_called()
        self.assertFalse(Path(loaded['marker']).exists())

    def fake_context(self):
        document=exact_tests.base_tests.ProtectionTests().document()
        document['seed']['boot_id']=NEW
        document['seed']['captured_mono_ns']=100_000_000
        class Context:
            quarantined=False
            def restore_seed(inner,seed):pass
            def adopt_yolo(inner):pass
            def close(inner):pass
            def checkpoint(inner,manifest):return copy.deepcopy(document['seed'])
            def snapshot(inner):
                return dict(active=0,primary_waiting=0,fenced=0,pending_result_tokens=[0]*3,
                    seed_loaded=1,quiesced=1)
        return Context()

    def test_archive_hash_link_is_written_into_the_next_sealed_checkpoint(self):
        loaded=self.load();config,_=self.config();context=self.fake_context()
        state=SimpleNamespace(pipeline_metrics=SimpleNamespace(optional_diagnostics=None),identity=None)
        def owner_factory(original,ctx,schedule):
            return SimpleNamespace(native_context=ctx,close=ctx.close)
        with patch.object(native_startup,'NativeContext',return_value=context), \
                patch.object(native_startup,'NativeYoloOwner',side_effect=owner_factory):
            owner,schedule=native_startup.attach(config,state,object(),loaded)
        state.dpu_schedule=schedule
        schedule.optional_status=lambda kind:{}
        written=native_startup.shutdown(config,state,owner)
        checkpoint=json.loads(Path(written['path']).read_text())
        link=checkpoint['previous_kernel_history']
        self.assertEqual(link['archive_sha256'],loaded['archive_sha256'])
        self.assertEqual(link['archive_path'],loaded['archive_path'])
        self.assertTrue(link['history_is_lower_bound'])
        self.assertEqual(checkpoint['seed']['source_pid'],os.getpid())

    def test_same_boot_attachment_carries_one_archive_link_without_nesting(self):
        config,_=self.config();context=self.fake_context()
        source=exact_tests.base_tests.ProtectionTests().document()
        history={'archive_path':'/private/archive.json','archive_sha256':'1'*64,
                 'source_boot':self.old,'history_is_lower_bound':True}
        source['previous_kernel_history']=copy.deepcopy(history)
        loaded=dict(seed=source['seed'],auxiliary=source['auxiliary'],document=source,
            sha256='2'*64,marker=str(self.root/'sameboot-consumed'))
        state=SimpleNamespace(pipeline_metrics=SimpleNamespace(optional_diagnostics=None))
        with patch.object(native_startup,'NativeContext',return_value=context), \
                patch.object(native_startup,'NativeYoloOwner',return_value=SimpleNamespace()):
            _,schedule=native_startup.attach(config,state,object(),loaded)
        self.assertEqual(schedule.protection_handoff['previous_kernel_history'],history)


if __name__=='__main__':unittest.main()
