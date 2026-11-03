"""Review generated trial wiring without loading a model or a board device."""
import ast,base64,gzip,hashlib,importlib.util
from pathlib import Path
import tempfile
import unittest

TRIAL=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_coordinated_recovery50_r2_20261023.py')
PARENT=TRIAL.with_name('board_recovery50_live_r2_20261023.py')
ROOT=Path(__file__).resolve().parent


def assignments(tree,names):
    return {n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
            and isinstance(n.targets[0],ast.Name) and n.targets[0].id in names}


class GeneratedTests(unittest.TestCase):
    def setUp(self):
        self.text=TRIAL.read_text();self.tree=ast.parse(self.text)
    def test_model_recovery_and_gil_payloads_are_exactly_inherited(self):
        names={'RETRY_PAYLOAD','RETRY_HASHES','RETRY_WRAPPER','RETRY_WRAPPER_SHA'}
        self.assertEqual(assignments(self.tree,names),assignments(ast.parse(PARENT.read_text()),names))
    def test_handoff_payload_is_exact_board_baseline_version(self):
        values=assignments(self.tree,{'HANDOFF_SHA','HANDOFF_DATA'})
        raw=gzip.decompress(base64.b64decode(values['HANDOFF_DATA']))
        self.assertEqual(raw,(ROOT/'handoff.py').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),values['HANDOFF_SHA'])
    def test_transition_happens_before_sampling_and_guard_remains_independent(self):
        self.assertLess(self.text.index("coordination.transition(coordinator,'candidate')"),
                        self.text.index('for index in range(25)'))
        self.assertIn("--on-active=600s",self.text)
        self.assertIn('RuntimeMaxSec=540',self.text)
        self.assertIn("str(folder/'rollback.py')],timeout=300",self.text)
        self.assertIn("coordinator.verify();assert coordinator.ready('original')",self.text)
    def test_gui_pid_exception_has_equivalent_config_health_and_xserver_checks(self):
        self.assertIn("unit_pids['aura-avatar-ui.service']=service",self.text)
        self.assertIn("if name!='aura-avatar-ui.service':assert service",self.text)
        self.assertIn("report['protected_audio_source_verified']=True",self.text)
        self.assertIn("for p,expected in protected.items():assert digest(p)==expected",self.text)
    def test_prepare_handoff_executes_all_dependencies_in_isolated_fixture(self):
        spec=importlib.util.spec_from_file_location('_offline_generated_trial',TRIAL)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        stub=b'''class BoardOps:
 def __init__(self,folder):self.folder=folder;self.meta={'unit_hashes':{},'runtimes':{}}
 def capture(self,wrapper):self.meta['wrapper']=str(wrapper)
 def save_meta(self):pass
'''
        module.HANDOFF_DATA=base64.b64encode(gzip.compress(stub)).decode()
        module.HANDOFF_SHA=hashlib.sha256(stub).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            module.Path=lambda value:tmp/'session-parent' if value=='/home/root/aura-coordinated-switch-20261023' else Path(value)
            ops,protocol=module.prepare_handoff(tmp/'wrapper.py',b'candidate unit',tmp/'candidate')
            self.assertEqual((ops.folder/'camera.candidate').read_bytes(),b'candidate unit')
            self.assertEqual(ops.meta['runtimes']['candidate'],str(tmp/'candidate'))
            self.assertEqual(ops.meta['unit_hashes']['candidate'],hashlib.sha256(b'candidate unit').hexdigest())
    def test_generated_restore_pins_module_and_uses_coordinated_protocol(self):
        spec=importlib.util.spec_from_file_location('_offline_restore_source',TRIAL)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        code=m.rollback_source(Path('/home/root/aura-coordinated-switch-20261023/test'))
        ast.parse(code)
        self.assertIn(m.HANDOFF_SHA,code)
        self.assertIn('m.BoardOps(root).restore()',code)
        self.assertNotIn("systemctl",code)


if __name__=='__main__':unittest.main()
