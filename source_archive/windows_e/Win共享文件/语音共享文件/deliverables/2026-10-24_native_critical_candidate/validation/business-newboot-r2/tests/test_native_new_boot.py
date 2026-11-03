"""Explicit fake kernel boots; no reboot, DSO/model or device calls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from board.vision import native_boot, native_startup
from board.vision.native_binding import Seed,Recovery
from board.vision.native_protection import make_native_seed
import test_native_business as base_tests


OLD='11111111-1111-4111-8111-111111111111'
NEW='22222222-2222-4222-8222-222222222222'


class NewBootTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.state_dir=self.root/'kernel-state'
        self.source=self.root/'checkpoint.json'
        self.document=base_tests.ProtectionTests().document()
        self.document['seed']['boot_id']=OLD
        self.document['seed']['admissions'][1:]=[62491,755]
        self.document['seed']['overruns'][1:]=[5,3]
        self.document['seed']['completed'][2]=755
        self.document['seed']['disabled'][1:]=[1,1]
        for i,reason,faults,attempts,recoveries,window in ((0,1,5,4,4,1),(1,2,3,2,2,2)):
            self.document['seed']['recovery'][i].update(phase=3,reason=reason,faults=faults,
                attempts=attempts,recoveries=recoveries,history_opaque=1,opaque_attempt_count=window)
        self.document['auxiliary']['sface_counters'].update(requests=1178,execution_attempts=755,
            completed=755,features_returned=748,deferred=430,slot_denials=397)
        self.pin=self.pin_document(self.document)
        self.real_current_boot=native_boot.current_boot
        self.kernel=patch.object(native_boot,'current_boot',return_value=NEW)
        self.kernel_mock=self.kernel.start();self.addCleanup(self.kernel.stop)
        self.clock=patch('time.monotonic_ns',return_value=100_000_000)
        self.clock.start();self.addCleanup(self.clock.stop)

    def pin_document(self,document,path=None):
        path=self.source if path is None else path
        raw=(json.dumps(document,sort_keys=True)+'\n').encode();path.write_bytes(raw)
        return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}

    def load(self,pin=None):
        return native_boot.load_new_boot_checkpoint(pin or self.pin,boot_id=NEW,
            marker_directory=self.state_dir)

    def config(self,*,allow=True):
        source_root=self.root/'runtime';source_root.mkdir(exist_ok=True)
        (source_root/'placeholder.py').write_text('VALUE = 1\n')
        files={'placeholder.py':hashlib.sha256((source_root/'placeholder.py').read_bytes()).hexdigest()}
        manifest=self.root/'manifest.json'
        manifest.write_text(json.dumps({'schema':'aura-native-python-source-2','files':files}))
        native=dict(library=str(self.root/'unused.so'),library_sha256='1'*64,seed=self.pin,
            source_manifest=str(manifest),source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
            source_unit_sha256='2'*64,checkpoint_output=str(self.root/'next.json'))
        if allow:
            native.update(allow_new_kernel_boot=True,new_boot_marker_directory=str(self.state_dir))
        return dict(native_execution=native,detector_backend='dpu_yolox',
            optional_admission_floor_ms=30,yunet_dpu_recovery=True,sface_dpu_recovery=True),source_root

    def test_previous_large_uptime_is_archived_not_replayed(self):
        loaded=self.load()
        self.assertGreater(loaded['archive_seed']['captured_mono_ns'],loaded['seed']['captured_mono_ns'])
        self.assertEqual(loaded['seed']['captured_mono_ns'],100_000_000)
        self.assertEqual(loaded['seed']['purpose'],'validated_new_kernel_boot')
        self.assertEqual(loaded['seed']['overruns'],[0,0,0])
        self.assertEqual(loaded['seed']['disabled'],[0,0,0])
        self.assertEqual(loaded['auxiliary']['sface_counters']['completed'],0)
        self.assertEqual(loaded['archive_counters']['overruns'],[0,5,3])
        self.assertEqual(loaded['archive_counters']['sface_counters']['completed'],755)
        self.assertEqual([(r['faults'],r['attempts'],r['recoveries'])
            for r in loaded['archive_counters']['recovery']],[(5,4,4),(3,2,2)])
        seed=make_native_seed(loaded['seed'],Seed,Recovery)
        self.assertEqual(seed.source_pid,0)
        self.assertEqual(seed.checkpoint_kind,0)

    def test_boot_opt_in_is_false_by_default(self):
        config,root=self.config(allow=False)
        with self.assertRaisesRegex(ValueError,'explicit native opt-in'):
            native_startup.preflight(config,boot_id=NEW,root=root)
        self.assertFalse(self.state_dir.exists())

    def test_opt_in_requires_boolean_and_marker_path(self):
        config,_=self.config()
        config['native_execution']['allow_new_kernel_boot']=1
        with self.assertRaises(ValueError):native_startup.configuration(config)
        config['native_execution']['allow_new_kernel_boot']=True
        del config['native_execution']['new_boot_marker_directory']
        with self.assertRaises(ValueError):native_startup.configuration(config)

    def test_preflight_checks_real_running_boot_argument(self):
        config,root=self.config()
        with self.assertRaisesRegex(ValueError,'running kernel'):
            native_startup.preflight(config,boot_id=OLD,root=root)

    def test_current_boot_is_read_from_proc_without_trusting_arguments(self):
        with patch.object(native_boot,'current_boot',side_effect=self.real_current_boot):
            actual=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            self.assertEqual(native_boot.checked_boot(actual),actual)
            fake=OLD if actual != OLD else NEW
            with self.assertRaises(ValueError):native_boot.checked_boot(fake)

    def test_same_boot_still_uses_r1_live_predecessor_refusal(self):
        config,root=self.config()
        self.kernel_mock.return_value=OLD
        # r1 also checks capture <= current clock; use the actual archived range.
        with patch('time.monotonic_ns',return_value=2_000_000_000_000):
            with self.assertRaisesRegex(ValueError,'still alive'):
                native_startup.preflight(config,boot_id=OLD,root=root)
        self.assertFalse(self.state_dir.exists())

    def test_new_boot_does_not_reject_reused_pid_and_birth(self):
        # Source PID really exists in this fake test; a genuinely different
        # running kernel makes source-process identity a separate old epoch.
        loaded=self.load()
        self.assertEqual(loaded['archive_seed']['source_pid'],os.getpid())
        native_boot.commit_new_boot(loaded)
        self.assertTrue(Path(loaded['archive_path']).is_file())

    def test_archive_and_marker_exist_before_context_restore_and_adoption(self):
        loaded=self.load();config,_=self.config()
        owner=SimpleNamespace(handle=7)
        calls=[]
        class Context:
            quarantined=False
            def __init__(inner,*args):
                calls.append('create')
                self.assertTrue(Path(loaded['archive_path']).is_file())
                self.assertTrue(Path(loaded['marker']).is_file())
            def restore_seed(inner,seed):
                calls.append('restore')
                self.assertEqual(seed['purpose'],'validated_new_kernel_boot')
                raise ValueError('injected restore refusal')
            def close(inner):calls.append('close')
        with patch.object(native_startup,'NativeContext',Context):
            with self.assertRaisesRegex(ValueError,'restore refusal'):
                native_startup.attach(config,SimpleNamespace(),owner,loaded)
        self.assertEqual(calls,['create','restore','close'])
        with self.assertRaises(ValueError):self.load()

    def test_archive_retains_complete_old_checkpoint_and_exact_source_sha(self):
        loaded=self.load();native_boot.commit_new_boot(loaded)
        archive=Path(loaded['archive_path']);raw=archive.read_bytes();doc=json.loads(raw)
        self.assertEqual(doc['checkpoint'],self.document)
        self.assertEqual(doc['source_checkpoint_sha256'],self.pin['sha256'])
        self.assertEqual(doc['source_manifest_sha256'],'1'*64)
        self.assertEqual(doc['source_boot'],OLD);self.assertEqual(doc['current_boot'],NEW)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),loaded['archive_sha256'])
        self.assertEqual(self.state_dir.stat().st_mode & 0o777,0o700)
        self.assertEqual(archive.stat().st_mode & 0o777,0o600)

    def test_current_boot_marker_cannot_be_bypassed_with_a_different_seed(self):
        loaded=self.load();native_boot.commit_new_boot(loaded)
        other=copy.deepcopy(self.document);other['source_unit_sha256']='3'*64
        pin=self.pin_document(other,self.root/'other.json')
        with self.assertRaises(ValueError):self.load(pin)
        self.assertNotIn(self.pin['sha256'],Path(loaded['marker']).name)

    def test_archive_failure_never_reaches_context_creation_or_consumes_marker(self):
        loaded=self.load();config,_=self.config()
        self.state_dir.mkdir(mode=0o700)
        (self.state_dir/'archive').symlink_to(self.root,target_is_directory=True)
        with patch.object(native_startup,'NativeContext') as factory:
            with self.assertRaises(ValueError):native_startup.attach(config,SimpleNamespace(),object(),loaded)
        factory.assert_not_called()
        self.assertFalse(Path(loaded['marker']).exists())

    def test_marker_fsync_failure_leaves_consumed_boot_and_refuses_retry(self):
        loaded=self.load();real_sync=native_boot._fsync_directory
        def fail_after_marker(path):
            if Path(loaded['marker']).exists():raise OSError('injected directory fsync failure')
            return real_sync(path)
        with patch.object(native_boot,'_fsync_directory',side_effect=fail_after_marker):
            with self.assertRaises(OSError):native_boot.commit_new_boot(loaded)
        self.assertTrue(Path(loaded['marker']).exists())
        with self.assertRaises(ValueError):self.load()

    def test_existing_partial_marker_is_fail_closed(self):
        self.state_dir.mkdir(mode=0o700)
        _,marker=native_boot.marker_paths(self.state_dir,NEW);marker.write_bytes(b'partial')
        with self.assertRaises(ValueError):self.load()

    def test_insecure_directory_mode_is_refused(self):
        loaded=self.load();self.state_dir.mkdir(mode=0o755)
        with self.assertRaises(ValueError):native_boot.commit_new_boot(loaded)
        self.assertFalse(Path(loaded['marker']).exists())

    def test_symlink_directory_is_refused(self):
        redirect=self.root/'redirect';redirect.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):
            native_boot.load_new_boot_checkpoint(self.pin,boot_id=NEW,marker_directory=redirect)

    def test_current_future_capture_cannot_create_a_new_budget(self):
        loaded=self.load();loaded['seed']['captured_mono_ns']+=1
        with self.assertRaises(ValueError):native_boot.commit_new_boot(loaded)
        self.assertFalse(self.state_dir.exists())

    def test_changed_clean_seed_counters_are_refused_before_consumption(self):
        loaded=self.load();loaded['seed']['overruns'][1]=5
        with self.assertRaises(ValueError):native_boot.commit_new_boot(loaded)
        self.assertFalse(self.state_dir.exists())

    def test_invalid_source_classes_and_missing_fields_are_refused(self):
        mutations=[lambda d:d.update(schema='aura-dpu-protection-handoff-1'),
            lambda d:d.update(scope='health_prefix'),
            lambda d:d['seed'].update(purpose='isolated_model_equivalence'),
            lambda d:d['seed'].update(checkpoint_kind=2),
            lambda d:d['seed'].update(fenced=1),
            lambda d:d['auxiliary'].update(fenced=1),
            lambda d:d['auxiliary'].update(pending_result_tokens=[0,0,2]),
            lambda d:d['seed'].update(boot_id='not-a-boot'),
            lambda d:d['seed'].update(source_pid=0),
            lambda d:d['seed']['recovery'][0].update(observed_ns=2_000_000_000_000),
            lambda d:d['seed']['recovery'][0].update(attempt_times_ns=[1,0],attempt_count=1),
            lambda d:d['seed']['recovery'][0].update(phase=0),
            lambda d:d['auxiliary'].update(sface_counters={}),
            lambda d:d['seed'].pop('source_manifest_sha256')]
        for index,change in enumerate(mutations):
            with self.subTest(index=index):
                document=copy.deepcopy(self.document);change(document)
                with self.assertRaises((ValueError,KeyError)):
                    self.load(self.pin_document(document,self.root/('bad-'+str(index)+'.json')))
        self.assertFalse(self.state_dir.exists())

    def test_hash_change_between_validation_and_commit_is_refused(self):
        loaded=self.load();self.source.write_text('{}')
        with self.assertRaises(ValueError):native_boot.commit_new_boot(loaded)
        self.assertFalse(self.state_dir.exists())


if __name__=='__main__':unittest.main()
