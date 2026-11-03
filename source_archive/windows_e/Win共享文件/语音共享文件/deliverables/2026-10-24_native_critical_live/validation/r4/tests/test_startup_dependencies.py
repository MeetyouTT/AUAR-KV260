import ast
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from board.vision import native_startup
from board.vision.person_bytetrack import PersonByteTracks,verify_sources


class Dependencies(unittest.TestCase):
    def config(self):
        folder=Path(__import__('board.vision.person_bytetrack',fromlist=['x']).__file__).parent/'bytetrack'
        names=['byte_tracker.py','kalman_filter.py','basetrack.py','matching.py','__init__.py','LICENSE','upstream_manifest.json']
        return dict(backend='bytetrack_numpy',source_sha256={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in names},
            track_threshold=.5,new_track_threshold=.6,match_threshold=.8,nominal_hz=10,lost_ms=500,confirm_observations=2)

    def test_actual_packaged_tracker_and_license_initialize(self):
        config=self.config();verify_sources(config)
        tracker=PersonByteTracks('dependency-check',config)
        result=tracker.update([],1,1.,640,480)
        self.assertEqual(result['tracks'],[])

    def test_missing_runtime_artifact_rejected_before_boot_consumption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'byte_tracker.py').write_text('#placeholder\n')
            config={'native_execution':{'seed':{}},'tracking':self.config()}
            import board.vision.person_bytetrack as tracking
            with patch.object(native_startup,'configuration',return_value=config['native_execution']), \
                 patch.object(native_startup,'verify_runtime_manifest'), \
                 patch.object(tracking,'verify_sources',side_effect=FileNotFoundError('LICENSE')), \
                 patch('board.vision.native_boot.checked_boot') as boot, \
                 patch.object(native_startup,'NativeContext') as factory:
                with self.assertRaises(FileNotFoundError):
                    native_startup.preflight(config,boot_id='unused',root=root)
                boot.assert_not_called();factory.assert_not_called()

    def test_tracker_initialization_precedes_native_adoption_and_worker_creation(self):
        source=Path(native_startup.__file__).parent/'ui_camera_service.py'
        tree=ast.parse(source.read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        text='\n'.join(source.read_text().splitlines()[function.lineno-1:])
        self.assertLess(text.index('tracker=Tracks(state.camera_epoch)'),text.index('detector,state.dpu_schedule=attach('))
        self.assertLess(text.index('tracker=Tracks(state.camera_epoch)'),text.index('state.identity = create_service('))


if __name__=='__main__':unittest.main()
