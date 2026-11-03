"""Exercise guarded two-file install and rollback on a temporary filesystem."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import install


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root/'bundle'
        self.bundle.mkdir()
        self.old = self.root/'active-launcher'
        self.old.write_bytes(b'old launcher')
        self.xorg = self.root/'active-xorg'
        self.xorg.write_bytes(b'old xorg')
        self.config = self.root/'config'
        self.config.write_bytes(b'unchanged config')
        for name, value in [('launcher.py',b'new launcher'),('xorg.conf',b'new xorg')]:
            (self.bundle/name).write_bytes(value)
        self.pid='123'
        self.proc=self.root/'proc/123/cmdline'
        self.proc.parent.mkdir(parents=True)
        self.proc.write_bytes(('python3\0'+str(self.old)+'\0--config\0'+str(self.config)+'\0').encode())
        self.boot=self.root/'boot';self.boot.write_text('test-boot')
        self.cid=self.root/'cid';self.cid.write_text('test-cid')
        self.manifest={'boot_id':'test-boot','cid':'test-cid','launcher':str(self.old),
            'launcher_sha256':install.digest(self.old),'config':str(self.config),
            'config_sha256':install.digest(self.config),'xorg_sha256':install.digest(self.xorg),
            'payload':{n:install.digest(self.bundle/n) for n in ('launcher.py','xorg.conf')}}
        (self.bundle/'manifest.json').write_text(json.dumps(self.manifest))
        mapping={'/etc/X11/xorg.conf':self.xorg,'/proc':self.root/'proc',
            '/sys/block/mmcblk1/device/cid':self.cid,'/proc/sys/kernel/random/boot_id':self.boot}
        def path(value):
            return mapping.get(str(value),Path(value))
        self.stack=[patch.object(install,'Path',path),patch.object(install,'__file__',str(self.bundle/'install.py')),
            patch.object(install.os,'geteuid',return_value=0),
            patch.object(install,'command',side_effect=lambda args: self.pid if args[0]=='systemctl' else '{}')]
        for item in self.stack:item.start();self.addCleanup(item.stop)

    def run_action(self, action):
        with patch('sys.argv',['install.py',action]):install.main()

    def test_install_and_explicit_rollback_preserve_original_bytes(self):
        self.run_action('apply')
        self.assertEqual(self.old.read_bytes(),b'new launcher')
        self.assertEqual(self.xorg.read_bytes(),b'new xorg')
        self.run_action('rollback')
        self.assertEqual(self.old.read_bytes(),b'old launcher')
        self.assertEqual(self.xorg.read_bytes(),b'old xorg')

    def test_concurrent_baseline_change_aborts_before_either_write(self):
        self.xorg.write_bytes(b'concurrent change')
        with self.assertRaises(AssertionError):self.run_action('apply')
        self.assertEqual(self.old.read_bytes(),b'old launcher')
        self.assertFalse((self.bundle/'backup').exists())

    def test_second_write_failure_rolls_back_first_write(self):
        original=install.replace
        def replace(path,data,mode):
            if path==self.xorg and data==b'new xorg':raise OSError('fixture second write failure')
            return original(path,data,mode)
        with patch.object(install,'replace',side_effect=replace):
            with self.assertRaises(OSError):self.run_action('apply')
        self.assertEqual(self.old.read_bytes(),b'old launcher')
        self.assertEqual(self.xorg.read_bytes(),b'old xorg')

    def test_rollback_cannot_overwrite_later_changes(self):
        self.run_action('apply')
        self.xorg.write_bytes(b'later change')
        with self.assertRaises(AssertionError):self.run_action('rollback')
        self.assertEqual(self.old.read_bytes(),b'new launcher')
        self.assertEqual(self.xorg.read_bytes(),b'later change')

    def test_failure_after_atomic_rename_still_rolls_back(self):
        original=install.replace
        def replace(path,data,mode):
            original(path,data,mode)
            if path==self.old and data==b'new launcher':raise OSError('fixture directory fsync failure')
        with patch.object(install,'replace',side_effect=replace):
            with self.assertRaises(OSError):self.run_action('apply')
        self.assertEqual(self.old.read_bytes(),b'old launcher')
        self.assertEqual(self.xorg.read_bytes(),b'old xorg')


if __name__=='__main__':unittest.main(verbosity=2)
