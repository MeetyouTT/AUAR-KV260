"""Offline regression for the narrowly scoped new-boot publisher."""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import prepare_spec
import publish_newboot as publish


def definitions(source):
    return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


class NewBootPublisher(unittest.TestCase):
    def test_prepare_is_exact_original_v18_with_only_fresh_metadata(self):
        spec = prepare_spec.prepare()
        self.assertEqual(publish.BASE_STARTUP, spec['startup_sha256'])
        self.assertEqual(publish.BASE_MANIFEST, spec['source_manifest_sha256'])
        self.assertEqual(publish.inputs()[0], spec['component_sha256'])
        self.assertEqual({}, spec['source_overrides'])
        self.assertEqual('2344', spec['camera_owner']['camera_start_ticks'])
        self.assertEqual(publish.NEW_BOOT, spec['camera_owner']['board_boot_id'])

    def test_prepare_cannot_start_or_ready(self):
        for action in ('start','ready','normal-close','guard'):
            with self.subTest(action=action), self.assertRaises(ValueError):
                publish.validate_spec(prepare_spec.prepare(), action)

    def test_applied_cannot_bootstrap_guard(self):
        with self.assertRaises(ValueError):
            publish.validate_spec(prepare_spec.proposed({}), 'guard-failed')

    def test_exact_five_override_paths(self):
        self.assertEqual({'common/board_production_bootstrap.py','board/runtime/board_business.py',
            'tools/production_board_business_gui.py','tools/board_avatar_gtk.py','tools/x11_display_activity.py'},
            publish.ALLOWED_OVERRIDES)
        with self.assertRaises(ValueError):
            prepare_spec.proposed({'board/runtime/board_memory_policy.py': __file__})

    def test_unknown_or_changed_component_is_rejected(self):
        for kind in ('missing','extra','different'):
            spec = prepare_spec.proposed({})
            if kind == 'missing': spec['component_sha256'].pop('common/board_memory.py')
            if kind == 'extra': spec['component_sha256']['new.py'] = '0' * 64
            if kind == 'different': spec['component_sha256']['common/board_memory.py'] = '0' * 64
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                publish.validate_spec(spec,'start')

    def test_applied_rejects_other_gui_or_launcher_hashes(self):
        for key in ('configuration_sha256','startup_sha256'):
            spec = prepare_spec.proposed({}); spec[key] = '0' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                publish.validate_spec(spec,'start')

    def test_new_boot_pid_birth_and_readback_are_pinned(self):
        for section,key,value in [(None,'boot_id',publish.OLD_BOOT), ('camera_owner','camera_pid',260102),
                ('camera_owner','camera_start_ticks','2345'), ('face_readback','path',publish.OLD_READBACK)]:
            spec = prepare_spec.prepare()
            (spec if section is None else spec[section])[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                publish.validate_spec(spec,'guard-failed')

    def test_complete_remote_python39_parse_and_original_lifecycle(self):
        old = definitions(publish.pinned(publish.REPAIR / 'release_v18_candidate/FROZEN_PUBLISH_REMOTE.py', publish.BASE_REMOTE_SHA))
        new = definitions(publish.build_remote(prepare_spec.proposed({})))
        for name in ('window','close','start','ready','state','ready_state','owner','guarded'):
            with self.subTest(name=name):
                self.assertEqual(ast.dump(old[name],include_attributes=False),ast.dump(new[name],include_attributes=False))

    def test_guarded_normal_start_checks_both_lease_files(self):
        source = publish.build_remote(prepare_spec.proposed({}))
        self.assertIn('ownerless(u);writer_and_ui_leases_free()',source)
        self.assertIn("with open('/run/aura-avatar-ui.lock','a')",source)
        self.assertIn("open('/home/root/.local/share/aura-board-business/writer.lock','a')",source)
        self.assertIn("c.command(['/bin/systemctl','--no-block','start','aura-avatar-ui.service'])",source)

    def test_live_owner_blocks_failed_guard_before_any_writes(self):
        function = definitions(publish.build_remote())['guard_failed']
        calls = []
        def ownerless(_):
            calls.append('ownerless')
            raise ValueError('live_owner')
        namespace = {'boot':lambda:calls.append('boot'),'source':lambda:calls.append('source'),
            'journal':lambda:{},'c':types.SimpleNamespace(show=lambda:{}),'ownerless':ownerless}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<fake-guard>','exec'),namespace)
        with self.assertRaises(ValueError): namespace['guard_failed']()
        self.assertEqual(['boot','source','ownerless'],calls)

    def test_readback_verifier_is_original_exact_source_and_never_writes(self):
        remote = publish.build_remote()
        fn = definitions(remote)['reviewed_face']
        text = ast.get_source_segment(remote,fn)
        self.assertIn("['build_candidate']",text)
        self.assertNotIn('write_new_candidate',text)
        self.assertIn("reader.private_metadata(str(path))",text)
        self.assertIn("c.read(path,face['sha256'])",text)

    def test_default_dry_does_not_import_ssh_or_create_files(self):
        with patch.object(sys,'argv',['publish_newboot.py','guard-failed']):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                publish.main()
        self.assertEqual('DRY_SOURCE_VALIDATED_NO_SSH',json.loads(output.getvalue())['status'])
        self.assertNotIn('board_ssh',sys.modules)


if __name__ == '__main__':
    unittest.main()
