"""Source-only preparation and fake publisher tests; no SSH/device imports."""
import ast
import base64
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import apply_v18_closed as apply
import publish_v18 as publish
import v18_common as common


def v17(): return common.frozen_v17_spec(common.REPAIR / 'release_v17_candidate/v17_spec.json')
def fake_v18():
    d = v17()
    d.update(release_stage=common.STAGE, previous_startup_sha256=common.V17_STARTUP,
        startup_sha256='1'*64, source_manifest_sha256='2'*64,
        release_sources={k: row[2] for k, row in common.CORE.items()})
    return d


class ClosedRelease(unittest.TestCase):
    def test_local_bundle_exact_three_pinned_sources_no_optional_contract(self):
        revision, payload = apply.local_bundle()
        self.assertEqual(set(common.CORE), set(payload))
        self.assertEqual({}, revision['business_options'])
        self.assertNotIn('gui_options', revision)
        self.assertNotIn('D01', json.dumps(revision))
        for rel, value in payload.items():
            self.assertEqual(common.CORE[rel][1], value['before_sha256'])
            self.assertEqual(common.CORE[rel][2], common.sha(base64.b64decode(value['base64'], validate=True)))

    def test_all_remote_source_parses_for_board_python39(self):
        ast.parse(apply.build_remote(), feature_version=(3, 9))
        ast.parse(publish.build_remote(), feature_version=(3, 9))

    def test_apply_original_io_lock_private_and_backup_guards_preserved(self):
        original = common.remote_from('listening_entry_fix/apply_closed_revision.py', common.APPLY_SHA)
        candidate = apply.build_remote()
        def functions(source):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
        for name in ['read', 'create', 'replace']:
            self.assertEqual(functions(original)[name], functions(candidate)[name])
        for anchor in ["with open('/run/aura-production-publisher.lock','a') as publication:",
            "with open(private/'writer.lock','a') as writer:", "journal['phase']=='NORMAL_CLOSED'",
            "unit['SendSIGKILL']=='no'", "unit['TimeoutStopUSec']=='infinity'",
            "verify_production_bootstrap(private,cfg['board_business']['bootstrap_receipt']",
            "for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)",
            "stage.mkdir(mode=0o700);backup=stage/'before';backup.mkdir(mode=0o700)"]:
            self.assertIn(anchor, candidate)
        self.assertIn('cfgraw=old_cfg;cfgpin=sha(cfgraw);assert cfgpin==CONFIG_SHA', candidate)
        self.assertNotIn("cfg['board_business'].update(REVISION['business_options'])", candidate)

    def test_spec_rejects_old_native_wrong_sources_and_non_v18_start(self):
        self.assertEqual(v17(), common.validate_spec(v17(), allow_v17=True))
        self.assertEqual(fake_v18(), common.validate_spec(fake_v18()))
        with self.assertRaises(ValueError): common.validate_spec(v17())
        for change in ['native', 'sources', 'config', 'pins', 'stage']:
            d = fake_v18()
            if change == 'native': d['native_library_sha256']='887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2'
            if change == 'sources': d['release_sources']['common/board_memory.py']='0'*64
            if change == 'config': d['configuration_sha256']='0'*64
            if change == 'pins': d['component_pins']=378
            if change == 'stage': d['release_stage']='response-latency-v17-unreviewed'
            with self.subTest(change=change), self.assertRaises(ValueError): common.validate_spec(d, allow_v17=True)

    def test_dry_main_never_invokes_ssh_and_never_creates_spec(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(apply, 'HERE', Path(temp)), patch.object(apply, 'ssh_json') as ssh:
                with patch.object(sys, 'argv', ['apply_v18_closed.py']), contextlib.redirect_stdout(io.StringIO()):
                    apply.main()
                ssh.assert_not_called(); self.assertFalse((Path(temp)/'v18_spec.json').exists())
            with patch.object(publish, 'HERE', Path(temp)), patch.object(publish, 'ssh_json') as ssh:
                with patch.object(sys, 'argv', ['publish_v18.py', 'start']), contextlib.redirect_stdout(io.StringIO()):
                    publish.main()
                ssh.assert_not_called(); self.assertFalse((Path(temp)/'v18_spec.json').exists())

    def test_successful_fake_apply_creates_only_new_spec_and_keeps_v17_bytes(self):
        revision, payload = apply.local_bundle()
        original = common.REPAIR / 'release_v17_candidate/v17_spec.json'
        old = original.read_bytes()
        result = dict(status='LISTENING_REVISION_INSTALLED_UI_STOPPED', stage=common.STAGE,
            startup_sha256='1'*64, source_manifest_sha256='2'*64, configuration_sha256=common.CONFIG_SHA,
            component_pins=379, source_files={k: row['sha256'] for k, row in payload.items()}, business_options={},
            native_library_sha256=common.NATIVE_SHA, character_pair_selection_sha256=common.PAIR_SHA)
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(apply, 'HERE', Path(temp)), patch.object(apply, 'ssh_json', return_value=result) as ssh:
                with patch.object(sys, 'argv', ['apply_v18_closed.py', '--execute-root-only']), contextlib.redirect_stdout(io.StringIO()):
                    apply.main()
                self.assertEqual(1, ssh.call_count)
                next_spec = json.loads((Path(temp)/'v18_spec.json').read_bytes())
                self.assertEqual(common.STAGE, common.validate_spec(next_spec)['release_stage'])
                self.assertEqual(common.CONFIG_SHA, next_spec['configuration_sha256'])
        self.assertEqual(old, original.read_bytes())

    def test_existing_new_spec_blocks_before_ssh(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'v18_spec.json'; path.write_bytes(b'public existing spec')
            with patch.object(apply, 'HERE', Path(temp)), patch.object(apply, 'ssh_json') as ssh:
                with patch.object(sys, 'argv', ['apply_v18_closed.py', '--execute-root-only']), self.assertRaises(AssertionError):
                    apply.main()
                ssh.assert_not_called(); self.assertEqual(b'public existing spec', path.read_bytes())

    def test_normal_close_requires_window_proof_and_fresh_source_before_window(self):
        remote = publish.build_remote(); tree = ast.parse(remote)
        window = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='window')
        called = []
        def rejected_source():
            called.append('source'); raise ValueError('synthetic source mismatch')
        namespace = dict(boot=lambda: called.append('boot'), source=rejected_source)
        exec(compile(ast.Module(body=[window], type_ignores=[]), '<fake-window>', 'exec'), namespace)
        with self.assertRaises(ValueError): namespace['window']()
        self.assertEqual(['boot', 'source'], called)
        self.assertIn("proof=window();need(c.sha(c.encoded(proof))==TOKEN", remote)
        self.assertIn("need(window()==proof,'window_changed_before_close')", remote)
        self.assertIn("c.same(c.process(proof['owner']['pid']),proof['owner'])", remote)

    def test_new_native_pair_sources_and_all_three_paths_pinned_in_publisher(self):
        remote = publish.build_remote()
        self.assertNotIn("=='887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2'", remote)
        self.assertIn("c.read(root/'production_source_manifest.json',SPEC['source_manifest_sha256'])", remote)
        self.assertIn("for rel,pin in selected.items():need(cfg['component_sha256'][rel]==pin", remote)
        self.assertIn('never_armed_paused_capture(v)', remote)
        self.assertIn("pair['native_config']['fps']==16", remote)


if __name__ == '__main__': unittest.main()
