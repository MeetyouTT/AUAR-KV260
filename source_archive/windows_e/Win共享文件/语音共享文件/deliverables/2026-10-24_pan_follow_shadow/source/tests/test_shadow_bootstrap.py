import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'shadow_runtime' / 'native_entry_shadow.py'
spec = importlib.util.spec_from_file_location('shadow_bootstrap', SOURCE)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def test_preserves_original_guarded_entry_and_only_swaps_camera_run_target(self):
        calls = []
        runpy = SimpleNamespace()
        camera = Path('/runtime/aura/board/vision/ui_camera_service.py')
        wrapper = Path('/runtime/aura/tools/board_camera_motion.py')
        original_entry = Path('/ops/native_entry.py')

        def original(path, *args, **kwargs):
            path = Path(path)
            calls.append((path, kwargs.get('run_name')))
            if path == original_entry:
                runpy.run_path(str(camera), run_name='__main__')
            return {'path': str(path)}

        runpy.run_path = original
        original = bootstrap.hook_camera_run(runpy, camera, wrapper)
        sys.argv = [str(original_entry)]
        original(str(original_entry), run_name='__main__')
        self.assertEqual(calls, [(original_entry, '__main__'), (wrapper, '__main__')])
        self.assertEqual(sys.argv[0], str(wrapper))

    def test_other_runpy_targets_pass_through_unchanged(self):
        marker = []
        camera = Path('/runtime/ui_camera_service.py')
        wrapper = Path('/runtime/board_camera_motion.py')
        unrelated = Path('/runtime/fixture.py')
        runpy = SimpleNamespace(run_path=lambda path, **kwargs: marker.append((path, kwargs)))
        original = bootstrap.hook_camera_run(runpy, camera, wrapper)
        runpy.run_path(unrelated, run_name='fixture')
        self.assertEqual(marker, [(unrelated, {'run_name': 'fixture'})])
        self.assertIsNot(runpy.run_path, original)


if __name__ == '__main__':
    unittest.main()
