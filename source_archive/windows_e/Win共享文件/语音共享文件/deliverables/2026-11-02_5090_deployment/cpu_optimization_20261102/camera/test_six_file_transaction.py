"""Pure local interruption tests; never invoke the target executor/guard."""
import copy,hashlib,importlib.util,json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('camera_tx_template',HERE/'six_file_transaction_template.py')
tx=importlib.util.module_from_spec(spec);spec.loader.exec_module(tx)
WORK=HERE/'transaction_test_workspace';WORK.mkdir(exist_ok=True)

class Interrupted(RuntimeError):pass

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='generated-six-files-',dir=WORK)
        self.root=Path(self.tmp.name).resolve();self.assertTrue(self.root.is_relative_to(WORK.resolve()))
        self.targets=self.root/'targets';self.targets.mkdir()
        self.payload=self.root/'payload';self.payload.mkdir();self.backup=self.root/'backup'
        self.records=[]
        for index,name in enumerate(tx.NAMES):
            target=self.targets/name;payload=self.payload/name
            before=('before-'+name).encode();after=('after-'+name).encode()
            target.write_bytes(before);payload.write_bytes(after)
            self.records.append({'name':name,'target':str(target),'payload':str(payload),
                'before_sha256':tx.digest(before),'after_sha256':tx.digest(after)})
    def tearDown(self):
        # Only this generated directory is recursively removed by TemporaryDirectory.
        self.assertTrue(self.root.is_relative_to(WORK.resolve()))
        self.assertTrue(self.root.name.startswith('generated-six-files-'))
        self.tmp.cleanup()
    def instance(self,fault=None):
        return tx.SixFileTransaction(self.records,self.backup,lambda:None,lambda:None,
            fault=fault,directory_sync=lambda path:None)
    def assert_before(self):
        for row in self.records:self.assertEqual(tx.digest(Path(row['target']).read_bytes()),row['before_sha256'])
    def assert_after(self):
        for row in self.records:self.assertEqual(tx.digest(Path(row['target']).read_bytes()),row['after_sha256'])

    def test_normal_commit_preserves_all_original_backups(self):
        obj=self.instance();obj.prepare();self.assert_before();obj.commit();self.assert_after()
        for index,row in enumerate(self.records):self.assertEqual(tx.digest((self.backup/('before-%02d.bin'%index)).read_bytes()),row['before_sha256'])

    def test_interrupt_before_all_backups_never_changes_targets(self):
        def fault(phase,index):
            if phase=='after_backup' and index==2:raise Interrupted()
        with self.assertRaises(Interrupted):self.instance(fault).prepare()
        self.assert_before();self.assertFalse((self.backup/'PLAN.json').exists())
        with self.assertRaises(FileNotFoundError):self.instance().commit(recover=True)

    def test_interrupt_after_third_replace_explicit_known_byte_recovery(self):
        def fault(phase,index):
            if phase=='after_replace' and index==2:raise Interrupted()
        obj=self.instance(fault);obj.prepare()
        original=[(self.backup/('before-%02d.bin'%i)).read_bytes() for i in range(6)]
        with self.assertRaises(Interrupted):obj.commit()
        for index,row in enumerate(self.records):
            wanted=row['after_sha256'] if index<=2 else row['before_sha256']
            self.assertEqual(tx.digest(Path(row['target']).read_bytes()),wanted)
        self.instance().commit(recover=True);self.assert_after()
        self.assertEqual(original,[(self.backup/('before-%02d.bin'%i)).read_bytes() for i in range(6)])

    def test_interrupted_staging_can_recreate_only_absent_known_stages(self):
        def fault(phase,index):
            if phase=='after_stage' and index==0:raise Interrupted()
        with self.assertRaises(Interrupted):self.instance(fault).prepare()
        self.assert_before();self.instance().commit(recover=True);self.assert_after()

    def test_unknown_target_before_prepare_is_not_overwritten(self):
        foreign=Path(self.records[2]['target']);foreign.write_bytes(b'unknown-current-bytes')
        with self.assertRaises(RuntimeError):self.instance().prepare()
        self.assertEqual(foreign.read_bytes(),b'unknown-current-bytes');self.assertFalse(self.backup.exists())

    def test_mid_commit_unknown_writer_is_preserved_and_recovery_refuses(self):
        foreign=Path(self.records[3]['target'])
        def fault(phase,index):
            if phase=='after_replace' and index==1:foreign.write_bytes(b'unknown-noncooperating-writer')
        obj=self.instance(fault);obj.prepare()
        with self.assertRaises(RuntimeError):obj.commit()
        snapshot={row['target']:Path(row['target']).read_bytes() for row in self.records}
        with self.assertRaises(RuntimeError):self.instance().commit(recover=True)
        self.assertEqual(snapshot,{row['target']:Path(row['target']).read_bytes() for row in self.records})
        self.assertEqual(foreign.read_bytes(),b'unknown-noncooperating-writer')

    def test_unknown_staged_bytes_are_never_reused_or_overwritten(self):
        obj=self.instance();obj.prepare();stage=Path(obj.plan['files'][0]['stage']);stage.write_bytes(b'unknown-stage')
        with self.assertRaises(RuntimeError):obj.commit()
        self.assert_before()
        with self.assertRaises(RuntimeError):self.instance().commit(recover=True)
        self.assertEqual(stage.read_bytes(),b'unknown-stage');self.assert_before()

    def test_rollback_uses_original_code_with_new_fresh_seed_and_consistent_meta(self):
        original={name:('original-'+name).encode() for name in tx.NAMES}
        original['ui_camera_service.py']=(HERE/'baseline/9d714b9bd00e__ui_camera_service.py').read_bytes()
        config={'native_execution':{'checkpoint_output':'/isolated-only/checkpoint.json',
            'seed':{'path':'/isolated-only/checkpoint.json','sha256':'c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471'},
            'source_unit_sha256':'unchanged-C-unit','source_manifest_sha256':'unchanged-original-Python-manifest'},'capture_fps':30}
        original['board_camera_ui.proposed.json']=tx.encode(config)
        meta={'candidate_config':'/isolated-only/config.json','candidate_ui_sha256':tx.UI_ORIGINAL,
            'protected':{'/isolated-only/config.json':tx.digest(original['board_camera_ui.proposed.json'])}}
        original['meta.json']=tx.encode(meta)
        fresh={'path':'/isolated-only/checkpoint.json','sha256':'a'*64}
        result=tx.safe_rollback_payload(original,fresh);new_config=json.loads(result['board_camera_ui.proposed.json'])
        self.assertEqual(new_config['native_execution']['seed'],fresh)
        self.assertNotEqual(result['board_camera_ui.proposed.json'],original['board_camera_ui.proposed.json'])
        self.assertEqual(json.loads(result['meta.json'])['protected'][meta['candidate_config']],tx.digest(result['board_camera_ui.proposed.json']))
        for name in tx.NAMES:
            if name not in ('meta.json','board_camera_ui.proposed.json'):self.assertEqual(result[name],original[name])
        self.assertEqual(config['native_execution']['seed']['sha256'],'c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471')
        with self.assertRaises(RuntimeError):tx.safe_rollback_payload(original,config['native_execution']['seed'])

    def test_root_attestation_identity_binds_target_seed_and_source_hashes(self):
        contract={'files':self.records,'expected':{'boot_id':'isolated-test-boot'},
            'fresh_checkpoint':{'path':'/isolated-only/checkpoint.json','sha256':'a'*64},
            'root_validation_receipt':{'path':'/isolated-only/receipt.json','sha256':'b'*64}}
        identity=tx.contract_plan_identity(contract)
        updated=copy.deepcopy(contract);updated['root_validation_receipt']['sha256']='c'*64
        self.assertEqual(tx.contract_plan_identity(updated),identity)
        updated=copy.deepcopy(contract);updated['fresh_checkpoint']['sha256']='c'*64
        self.assertNotEqual(tx.contract_plan_identity(updated),identity)
        updated=copy.deepcopy(contract);updated['files'][0]['after_sha256']='c'*64
        self.assertNotEqual(tx.contract_plan_identity(updated),identity)

    def test_rollback_before_must_be_known_prior_bytes_not_merely_a_new_hash(self):
        obj=self.instance();obj.prepare()
        original={row['name']:(self.backup/('before-%02d.bin'%index)).read_bytes() for index,row in enumerate(self.records)}
        plan=self.backup/'PLAN.json'
        contract={'direction':'rollback','rollback_predecessor_plan':{'path':str(plan),'sha256':tx.digest(plan.read_bytes())},
            'files':copy.deepcopy(self.records)}
        tx.check_known_before(contract,original)
        contract['files'][2]['before_sha256']='c'*64
        with self.assertRaises(RuntimeError):tx.check_known_before(contract,original)

if __name__=='__main__':unittest.main(verbosity=2)
