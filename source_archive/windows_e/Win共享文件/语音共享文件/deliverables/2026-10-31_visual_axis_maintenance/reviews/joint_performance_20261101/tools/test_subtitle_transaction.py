"""Local fail-closed transaction contract checks; no device connection or process control."""
from pathlib import Path
import ast
import base64
import copy
import hashlib
import importlib.util
import itertools
import json
import sys
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
PKG=HERE/'package/subtitle_receipt'
load=lambda name:json.loads((PKG/name).read_bytes())
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def need(value,code):
    if not value:raise ValueError(code)


class TransactionContractTests(unittest.TestCase):
    def setUp(self):
        self.overlay=module(PKG/'single_projection_overlay.py','public_transaction_contract')
        self.overlay.need=need
        self.overlay.Path=Path  # supplied by the frozen definitions in the real operator source

    def test_frozen_code_and_payload_closure(self):
        manifest=load('BUNDLE_MANIFEST.json')
        for name,pin in manifest['files'].items():
            raw=(PKG/name).read_bytes();self.assertEqual(sha(raw),pin)
            if name.endswith('.py'):ast.parse(raw.decode())

    def test_exactly_one_of_380_sources_and_no_configuration_changes(self):
        old,new=load('base_spec.json'),load('candidate_spec.json')
        self.assertEqual(len(new['component_sha256']),380)
        self.assertEqual([k for k in old['component_sha256'] if old['component_sha256'][k]!=new['component_sha256'][k]],
                         ['tools/production_memory_presentation.py'])
        self.assertEqual(old['configuration_sha256'],new['configuration_sha256'])
        self.assertEqual(old['camera_owner'],new['camera_owner'])
        a,b=load('base_startup.json'),load('candidate_startup.json')
        a.pop('component_sha256');b.pop('component_sha256');self.assertEqual(a,b)

    def test_manifest_file_changes_only_source_and_startup(self):
        old,new=load('base_manifest.json'),load('candidate_manifest.json')
        changed={k for k in old['files'] if old['files'][k]!=new['files'][k]}
        self.assertEqual(changed,{'runtime/aura/tools/production_memory_presentation.py','startup/config.json'})
        self.assertEqual(new['files']['startup/config.json']['sha256'],sha((PKG/'candidate_startup.json').read_bytes()))

    def test_rollback_restores_all_three_exact_old_bytes(self):
        forward,rollback=load('forward_plan.json'),load('rollback_plan.json')
        expected={'production_memory_presentation.py':PKG/'rollback/production_memory_presentation.py',
                  'production-source-manifest.json':PKG/'base_manifest.json','startup-config.json':PKG/'base_startup.json'}
        for name,row in rollback['targets'].items():
            self.assertEqual(base64.b64decode(row['new_base64']),expected[name].read_bytes())
            self.assertEqual(row['new_sha256'],forward['targets'][name]['old_sha256'])
            self.assertEqual(row['old_sha256'],forward['targets'][name]['new_sha256'])

    def test_forward_initial_mixed_or_unknown_payload_refused(self):
        o=self.overlay;o.PLAN=load('forward_plan.json')
        current={k:v['old_sha256'] for k,v in o.PLAN['targets'].items()};o.validate_snapshot(current,first_apply=True)
        key=next(iter(current));current[key]=o.PLAN['targets'][key]['new_sha256']
        with self.assertRaises(ValueError):o.validate_snapshot(current,first_apply=True)
        o.validate_snapshot(current,first_apply=False)
        current[key]='0'*64
        with self.assertRaises(ValueError):o.validate_snapshot(current,first_apply=False)

    def test_partial_rollback_only_accepts_known_old_new_combinations(self):
        o=self.overlay;o.PLAN=load('rollback_plan.json');keys=list(o.PLAN['targets'])
        for bits in itertools.product((False,True),repeat=3):
            current={k:o.PLAN['targets'][k]['new_sha256' if bit else 'old_sha256'] for k,bit in zip(keys,bits)}
            o.validate_snapshot(current,first_apply=True)
        current[keys[0]]='f'*64
        with self.assertRaises(ValueError):o.validate_snapshot(current,first_apply=True)

    def configure_parent_fixture(self,direction):
        o=self.overlay;o.PLAN=load(direction+'_plan.json');journal={};files={}
        for key,row in o.PLAN['parent_transactions'].items():
            raw=json.dumps({row['field']:row['spec_sha256']}).encode();path=str(Path(row['stage'])/'transaction.json')
            files[path]=raw;journal[key]=dict(state='APPLIED',stage=row['stage'],transaction_sha256=sha(raw))
        def read(path,pin):
            raw=files[str(path)];need(sha(raw)==pin,'parent_file_changed');return raw
        o.c=NS(read=read,parse=json.loads)
        return o,journal

    def test_ancestor_marker_cannot_be_missing_changed_or_unapplied(self):
        o,journal=self.configure_parent_fixture('forward');o.parent_transactions(journal)
        key=next(iter(journal))
        for update in ({'state':'INTENT'},{'stage':'/other'},{'transaction_sha256':'0'*64}):
            bad=copy.deepcopy(journal);bad[key].update(update)
            with self.assertRaises((ValueError,KeyError)):o.parent_transactions(bad)
        bad=copy.deepcopy(journal);bad.pop(key)
        with self.assertRaises(ValueError):o.parent_transactions(bad)

    def test_rollback_accepts_intent_of_exact_forward_but_preserves_ancestors(self):
        o,journal=self.configure_parent_fixture('rollback')
        journal['subtitle_submit_receipt']['state']='INTENT';o.parent_transactions(journal)
        journal['axis_direction_rebind']['state']='INTENT'
        with self.assertRaises(ValueError):o.parent_transactions(journal)

    def test_mutating_operator_action_needs_exact_internal_review_before_ssh(self):
        runner=module(HERE/'tools/publish_subtitle_receipt.py','public_operator_gate_contract')
        with patch.object(runner,'ssh',side_effect=AssertionError('SSH must not be reached')) as transport:
            with patch.object(sys,'argv',['publisher','forward','guard']):
                with self.assertRaisesRegex(AssertionError,'internal local review'):runner.main()
            transport.assert_not_called()


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(TransactionContractTests))
    proof=dict(schema='aura-local-single-projection-transaction-contract-1',tests=result.testsRun,
               failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),device_access=False,
               bundle_manifest_sha256=sha((PKG/'BUNDLE_MANIFEST.json').read_bytes()))
    target=HERE/'evidence'/('subtitle_receipt_local_transaction_tests_'+str(time.time_ns())+'.json')
    with target.open('x',encoding='utf-8') as f:json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps(proof));raise SystemExit(0 if result.wasSuccessful() else 1)
