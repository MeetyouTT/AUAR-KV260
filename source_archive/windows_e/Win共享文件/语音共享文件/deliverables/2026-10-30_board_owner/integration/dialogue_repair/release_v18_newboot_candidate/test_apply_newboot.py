"""Offline source and mutation-boundary tests for the new-boot apply step."""
import ast
import base64
import copy
import unittest

import apply_newboot_closed as apply
import prepare_spec
import publish_newboot as publish


class NewBootApply(unittest.TestCase):
    def test_source_parses_on_board_python39(self):
        ast.parse(apply.build_remote(prepare_spec.proposed({})),feature_version=(3,9))

    def test_no_main_source_dispatch_can_run_start_in_apply(self):
        source=apply.build_remote(prepare_spec.proposed({}))
        tree=ast.parse(source)
        calls=[]
        for node in tree.body:
            if isinstance(node,ast.With):
                calls += [n.func.id for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertIn('apply_closed',calls)
        self.assertNotIn('start',calls)
        self.assertNotIn('close',calls)
        self.assertNotIn('ready',calls)

    def test_original_v18_and_all_379_sources_are_checked(self):
        source=apply.build_remote(prepare_spec.proposed({}))
        for anchor in ["c.read(root/'startup/config.json',BASE_STARTUP_SHA)",
                "old_startup['component_sha256']==BASE_PINS", "for rel,pin in BASE_PINS.items():c.read",
                "c.read(root/'production_source_manifest.json',BASE_MANIFEST_SHA)",
                "manifest['component_pins']==BASE_PINS", "reviewed_face()"]:
            self.assertIn(anchor,source)

    def test_guard_and_actual_writer_locks_precede_verifier_and_mutation(self):
        text=apply.APPLY_REMOTE
        self.assertIn("j.get('phase')=='NEW_BOOT_OWNERLESS'",text)
        self.assertIn("private/'writer.lock',private/'speaker/speaker-writer.lock'",text)
        self.assertLess(text.index('fcntl.flock(stream'),text.index('proof=verify_production_bootstrap'))
        self.assertLess(text.index('proof=verify_production_bootstrap'),text.index('stage.mkdir'))
        self.assertLess(text.index("save(j)"),text.index("atomic(root/'runtime/aura'/rel,raw)"))

    def test_original_bytes_and_prepared_outputs_are_saved_first(self):
        text=apply.APPLY_REMOTE
        for anchor in ["c.create(backup/name,raw)","c.create(destination,original)",
                "c.create(stage/'applied-spec.json'", "c.create(stage/'prepared-manifest.json'"]:
            self.assertLess(text.index(anchor),text.index("atomic(root/'runtime/aura'/rel,raw)"))

    def test_manifest_configuration_metadata_matches_installed_and_prepared_bytes(self):
        text=apply.APPLY_REMOTE
        self.assertIn("manifest['configuration_sha256']=c.sha(new_gui_raw)",text)
        self.assertIn("manifest['configuration_path']=str(stage/'prepared-gui.json')",text)
        self.assertIn("c.create(stage/'prepared-gui.json',new_gui_raw)",text)
        self.assertLess(text.index("manifest['configuration_path']"),text.index('manifest_raw=c.encoded(manifest)'))
        self.assertLess(text.index('proof=verify_production_bootstrap'),text.index('stage.mkdir'))

    def test_applied_complete_sources_are_rechecked_before_return(self):
        text=apply.APPLY_REMOTE
        self.assertLess(text.index("atomic(root/'production_source_manifest.json',manifest_raw)"),
            text.index('source();ownerless(c.show());guarded(j)'))
        self.assertLess(text.index('source();ownerless(c.show());guarded(j)'),
            text.index("return dict(status='NEW_BOOT_SOURCES_APPLIED_UI_STOPPED'"))

    def test_empty_source_payload_is_config_only(self):
        self.assertEqual({},apply.payload_for(prepare_spec.proposed({})))

    def test_payload_is_exact_local_candidate_bytes(self):
        source=publish.REPAIR/'animation_thinking_collaboration/ui_responsiveness_v18/candidate/aura/tools/board_avatar_gtk.py'
        if not source.exists():
            self.skipTest('Candidate not yet sealed')
        spec=prepare_spec.proposed({'tools/board_avatar_gtk.py':source})
        payload=apply.payload_for(spec)['tools/board_avatar_gtk.py']
        self.assertEqual(source.read_bytes(),base64.b64decode(payload['base64'],validate=True))
        self.assertEqual(publish.inputs()[0]['tools/board_avatar_gtk.py'],payload['before_sha256'])


if __name__=='__main__':
    unittest.main()
