import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import runtime_entry

BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'


class EntryTests(unittest.TestCase):
    def test_repeated_launches_keep_separate_records_and_original_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            records=[]
            def launch(argv,record_directory):
                records.append((list(argv),record_directory));return 17
            loader=lambda _:SimpleNamespace(launch=launch)
            argv=['/pinned/board_camera_motion.py','--config','/original/config.json']
            for _ in range(2):self.assertEqual(runtime_entry.launch(argv,root=tmp,boot_id=BOOT,loader=loader),17)
            self.assertEqual(records[0][0],argv);self.assertNotEqual(records[0][1],records[1][1])
            self.assertEqual(records[0][1].parent,Path(tmp)/'process-settings'/BOOT)

    def test_invalid_boot_or_missing_entry_never_loads_runtime(self):
        called=[]
        with tempfile.TemporaryDirectory() as tmp:
            for boot in ('../escape','not-a-uuid',BOOT.upper()):
                with self.assertRaises(ValueError):runtime_entry.launch(['camera'],root=tmp,boot_id=boot,loader=lambda p:called.append(p))
            with self.assertRaises(ValueError):runtime_entry.launch([],root=tmp,boot_id=BOOT,loader=lambda p:called.append(p))
        self.assertEqual(called,[])

    def test_symlink_record_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'release';root.mkdir();other=Path(tmp)/'other';other.mkdir()
            (root/'process-settings').symlink_to(other,target_is_directory=True)
            with self.assertRaises(ValueError):runtime_entry.launch(['camera'],root=root,boot_id=BOOT,loader=lambda p:None)
            self.assertEqual(list(other.iterdir()),[])

    def test_changed_wrapper_is_refused_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'gil_camera_launcher.py';path.write_text('raise RuntimeError("must not execute")\n')
            with self.assertRaises(RuntimeError):runtime_entry.load_wrapper(path)


if __name__=='__main__':unittest.main()
