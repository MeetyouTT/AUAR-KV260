"""Exercise real-file rollback and refusal to overwrite later changes."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('candidate',Path(__file__).with_name('native_firstmode_install.py'))
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
BASELINE = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_original_baseline/evidence/hdmi-original-flicker-timing.json')

class InstallationTests(unittest.TestCase):
    def setUp(self):
        import json
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.xorg = self.root/'etc/X11/xorg.conf'
        self.uenv = self.root/'boot/uEnv.txt'
        self.xorg.parent.mkdir(parents=True)
        self.uenv.parent.mkdir(parents=True)
        self.before_xorg = json.loads(BASELINE.read_text())['/etc/X11/xorg.conf']['text'].encode()
        self.before_uenv = b'bootargs=earlycon console=ttyPS1,115200 clk_ignore_unused root=/dev/ram0 rw init_fatal_sh=1 cma=1536M zynqmp_dpsub.power_on_delay_ms=5000\nuenvcmd=echo AURA DP wake delay configured: 5000 ms\n'
        self.xorg.write_bytes(self.before_xorg)
        self.uenv.write_bytes(self.before_uenv)

    def assert_originals(self):
        self.assertEqual(self.xorg.read_bytes(),self.before_xorg)
        self.assertEqual(self.uenv.read_bytes(),self.before_uenv)

    def test_install_and_rollback_preserve_bootargs(self):
        candidate.install(self.root,{})
        self.assertEqual(self.xorg.read_text(),candidate.NATIVE_XORG)
        expected = self.before_uenv.replace(b'power_on_delay_ms=5000\n',b'power_on_delay_ms=5000 drm_kms_helper.fbdev_emulation=0\n')
        self.assertEqual(self.uenv.read_bytes(),expected)
        candidate.rollback(self.root)
        self.assert_originals()

    def test_integrity_loader_without_file_global(self):
        source=Path(__file__).with_name('native_firstmode_install.py')
        namespace={'__name__':'reviewed_uart_exec'}
        exec(compile(source.read_bytes(),str(source),'exec'),namespace)
        self.assertNotIn('__file__',namespace)
        namespace['install'](self.root,{})
        namespace['rollback'](self.root)
        self.assert_originals()

    def inject_after_replace(self,fail_at):
        calls = []
        def fail(path,data,mode):
            candidate.atomic_write(path,data,mode)
            calls.append(path)
            if len(calls)==fail_at:
                raise OSError('injected failure after atomic replacement')
        with self.assertRaises(OSError):
            candidate.install(self.root,{},writer=fail)
        self.assert_originals()

    def test_failure_after_first_replace_restores_files(self):
        self.inject_after_replace(1)

    def test_failure_after_second_replace_restores_files(self):
        self.inject_after_replace(2)

    def test_changed_boot_config_refused_before_backup(self):
        later = self.before_uenv+b'# later change\n'
        self.uenv.write_bytes(later)
        with self.assertRaises(AssertionError):
            candidate.install(self.root,{})
        self.assertEqual(self.uenv.read_bytes(),later)
        self.assertEqual(self.xorg.read_bytes(),self.before_xorg)
        self.assertFalse((self.root/candidate.BACKUP.lstrip('/')).exists())

    def test_rollback_refuses_later_edit_without_partial_write(self):
        candidate.install(self.root,{})
        installed_uenv=self.uenv.read_bytes()
        self.xorg.write_text('# later user edit\n')
        with self.assertRaises(AssertionError):
            candidate.rollback(self.root)
        self.assertEqual(self.xorg.read_text(),'# later user edit\n')
        self.assertEqual(self.uenv.read_bytes(),installed_uenv)

if __name__ == '__main__':
    unittest.main(verbosity=2)
