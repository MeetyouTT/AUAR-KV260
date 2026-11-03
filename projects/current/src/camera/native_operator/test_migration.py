import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE));sys.path.insert(0,'/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
import identity_recovery as m
from board.vision import native_startup as ns,dpu_sface,native_binding

class MigrationTests(unittest.TestCase):
    def run_case(self,unit='old',bad_hash=False):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'checkpoint.json';seed={'primary_calls':456,'primary_period_overruns':18,
                'recovery':[{'faults':7,'attempts':6,'recoveries':6},{'faults':3,'attempts':2,'recoveries':2}]}
            p.write_text(json.dumps({'source_unit_sha256':unit,'seed':seed}))
            settings=dict(old_library='old.so',old_library_sha256='oldhash',library='new.so',library_sha256='newhash',
                predecessor_unit_sha256='old',unit_sha256='new',request_boot_id='boot')
            config={'native_execution':dict(library='old.so',library_sha256='oldhash',source_unit_sha256='old',
                seed={'path':str(p),'sha256':'wrong' if bad_hash else hashlib.sha256(p.read_bytes()).hexdigest()})}
            def exact_preflight(cfg,**kwargs):
                self.assertEqual(cfg['native_execution']['library'],'new.so')
                self.assertEqual(cfg['native_execution']['source_unit_sha256'],unit)
                return {'seed':copy.deepcopy(seed),'document':{'source_unit_sha256':unit}}
            prior=(ns.preflight,ns.attach,native_binding.NativeContext.__init__,dpu_sface.DpuSFace.__init__,dpu_sface.DpuSFace.feature,dpu_sface.DpuSFace.close)
            try:
                ns.preflight=exact_preflight;m.install(settings,root)
                if unit=='unexpected' or bad_hash:
                    with self.assertRaises(RuntimeError):ns.preflight(config,boot_id='boot',root=root)
                else:
                    loaded=ns.preflight(config,boot_id='boot',root=root)
                    self.assertEqual(loaded['seed'],seed)
                    self.assertEqual(config['native_execution']['source_unit_sha256'],'new')
                    self.assertFalse(list(root.glob('operator-consumed-*')))
            finally:
                ns.preflight,ns.attach,native_binding.NativeContext.__init__,dpu_sface.DpuSFace.__init__,dpu_sface.DpuSFace.feature,dpu_sface.DpuSFace.close=prior
    def test_explicit_old_unit_preserves_the_whole_seed(self):self.run_case()
    def test_restart_from_new_unit_preserves_whole_seed(self):self.run_case('new')
    def test_other_unit_is_rejected(self):self.run_case('unexpected')
    def test_changed_checkpoint_is_rejected(self):self.run_case(bad_hash=True)

if __name__=='__main__':unittest.main()
