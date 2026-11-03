"""Offline source and closure tests. No production/device imports or writes."""
import ast
import copy
import unittest
from unittest.mock import patch

import apply_stability_closed as apply
import stability_common as common


def fake_sources():
    pins=common.baseline()['component_sha256']
    return {rel:{'before_sha256':pins[rel],'sha256':str(index)*64,'local_source':'public-fixture-'+str(index)+'.py'}
        for index,rel in enumerate(sorted(common.ALLOWED_PATHS),1)}


def definitions(source):
    return {node.name:node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef)}


class MinorRelease(unittest.TestCase):
    def setUp(self):
        self.patch=patch.object(common,'approved_sources',side_effect=fake_sources)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_baseline_matches_actual_sealed_new_boot(self):
        spec=common.baseline()
        self.assertEqual(common.BASE_STARTUP_SHA,spec['startup_sha256'])
        self.assertEqual(common.BASE_MANIFEST_SHA,spec['source_manifest_sha256'])
        self.assertEqual(common.BASE_CONFIG_SHA,spec['configuration_sha256'])
        self.assertEqual(379,len(spec['component_sha256']))

    def test_allowlist_has_only_two_explicit_paths(self):
        self.assertEqual({'tools/board_avatar_gtk.py','tools/board_recording.py'},common.ALLOWED_PATHS)

    def test_proposed_changes_only_two_existing_source_pins(self):
        before=common.baseline();after=common.proposed()
        changed={rel for rel,pin in before['component_sha256'].items() if pin!=after['component_sha256'][rel]}
        self.assertEqual(common.ALLOWED_PATHS,changed)
        self.assertEqual(set(before['component_sha256']),set(after['component_sha256']))
        for key in ('configuration_sha256','native_library_sha256','character_pair_selection_sha256',
                    'face_readback','camera_owner','boot_id','retention_enabled','expected_final_listening_enabled'):
            self.assertEqual(before[key],after[key],key)

    def test_cold_boot_and_x11_pins_are_preserved(self):
        before=common.baseline();after=common.proposed()
        for rel in ('common/board_production_bootstrap.py','board/runtime/board_business.py',
                    'tools/production_board_business_gui.py','tools/x11_display_activity.py'):
            self.assertEqual(before['component_sha256'][rel],after['component_sha256'][rel])

    def test_only_baseline_can_be_explicitly_validated_as_baseline(self):
        common.validate_spec(common.baseline(),allow_baseline=True)
        with self.assertRaises(ValueError):common.validate_spec(common.baseline())

    def test_proposed_spec_cannot_be_started_or_declared_ready(self):
        spec=common.proposed()
        common.validate_spec(spec,allow_proposed=True)
        with self.assertRaises(ValueError):common.validate_spec(spec)

    def test_actual_applied_manifest_fingerprint_required(self):
        spec=common.proposed();spec['minor_state']='APPLIED'
        with self.assertRaises(ValueError):common.validate_spec(spec)
        spec['source_manifest_sha256']='d'*64
        self.assertEqual(spec,common.validate_spec(spec))

    def test_mutated_config_or_unapproved_component_rejected(self):
        for key in ('config','unknown','missing','coldboot','preference'):
            spec=common.proposed()
            if key=='config':spec['configuration_sha256']='0'*64
            if key=='unknown':spec['component_sha256']['unknown.py']='0'*64
            if key=='missing':del spec['component_sha256']['common/board_memory.py']
            if key=='coldboot':spec['component_sha256']['common/board_production_bootstrap.py']='0'*64
            if key=='preference':spec['expected_final_listening_enabled']=True
            with self.subTest(key=key),self.assertRaises(ValueError):common.validate_spec(spec,allow_proposed=True)

    def test_all_sources_parse_for_board_python39(self):
        ast.parse(common.publisher_remote(common.baseline()),feature_version=(3,9))
        ast.parse(apply.build_remote(common.proposed()),feature_version=(3,9))

    def test_original_normal_publication_lifecycle_is_preserved(self):
        before=definitions(common.previous_publisher().build_remote(common.baseline()))
        after=definitions(common.publisher_remote(common.baseline()))
        for name in ('guard','window','close','start','ready','inactive','source','boot','state','never_armed_paused_capture'):
            self.assertEqual(ast.dump(before[name],include_attributes=False),ast.dump(after[name],include_attributes=False),name)
        self.assertNotIn('guard_failed',after)

    def test_apply_requires_actual_normal_closed_inactive_unit(self):
        text=apply.APPLY_REMOTE
        self.assertIn("j.get('phase')=='NORMAL_CLOSED'",text)
        self.assertIn("c.show()['ActiveState']=='inactive'",text)
        self.assertIn('boot();j=journal();inactive(j)',text)

    def test_all_current_sources_private_receipt_and_locks_are_checked(self):
        text=apply.APPLY_REMOTE
        self.assertIn('for rel,pin in BASE_PINS.items():c.read',text)
        self.assertIn("private/'writer.lock',private/'speaker/speaker-writer.lock'",text)
        self.assertLess(text.index('fcntl.flock(stream'),text.index('proof=verify_production_bootstrap'))
        self.assertLess(text.index('proof=verify_production_bootstrap'),text.index('stage.mkdir'))

    def test_guards_and_before_bytes_precede_changes(self):
        text=apply.APPLY_REMOTE
        first_write=text.index("atomic(root/'runtime/aura'/rel,raw)")
        for anchor in ('c.create(backup/name,raw)','c.create(destination,original)',
                       "c.create(stage/'prepared-manifest.json'","phase='MINOR_SOURCE_INSTALL_INTENT'",'save(j)'):
            self.assertLess(text.index(anchor),first_write)
        self.assertLess(first_write,text.index('source();ownerless(c.show());guarded(j)'))

    def test_gui_config_is_verified_but_never_rewritten(self):
        text=apply.APPLY_REMOTE
        self.assertIn("c.read(manifest['configuration_path'],BASE_CONFIG_SHA)",text)
        self.assertIn("c.read(root/'runtime/aura/config/board_avatar_gtk.json',BASE_CONFIG_SHA)==gui_raw",text)
        self.assertNotIn("atomic(root/'runtime/aura/config/board_avatar_gtk.json'",text)
        assignments=[ast.get_source_segment(text,target) for node in ast.walk(ast.parse(text))
            if isinstance(node,ast.Assign) for target in node.targets]
        self.assertNotIn("manifest['configuration_path']",assignments)
        self.assertNotIn("manifest['configuration_sha256']",assignments)

    def test_apply_dispatch_never_starts_or_closes_a_process(self):
        tree=ast.parse(apply.build_remote(common.proposed()))
        calls=[]
        for node in tree.body:
            if isinstance(node,ast.With):
                calls += [item.func.id for item in ast.walk(node) if isinstance(item,ast.Call) and isinstance(item.func,ast.Name)]
        self.assertIn('apply_minor_closed',calls)
        self.assertNotIn('start',calls)
        self.assertNotIn('close',calls)


class FrozenPayload(unittest.TestCase):
    def test_actual_two_sources_match_author_bytes_and_current_baseline(self):
        sources=common.approved_sources();before=common.baseline()
        self.assertEqual(common.ALLOWED_PATHS,set(sources))
        for rel,row in sources.items():
            self.assertEqual(before['component_sha256'][rel],row['before_sha256'])
            self.assertEqual(row['sha256'],common.sha(common.pinned(row['local_source'],row['sha256'])))
        spec=common.proposed()
        self.assertEqual(379,len(spec['component_sha256']))
        self.assertEqual(spec,common.validate_spec(spec,allow_proposed=True))

    def test_actual_startup_pin_is_reproducible(self):
        spec=common.proposed()
        startup=common.previous_publisher().inputs()[1]
        startup['component_sha256']=spec['component_sha256']
        self.assertEqual(spec['startup_sha256'],common.sha(common.encoded(startup)))
        self.assertEqual(common.BASE_CONFIG_SHA,spec['configuration_sha256'])

    def test_unsealed_payload_hash_fails_before_transport(self):
        with patch.object(common,'APPROVED_PAYLOAD_SHA','0'*64):
            with self.assertRaises(ValueError):common.approved_sources()


if __name__=='__main__':
    unittest.main()
