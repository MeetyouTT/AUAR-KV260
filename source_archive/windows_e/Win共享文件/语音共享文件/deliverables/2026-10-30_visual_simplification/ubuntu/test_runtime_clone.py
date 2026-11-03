"""Exercise the actual pinned launcher's log guard and uploader boundary."""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch

from runtime_clone import clone_runtime

HERE = Path(__file__).resolve().parent
LAUNCHER = HERE/'source_before/launcher.py'


def create_log(root):
    source = LAUNCHER.read_text()
    start = source.index("            sessions = root/'managed-runs'")
    end = source.index('                args = [sys.executable',start)
    namespace = dict(root=root, boot='SYNTHETIC_BOOT', time=time, shutil=shutil, os=os)
    exec(compile(textwrap.dedent(source[start:end]),str(LAUNCHER),'exec'),namespace)
    return namespace['log']


class RuntimeCloneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aura-visual-clone-test-')
        self.base = Path(self.tmp.name)
        self.old = self.base/'old'
        self.old.mkdir()
        (self.old/'aura').mkdir()
        (self.old/'aura/component.py').write_text('UNCHANGED = True\n')
        (self.old/'avatar_user_settings.json').write_text('{"muted":false}')
        (self.old/'launch.json').write_text('{"session":"old"}')
        self.log = create_log(self.old)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reproduce_previous_copy_failure(self):
        bad = self.base/'bad'
        shutil.copytree(self.old,bad,symlinks=True,
                        ignore=shutil.ignore_patterns('managed-runs','__pycache__'))
        self.assertEqual((bad/'stage.log').resolve(),self.log)
        with self.assertRaises(ValueError):
            create_log(bad)

    def test_new_root_generates_own_log_and_can_restart(self):
        new = clone_runtime(self.old,self.base/'new')
        self.assertFalse((new/'launch.json').exists())
        first = create_log(new)
        first.relative_to(new/'managed-runs')
        self.assertEqual((new/'stage.log').resolve(),first)
        second = create_log(new)
        self.assertNotEqual(first,second)
        self.assertEqual((new/'stage.log').resolve(),second)
        self.assertEqual((self.old/'stage.log').resolve(),self.log)

    def test_unmanaged_log_is_still_rejected(self):
        new = clone_runtime(self.old,self.base/'new')
        (new/'stage.log').write_text('preserve this evidence')
        with self.assertRaises(RuntimeError):
            create_log(new)
        self.assertEqual((new/'stage.log').read_text(),'preserve this evidence')

    def test_cross_root_link_is_still_rejected(self):
        new = clone_runtime(self.old,self.base/'new')
        (new/'stage.log').symlink_to(self.log)
        with self.assertRaises(ValueError):
            create_log(new)
        self.assertEqual((new/'stage.log').resolve(),self.log)

    def test_broken_link_is_still_rejected(self):
        new = clone_runtime(self.old,self.base/'new')
        (new/'stage.log').symlink_to(self.base/'missing.log')
        with self.assertRaises(FileNotFoundError):
            create_log(new)

    def test_components_settings_and_asset_links_preserved(self):
        asset = self.base/'assets'
        asset.mkdir()
        (self.old/'aura/assets').symlink_to(asset,target_is_directory=True)
        (self.old/'aura/__pycache__').mkdir()
        (self.old/'aura/__pycache__/stale.pyc').write_bytes(b'stale')
        (self.old/'aura/old.pyc').write_bytes(b'stale')
        new = clone_runtime(self.old,self.base/'new')
        self.assertEqual((new/'aura/component.py').read_bytes(),(self.old/'aura/component.py').read_bytes())
        self.assertEqual((new/'avatar_user_settings.json').read_bytes(),
                         (self.old/'avatar_user_settings.json').read_bytes())
        self.assertEqual(os.readlink(new/'aura/assets'),str(asset))
        self.assertFalse((new/'aura/__pycache__').exists())
        self.assertFalse((new/'aura/old.pyc').exists())

    def test_existing_destination_is_never_overwritten(self):
        with self.assertRaises(FileExistsError):
            clone_runtime(self.old,self.old)


class RetiredObserverTests(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location('retired_observer',HERE.parent/'board/device_observer.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_old_tick_cannot_enable_thread_capture_or_upload(self):
        cls = self.load().DeviceObserver
        with patch('threading.Thread',side_effect=AssertionError('Unexpected worker')), \
             patch('http.client.HTTPConnection',side_effect=AssertionError('Unexpected network')):
            observer = cls('SYNTHETIC_ONLY')
            for value in (True,False,True):
                observer.enabled = value
                observer.run()
                self.assertFalse(observer.enabled)
            self.assertFalse(observer.public()['image_upload_enabled'])
            self.assertEqual(observer.public()['sent'],0)
            observer.close()

    def test_cadence_input_contract_preserved(self):
        cls = self.load().DeviceObserver
        for cadence in (9,301):
            with self.assertRaises(ValueError):
                cls('SYNTHETIC_ONLY',interval=cadence)


if __name__ == '__main__':
    unittest.main(verbosity=2)
