"""Real process-local settings with a fake target runner, restored on every path."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import gil_camera_launcher as launcher


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.target=self.root/'board_camera_motion.py'
        self.target.write_text('pass\n');self.sha=hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.before=sys.getswitchinterval();self.argv=sys.argv

    def call(self,runner=lambda *a,**kw:None,expected=None):
        return launcher.launch([str(self.target),'--config','original.json'],allowed_root=self.root,
            expected_sha=expected or self.sha,record_directory=self.root,runner=runner)

    def test_real_1ms_setting_args_record_and_restoration(self):
        def runner(*args,**kwargs):
            self.assertAlmostEqual(sys.getswitchinterval(),.001)
            self.assertEqual(sys.argv,[str(self.target),'--config','original.json'])
            self.assertEqual(kwargs,{'run_name':'__main__'})
        with patch.dict('os.environ',{'AURA_EXPERIMENT_GIL_MS':'1'}):self.call(runner)
        self.assertEqual(sys.getswitchinterval(),self.before);self.assertIs(sys.argv,self.argv)
        record=json.loads(next(self.root.glob('process-setting-*.json')).read_text())
        self.assertEqual(record['actual_start_seconds'],.001)

    def test_5ms_control_applies_same_wrapper(self):
        with patch.dict('os.environ',{'AURA_EXPERIMENT_GIL_MS':'5'}):
            self.call(lambda *a,**kw:self.assertAlmostEqual(sys.getswitchinterval(),.005))
        self.assertEqual(sys.getswitchinterval(),self.before)

    def test_native_or_application_exception_restores_interpreter_setting(self):
        def failed(*args,**kwargs):raise RuntimeError('synthetic target failure')
        with patch.dict('os.environ',{'AURA_EXPERIMENT_GIL_MS':'1'}),self.assertRaises(RuntimeError):self.call(failed)
        self.assertEqual(sys.getswitchinterval(),self.before);self.assertIs(sys.argv,self.argv)

    def test_wrong_hash_refuses_before_settings_or_record_write(self):
        with patch.dict('os.environ',{'AURA_EXPERIMENT_GIL_MS':'1'}),self.assertRaises(ValueError):self.call(expected='a'*64)
        self.assertEqual(sys.getswitchinterval(),self.before);self.assertFalse(list(self.root.glob('process-setting*')))

    def test_missing_or_unreviewed_interval_rejected(self):
        for value in ('','0','2','1.0'):
            with self.subTest(value=value),patch.dict('os.environ',{'AURA_EXPERIMENT_GIL_MS':value}),self.assertRaises(ValueError):self.call()
        self.assertEqual(sys.getswitchinterval(),self.before)

    def test_symlink_or_unrelated_target_rejected(self):
        self.target.unlink();other=self.root/'other.py';other.write_text('pass\n');self.target.symlink_to(other)
        with patch.dict('os.environ',{'AURA_EXPERIMENT_GIL_MS':'1'}),self.assertRaises(ValueError):self.call()
        self.assertEqual(sys.getswitchinterval(),self.before)


if __name__=='__main__':unittest.main(verbosity=2)
