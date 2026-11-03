import bootstrap
import hashlib,json,tempfile,unittest
from pathlib import Path
from board.vision.dpu_protection_handoff import restore_protection
from board.vision.dpu_vision_schedule import DpuVisionSchedule
import test_protection_handoff as fixtures

OLD='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
NEW='197de08c-bf50-4ad8-9955-25d69a3c100a'
class FreshBootTests(unittest.TestCase):
    def run_restore(self,folder,boot=NEW,allowed=True,seed=None):
        seed=fixtures.HandoffTests().seed() if seed is None else seed;seed['boot']=OLD
        p=Path(folder)/'seed.json';raw=json.dumps(seed).encode();p.write_bytes(raw)
        s=DpuVisionSchedule(yunet_recovery=True,sface_recovery=True)
        meta=restore_protection(s,dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest()),
            boot_id=boot,allow_new_boot=allowed,clock_ns=lambda:1)
        return s,meta
    def test_new_kernel_boot_is_new_window_not_old_monotonic_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            s,m=self.run_restore(folder)
            self.assertEqual(s.primary_calls,0);self.assertEqual(s.jobs,{})
            self.assertEqual(s.yunet_recovery.phase,'RUNNING');self.assertEqual(s.sface_recovery.phase,'RUNNING')
            self.assertEqual(m['previous_snapshot_faults'],{'yunet':1,'sface':1});self.assertTrue(m['first_use'])
            self.assertEqual(m['source_boot'],OLD);self.assertEqual(m['current_boot'],NEW)
    def test_duplicate_in_same_new_boot_holds_both_optional_jobs(self):
        with tempfile.TemporaryDirectory() as folder:
            self.run_restore(folder);s,m=self.run_restore(folder)
            self.assertFalse(m['first_use'])
            self.assertTrue(all(s.jobs[k]['disabled'] for k in ('yunet','sface')))
            self.assertEqual(s.sface_recovery.phase,'LATCHED');self.assertEqual(s.yunet_recovery.phase,'LATCHED')
    def test_another_real_boot_has_separate_consumption_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            self.run_restore(folder)
            s,m=self.run_restore(folder,boot='8be089ce-4275-49b6-80ac-99bff69abf2d')
            self.assertTrue(m['first_use']);self.assertEqual(s.sface_recovery.phase,'RUNNING')
    def test_cross_boot_is_disabled_unless_explicit_boolean_true(self):
        for allowed in (False,None,1,'true'):
            with self.subTest(allowed=allowed),tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):self.run_restore(folder,allowed=allowed)
    def test_noncanonical_boot_never_becomes_a_marker_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):self.run_restore(folder,boot='../other')
            self.assertFalse(list(Path(folder).glob('*.consumed')))
    def test_corrupt_hash_rejected_even_for_new_boot(self):
        with tempfile.TemporaryDirectory() as folder:
            seed=fixtures.HandoffTests().seed();seed['boot']=OLD;p=Path(folder)/'seed.json';p.write_text(json.dumps(seed))
            s=DpuVisionSchedule(yunet_recovery=True,sface_recovery=True)
            with self.assertRaises(ValueError):restore_protection(s,dict(path=str(p),sha256='0'*64),boot_id=NEW,allow_new_boot=True)
    def test_seed_file_is_not_modified_by_fresh_boot(self):
        with tempfile.TemporaryDirectory() as folder:
            seed=fixtures.HandoffTests().seed();seed['boot']=OLD
            self.run_restore(folder,seed=seed)
            self.assertEqual(json.loads((Path(folder)/'seed.json').read_text()),seed)
