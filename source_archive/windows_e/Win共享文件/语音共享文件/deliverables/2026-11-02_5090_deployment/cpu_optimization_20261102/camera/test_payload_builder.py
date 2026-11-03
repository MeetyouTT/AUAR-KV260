"""In-memory technical JSON fixtures; no production checkpoint is fabricated."""
import copy,hashlib,importlib.util,json
from pathlib import Path
import unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('offline_camera_payload',HERE/'prepare_transaction_payload.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def raw(value):return (json.dumps(value,indent=2)+'\n').encode()
def sha(value):return hashlib.sha256(value).hexdigest()

class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.original_old=copy.deepcopy(builder.OLD)
        discovery=json.loads((HERE/'SOURCE_DISCOVERY.json').read_text())['board_result']
        meta=copy.deepcopy(discovery['meta']);prefix=builder.CANDIDATE_ROOT+'/aura/'
        files={key[len(prefix):]:value for key,value in meta['protected'].items() if key.startswith(prefix) and key.endswith('.py')}
        self.assertEqual(len(files),222)
        manifest={'schema':'aura-native-python-source-2','root':builder.CANDIDATE_ROOT+'/aura','files':files}
        manifest_raw=raw(manifest)
        config=copy.deepcopy(discovery['config'])
        config['identity']={'enabled':True,'config':'/isolated-test-only/identity.json'}
        native=copy.deepcopy(json.loads((HERE/'DEPLOYMENT_CONTRACT_DISCOVERY.json').read_text())['native_execution'])
        native['source_manifest_sha256']=sha(manifest_raw)
        config['native_execution']=native;config_raw=raw(config)
        runtime_raw=raw(json.loads((HERE/'DEPLOYMENT_CONTRACT_DISCOVERY.json').read_text())['runtime_manifest'])
        meta['protected'][builder.TARGETS['camera-python-manifest.json']]=sha(manifest_raw)
        meta['protected'][builder.TARGETS['board_camera_ui.proposed.json']]=sha(config_raw)
        self.inputs={'ui_camera_service.py':(HERE/'baseline/9d714b9bd00e__ui_camera_service.py').read_bytes(),
            'native_entry_pan_face_v5.py':(HERE/'baseline/288f6b7b5670__native_entry_pan_face_v5.py').read_bytes(),
            'camera-python-manifest.json':manifest_raw,'board_camera_ui.proposed.json':config_raw,
            'meta.json':raw(meta),'runtime-manifest.json':runtime_raw}
        # Replace only fixture SHA expectations in this isolated test module.
        # Production builder source and pinned release constants stay unchanged.
        builder.OLD.update({name:sha(value) for name,value in self.inputs.items() if name!='meta.json'})
        self.meta_sha=sha(self.inputs['meta.json'])
        self.fresh_path=native['checkpoint_output']
        self.synthetic_only_sha='a'*64
    def tearDown(self):builder.OLD=self.original_old

    def prepare(self,inputs=None,meta_sha=None,path=None,digest=None):
        return builder.prepare(inputs or self.inputs,meta_sha or self.meta_sha,path or self.fresh_path,digest or self.synthetic_only_sha)

    def test_six_file_plan_preserves_every_unrelated_setting(self):
        payload,plan=self.prepare()
        self.assertEqual(set(payload),set(builder.TARGETS));self.assertFalse(plan['board_actions_performed'])
        old_manifest=json.loads(self.inputs['camera-python-manifest.json']);new_manifest=json.loads(payload['camera-python-manifest.json'])
        self.assertEqual(len(new_manifest['files']),222)
        changed={key for key in old_manifest['files'] if old_manifest['files'][key]!=new_manifest['files'][key]}
        self.assertEqual(changed,{'board/vision/ui_camera_service.py'})
        old_config=json.loads(self.inputs['board_camera_ui.proposed.json']);new_config=json.loads(payload['board_camera_ui.proposed.json'])
        self.assertEqual({k:v for k,v in old_config.items() if k!='native_execution'},{k:v for k,v in new_config.items() if k!='native_execution'})
        for key,value in old_config['native_execution'].items():
            if key not in ('source_manifest_sha256','seed'):self.assertEqual(new_config['native_execution'][key],value,key)
        old_meta=json.loads(self.inputs['meta.json']);new_meta=json.loads(payload['meta.json'])
        changed={key for key in old_meta['protected'] if old_meta['protected'][key]!=new_meta['protected'][key]}
        self.assertEqual(changed,{builder.TARGETS[name] for name in ('ui_camera_service.py','camera-python-manifest.json','board_camera_ui.proposed.json')})
        for key,value in old_meta.items():
            if key not in ('candidate_ui_sha256','protected'):self.assertEqual(new_meta[key],value,key)
        old_runtime=json.loads(self.inputs['runtime-manifest.json']);new_runtime=json.loads(payload['runtime-manifest.json'])
        changed={key for key in old_runtime['files'] if old_runtime['files'][key]!=new_runtime['files'][key]}
        self.assertEqual(changed,{builder.TARGETS['native_entry_pan_face_v5.py']})
        self.assertEqual(new_runtime['files'][builder.OP+'/source-manifest.json'],builder.UNIT)
        self.assertEqual(plan['checkpoint_output_unchanged'],self.fresh_path)
        self.assertFalse(plan['service_argv_changed'])

    def test_already_consumed_old_final_sha_rejected(self):
        with self.assertRaises(AssertionError):self.prepare(digest='c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471')

    def test_foreign_checkpoint_output_rejected(self):
        with self.assertRaises(AssertionError):self.prepare(path='/isolated-test-only/foreign-checkpoint.json')

    def test_unexpected_source_and_meta_bytes_rejected(self):
        changed=dict(self.inputs);changed['ui_camera_service.py']+=b'\n'
        with self.assertRaises(AssertionError):self.prepare(inputs=changed)
        with self.assertRaises(AssertionError):self.prepare(meta_sha='b'*64)

if __name__=='__main__':unittest.main(verbosity=2)
