"""Actual frozen public bytes, fake metadata, AST only; no remote execution."""
import ast
import base64
import copy
import json
from pathlib import Path
import unittest
import apply_v17_closed as apply
import publish_v17_ready as publish
from release_common import (APPLY_SHA,PUBLISH_SHA,V16_STARTUP,V16_MANIFEST,V16_CONFIG,
    STAGE,OLD_PAIR,NEW_PAIR,NEW_NATIVE,remote_from,sha)


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.revision,cls.payload,cls.audit=apply.local_bundle()
        cls.remote=apply.build_remote(cls.revision,cls.payload,cls.audit)
        cls.old_pair_bytes=apply.pinned(apply.ANIM/'before/aura/config/yuki_pair.formal.json',OLD_PAIR)

    def preflight(self):
        cfg=dict(board_business=dict(asr_variant='paraformer_small',asr_threads=3,
            asr_directory='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6'),
            character_pair=dict(selection_sha256=OLD_PAIR),untouched=['public-sentinel'])
        namespace=dict(SPEC=dict(startup_sha256=V16_STARTUP,configuration_sha256=V16_CONFIG,component_pins=378),
            V16_STARTUP=V16_STARTUP,V16_MANIFEST=V16_MANIFEST,V16_CONFIG=V16_CONFIG,
            REVISION=copy.deepcopy(self.revision),V17_STAGE=STAGE,NEW_PAIR=NEW_PAIR,
            OLD_PAIR=OLD_PAIR,NEW_NATIVE=NEW_NATIVE,NON_PY=apply.NON_PY,
            cfg=cfg,gui_options={},PAYLOAD=copy.deepcopy(self.payload),ARTIFACTS=copy.deepcopy(self.audit),
            EXPECTED_PAYLOAD={r:[v['sha256'],v['before_sha256']] for r,v in self.payload.items()},
            EXPECTED_ARTIFACTS={k:v['sha256'] for k,v in self.audit.items()},
            root=Path('/public-fixture-only'),read=lambda path,pin:self.old_pair_bytes,
            base64=base64,sha=sha,json=json,ast=ast)
        return namespace

    def run_preflight(self,namespace):
        # Execute only the added source/receipt/config checks in RAM. The
        # original remote file/systemd/lock/bootstrap/write blocks never run.
        exec(compile(apply.PREFLIGHT,'<v17-public-preflight-only>','exec'),namespace)

    def test_exact_13_payload_and_real_receipts_pass(self):
        self.assertEqual(len(self.payload),13)
        self.assertEqual([r for r,v in self.payload.items() if v['before_sha256'] is None],['common/feature_intents.py'])
        self.assertEqual({r for r in self.payload if not r.endswith('.py')},set(apply.NON_PY))
        self.run_preflight(self.preflight())

    def test_unknown_payload_tampered_bytes_receipts_or_asr_settings_reject(self):
        for change in ('extra','missing','bytes','receipt','asr_threads','asr_variant','business_options','gui_options'):
            with self.subTest(change=change):
                n=self.preflight()
                if change=='extra':n['PAYLOAD']['extra.so']=next(iter(n['PAYLOAD'].values()))
                elif change=='missing':n['PAYLOAD'].pop('tools/native_yuki.py')
                elif change=='bytes':n['PAYLOAD']['tools/libaura_yuki.so']['base64']=base64.b64encode(b'bad').decode()
                elif change=='receipt':n['ARTIFACTS']['build']['base64']=base64.b64encode(b'{}').decode()
                elif change=='asr_threads':n['cfg']['board_business']['asr_threads']=1
                elif change=='asr_variant':n['cfg']['board_business']['asr_variant']='baseline'
                elif change=='business_options':n['REVISION']['business_options']={'asr_threads':1}
                else:n['gui_options']={'voice_barge_in':True}
                with self.assertRaises((AssertionError,ValueError)):self.run_preflight(n)

    def test_pair_persona_presentation_and_other_runtime_pin_changes_reject(self):
        before=json.loads(self.old_pair_bytes)
        after=json.loads(base64.b64decode(self.payload['config/yuki_pair.formal.json']['base64']))
        for change in ('identity','presentation','runtime'):
            changed=copy.deepcopy(after)
            if change=='identity':changed['identity']['formal_name']='synthetic-change'
            elif change=='presentation':changed['presentation']['revision']='synthetic-change'
            else:changed['runtime_pins']['tools/egl_window.py']='0'*64
            with self.assertRaises(AssertionError):apply.validate_pair(before,changed,self.payload)

    def test_only_actual_gui_selection_assignment_changes_config(self):
        nodes=[n for n in ast.walk(ast.parse(self.remote)) if isinstance(n,ast.Assign)
               and len(n.targets)==1 and ast.unparse(n.targets[0])=="cfg['character_pair']['selection_sha256']"]
        self.assertEqual(len(nodes),1)
        cfg=self.preflight()['cfg'];before=copy.deepcopy(cfg)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-config-assignment>','exec'),dict(cfg=cfg,NEW_PAIR=NEW_PAIR))
        expected=copy.deepcopy(before);expected['character_pair']['selection_sha256']=NEW_PAIR
        self.assertEqual(cfg,expected)
        self.assertEqual(cfg['board_business'],before['board_business'])

    def test_original_apply_helpers_and_close_private_pin_guards_retained(self):
        original=remote_from('listening_entry_fix/apply_closed_revision.py',APPLY_SHA)
        funcs=lambda raw:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(funcs(original),funcs(self.remote))
        for line in (
            " fcntl.flock(publication,fcntl.LOCK_EX|fcntl.LOCK_NB)",
            " assert unit['MainPID']=='0' and unit['ActiveState']=='inactive' and unit['SendSIGKILL']=='no' and unit['TimeoutStopUSec']=='infinity' and not unit['Job']",
            " journal=json.loads(read(control/'state.json'));assert journal['phase']=='NORMAL_CLOSED' and journal['guard_removed'] is False and journal['active_root']==str(root)",
            " for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)",
            " private=Path(cfg['board_business']['private_root']);assert private==Path('/home/root/.local/share/aura-board-business')",
            " proof=verify_production_bootstrap(private,cfg['board_business']['bootstrap_receipt'],cfg['board_business']['bootstrap_receipt_sha256']);assert proof['profiles_migration_verified'] is True",
            "  fcntl.flock(writer,fcntl.LOCK_EX|fcntl.LOCK_NB)"):
            self.assertIn(line,original);self.assertIn(line,self.remote)

    def test_publisher_only_source_function_changed_and_native_gate_not_removed(self):
        original=remote_from('production_business_acceptance/publish_business_ui.py',PUBLISH_SHA)
        revised=publish.build_remote()
        funcs=lambda raw:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        old,new=funcs(original),funcs(revised)
        self.assertEqual(set(old),set(new))
        self.assertEqual([n for n in old if old[n]!=new[n]],['source'])
        self.assertIn("SPEC.get('native_library_sha256')=='"+NEW_NATIVE+"'",revised)
        self.assertIn("cfg['component_sha256']['tools/libaura_yuki.so']==SPEC['native_library_sha256']",revised)
        self.assertIn("assert ACTION in ('start','ready')",revised)


if __name__=='__main__':unittest.main(verbosity=2)
