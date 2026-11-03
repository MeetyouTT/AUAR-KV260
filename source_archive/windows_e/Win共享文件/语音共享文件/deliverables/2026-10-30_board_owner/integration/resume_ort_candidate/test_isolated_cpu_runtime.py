"""Synthetic path/preload fixtures; no native dependency, board or model access."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile


HELPER = Path(__file__).with_name('isolated_cpu_runtime.py')
SPEC = importlib.util.spec_from_file_location('isolated_runtime_fixture', HELPER)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class WheelFixtures(unittest.TestCase):
    def check(self, entries):
        data = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(data, 'w') as archive:
                for name, value in entries:
                    archive.writestr(name, value)
        data.seek(0)
        with zipfile.ZipFile(data) as archive:
            selected, skipped = runtime.checked_entries(archive, 'onnxruntime', '1.19.2')
            return [entry.filename for entry in selected], skipped

    def test_only_packaged_example_models_are_omitted(self):
        selected, skipped = self.check([
            ('onnxruntime/__init__.py', b''),
            ('onnxruntime.libs/dependency.so', b'fixture'),
            ('onnxruntime-1.19.2.dist-info/METADATA', b'fixture'),
            ('onnxruntime/datasets/example.onnx', b'example'),
        ])
        self.assertEqual(len(selected), 3)
        self.assertEqual(skipped, ['onnxruntime/datasets/example.onnx'])

    def test_traversal_absolute_and_noncanonical_paths_rejected(self):
        for name in ('../escape', '/absolute', 'onnxruntime/../escape',
                     'onnxruntime//double.py', './onnxruntime/item.py'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.check([(name, b'fixture')])

    def test_foreign_distribution_root_rejected(self):
        with self.assertRaises(ValueError):
            self.check([('sitecustomize.py', b'fixture')])

    def test_duplicate_member_rejected(self):
        with self.assertRaises(ValueError):
            self.check([('onnxruntime/item.py', b'a'), ('onnxruntime/item.py', b'b')])

    def test_zip_symlink_rejected(self):
        link = zipfile.ZipInfo('onnxruntime/symlink')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(ValueError):
            self.check([(link, b'../../outside')])

    def test_expansion_limit_rejected_without_large_allocation(self):
        entry = zipfile.ZipInfo('onnxruntime/large')
        entry.file_size = 256 * 1024 * 1024 + 1
        archive = type('FakeArchive', (), {'infolist': lambda self: [entry]})()
        with self.assertRaises(ValueError):
            runtime.checked_entries(archive, 'onnxruntime', '1.19.2')


class PreloadFixtures(unittest.TestCase):
    def invoke(self, probe_body, expected_ort='1.19.2'):
        with tempfile.TemporaryDirectory(prefix='aura-ort-fixture-') as temporary:
            root = Path(temporary)
            chosen, old = root / 'chosen', root / 'old'
            for folder, version in ((chosen, '1.19.2'), (old, 'old')):
                (folder / 'numpy').mkdir(parents=True)
                (folder / 'numpy/__init__.py').write_text("__version__ = '1.26.4'\n", encoding='utf-8')
                (folder / 'onnxruntime/capi').mkdir(parents=True)
                (folder / 'onnxruntime/__init__.py').write_text(
                    "__version__ = " + repr(version) + "\ndef get_available_providers(): return ['CPUExecutionProvider']\n",
                    encoding='utf-8')
                (folder / 'onnxruntime/capi/__init__.py').write_text('', encoding='utf-8')
                (folder / 'onnxruntime/capi/onnxruntime_pybind11_state.py').write_text(
                    '# Fake pure Python binding; never native.\n', encoding='utf-8')
            probe = root / 'probe.py'
            probe.write_text('OLD = ' + repr(str(old)) + '\n' + probe_body, encoding='utf-8')
            config = dict(ort_root=str(chosen), ort_version=expected_ort,
                          numpy_root=str(chosen), numpy_version='1.26.4',
                          paths=[], probe=str(probe), probe_sha256=runtime.sha(probe), probe_args=[])
            saved_path, saved_argv = sys.path[:], sys.argv[:]
            try:
                with patch.dict(sys.modules):
                    for key in list(sys.modules):
                        if key == 'numpy' or key.startswith('numpy.') or key == 'onnxruntime' or key.startswith('onnxruntime.'):
                            del sys.modules[key]
                    with patch.object(runtime, 'platform_guard'), patch.object(runtime, 'native_maps', return_value=[]):
                        with contextlib.redirect_stderr(io.StringIO()) as output:
                            runtime.child(config)
                            lines = output.getvalue().splitlines()
                            return {line.split(' ', 1)[0]: json.loads(line.split(' ', 1)[1]) for line in lines}
            finally:
                sys.path[:], sys.argv[:] = saved_path, saved_argv

    def test_original_probe_prepending_old_dependencies_keeps_selected_modules(self):
        proofs = self.invoke("import sys\nsys.path.insert(0, OLD)\nimport numpy, onnxruntime\n"
                             "assert numpy.__version__ == '1.26.4'\n"
                             "assert onnxruntime.__version__ == '1.19.2'\nraise SystemExit(0)\n")
        self.assertEqual(proofs['ORT_PRELOAD_PROOF']['ort_version'], '1.19.2')
        self.assertEqual(proofs['ORT_ISOLATION_PROOF']['numpy_version'], '1.26.4')
        self.assertFalse(proofs['ORT_ISOLATION_PROOF']['hot_reload_performed'])

    def test_wrong_selected_version_fails_before_probe(self):
        with self.assertRaisesRegex(RuntimeError, 'ORT version'):
            self.invoke("raise AssertionError('probe must not run')\n", expected_ort='1.17.3')

    def test_probe_replacing_preloaded_module_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'replaced its preloaded runtime'):
            self.invoke("import sys\nsys.modules['numpy'] = object()\n")

    def test_nonzero_probe_exit_is_preserved(self):
        with self.assertRaises(SystemExit) as caught:
            self.invoke('raise SystemExit(7)\n')
        self.assertEqual(caught.exception.code, 7)


if __name__ == '__main__':
    unittest.main(verbosity=2)
