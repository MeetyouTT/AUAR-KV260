"""Public filesystem and exact-baseline checks for the sole added component."""
import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import apply_stability_closed as apply
import stability_common as common


def need(value, code):
    if not value:
        raise ValueError(code)


def namespace(**extra):
    selected = [node for node in ast.parse(apply.APPLY_REMOTE).body
                if isinstance(node, ast.FunctionDef)
                and node.name in ('require_added_components_absent', 'install_added_component')]
    value = dict(need=need, NEW_SOURCE_PATHS=['board/runtime/history_delete.py'],
                 c=SimpleNamespace(relative=lambda value: value))
    value.update(extra)
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<public-new-component-test>', 'exec'), value)
    return value


class AddedComponentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='public-v20-new-file-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.file = self.root / 'runtime/aura/board/runtime/history_delete.py'
        self.file.parent.mkdir(parents=True)

    def test_exact_absent_component_is_accepted(self):
        namespace()['require_added_components_absent'](self.root)

    def test_existing_file_or_directory_is_rejected(self):
        for kind in ('file', 'directory'):
            with self.subTest(kind=kind):
                if kind == 'file':
                    self.file.write_bytes(b'public-existing-source')
                else:
                    self.file.mkdir()
                with self.assertRaisesRegex(ValueError, 'must_be_absent'):
                    namespace()['require_added_components_absent'](self.root)
                if kind == 'file':
                    self.assertEqual(self.file.read_bytes(), b'public-existing-source')
                    self.file.unlink()
                else:
                    self.file.rmdir()

    def test_dangling_symlink_is_rejected_even_when_exists_is_false(self):
        original = Path.is_symlink
        def simulated_link(path):
            return path == self.file or original(path)
        with patch.object(Path, 'is_symlink', simulated_link), self.assertRaisesRegex(ValueError, 'must_be_absent'):
            namespace()['require_added_components_absent'](self.root)

    def test_unexpected_added_path_is_rejected(self):
        for paths in ([], ['other.py'], ['board/runtime/history_delete.py', 'other.py']):
            with self.subTest(paths=paths), self.assertRaisesRegex(ValueError, 'allowlist'):
                namespace(NEW_SOURCE_PATHS=paths)['require_added_components_absent'](self.root)

    def install_namespace(self):
        calls = []
        def create(path, raw):
            with path.open('xb') as stream:
                stream.write(raw)
            calls.append('created')
        system = SimpleNamespace(O_DIRECTORY=1, O_RDONLY=2,
            open=lambda path, flags: calls.append(('directory', path)) or 101,
            fsync=lambda fd: calls.append(('fsync', fd)),
            close=lambda fd: calls.append(('close', fd)))
        return namespace(c=SimpleNamespace(create=create), os=system), calls

    def test_added_file_install_uses_exclusive_create_and_directory_sync(self):
        value, calls = self.install_namespace()
        value['install_added_component'](self.file, b'public-new-source')
        self.assertEqual(self.file.read_bytes(), b'public-new-source')
        self.assertEqual(calls, ['created', ('directory', str(self.file.parent)),
                                 ('fsync', 101), ('close', 101)])

    def test_file_appearing_after_absence_check_is_never_overwritten(self):
        namespace()['require_added_components_absent'](self.root)
        self.file.write_bytes(b'public-racing-source')
        value, calls = self.install_namespace()
        with self.assertRaises(FileExistsError):
            value['install_added_component'](self.file, b'public-new-source')
        self.assertEqual(self.file.read_bytes(), b'public-racing-source')
        self.assertEqual(calls, [])

    def test_linux_trusted_create_keeps_exclusive_nofollow_flags(self):
        path = common.REPAIR.parent / 'formal_character_switch/publish/formal_publish.py'
        raw = common.pinned(path, 'c97bdb5e87268e2fb846b171b9b0bb97cac98baa2664e733173912e73071956b')
        tree = ast.parse(raw)
        create = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'create')
        text = ast.get_source_segment(raw.decode(), create)
        self.assertIn('os.O_EXCL', text)
        self.assertIn('os.O_NOFOLLOW', text)
        self.assertIn('os.fsync(out.fileno())', text)


class FinalClosureTests(unittest.TestCase):
    def test_pending_final_payload_cannot_reach_transport_import(self):
        with patch.object(common, 'PAYLOAD_FINALIZED', False), self.assertRaisesRegex(ValueError, 'final_source'):
            common.execute_remote('', {}, timeout=1)

    def test_unsealed_ready_or_mapping_is_rejected(self):
        for name in ('BASE_READY_SHA', 'BASE_MAPPING_SHA'):
            with self.subTest(name=name), patch.object(common, name, None), self.assertRaisesRegex(ValueError, 'evidence_binding'):
                common.baseline()

    def test_uncommitted_mapping_or_enabled_ready_is_rejected(self):
        original = common.pinned
        for mode in ('mapping', 'ready'):
            def substitute(path, digest):
                raw = original(path, digest)
                path = Path(path)
                if path.name == ('source_mapping.json' if mode == 'mapping' else 'ready.json'):
                    value = json.loads(raw)
                    value['current_publication_committed' if mode == 'mapping' else 'listening_enabled'] = mode != 'mapping'
                    return common.encoded(value)
                return raw
            with self.subTest(mode=mode), patch.object(common, 'pinned', substitute), self.assertRaisesRegex(ValueError, 'committed_v19'):
                common.baseline()

    def test_new_component_cannot_claim_an_existing_before_hash(self):
        original = common.pinned
        def substitute(path, digest):
            raw = original(path, digest)
            if Path(path).name == 'APPROVED_PAYLOAD.json':
                value = json.loads(raw)
                value['sources']['board/runtime/history_delete.py']['before_sha256'] = 'a' * 64
                return common.encoded(value)
            return raw
        with patch.object(common, 'pinned', substitute), self.assertRaisesRegex(ValueError, 'source_baseline'):
            common.approved_sources()

    def test_absence_is_rechecked_after_leases_before_backups(self):
        text = apply.APPLY_REMOTE
        self.assertEqual(text.count('require_added_components_absent(root)'), 3)
        lease = text.index('fcntl.flock(stream')
        recheck = text.index('ownerless(c.show());guarded(j);reviewed_face();require_added_components_absent(root)')
        self.assertLess(lease, recheck)
        self.assertLess(recheck, text.index('proof=verify_production_bootstrap'))
        self.assertLess(recheck, text.index('stage.mkdir'))


if __name__ == '__main__':
    unittest.main()
