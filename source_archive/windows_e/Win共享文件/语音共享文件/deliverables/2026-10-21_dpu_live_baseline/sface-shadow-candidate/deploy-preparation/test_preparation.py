"""Local syntax, frozen-source pins and synthetic rollback byte protection."""
import ast
import importlib.util
from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('shadow_pilot_preparation',str(ROOT/'board_shadow_pilot.py'))
pilot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class PreparationTests(unittest.TestCase):
    def test_script_and_independent_rollback_parse_and_pin_frozen_sources(self):
        ast.parse((ROOT/'board_shadow_pilot.py').read_text())
        ast.parse(pilot.rollback_source(Path('/review-only')))
        self.assertEqual(len(pilot.OVERLAY),6)
        self.assertEqual(len(pilot.BASELINE),7)
        for relative,expected in pilot.OVERLAY.items():
            self.assertEqual(hashlib.sha256((ROOT.parent/'candidate/aura'/relative).read_bytes()).hexdigest(),expected)

    def test_rollback_restores_retained_yunet_bytes_and_only_controls_camera(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            old=b'ExecStart=/current-retained-yunet/aura/tools/board_camera_motion.py\n'
            new=b'ExecStart=/new-shadow/aura/tools/board_camera_motion.py\n'
            unit=root/'unit.service';unit.write_bytes(new)
            (root/'camera.service.original').write_bytes(old)
            (root/'camera.service.candidate').write_bytes(new)
            source=pilot.rollback_source(root).replace("Path('/etc/systemd/system/aura-camera-ui.service')",repr(unit))
            # repr(Path) is PosixPath(...), which requires an extra local symbol.
            calls=[]
            def run(args,**kwargs):calls.append(args);return subprocess.CompletedProcess(args,0)
            scope={'PosixPath':Path}
            try:
                with patch('subprocess.run',side_effect=run):exec(compile(source,'synthetic-rollback','exec'),scope)
            finally:
                if 'lock' in scope:scope['lock'].close()
            self.assertEqual(unit.read_bytes(),old)
            self.assertEqual(calls,[['systemctl','stop','aura-camera-ui.service'],
                ['systemctl','daemon-reload'],['systemctl','start','--no-block','aura-camera-ui.service']])

    def test_rollback_refuses_later_unrelated_unit_before_stop_or_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);unit=root/'unit.service'
            unit.write_bytes(b'later unrelated service')
            (root/'camera.service.original').write_bytes(b'retained yunet')
            (root/'camera.service.candidate').write_bytes(b'shadow candidate')
            source=pilot.rollback_source(root).replace("Path('/etc/systemd/system/aura-camera-ui.service')",repr(unit))
            scope={'PosixPath':Path}
            try:
                with patch('subprocess.run') as run:
                    with self.assertRaises(AssertionError):exec(compile(source,'synthetic-rollback','exec'),scope)
                    run.assert_not_called()
            finally:
                if 'lock' in scope:scope['lock'].close()
            self.assertEqual(unit.read_bytes(),b'later unrelated service')


if __name__=='__main__':unittest.main()
