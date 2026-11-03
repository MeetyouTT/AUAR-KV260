import ast
from pathlib import Path
import unittest
node=next(n for n in ast.parse((Path(__file__).resolve().parents[1]/'resource_snapshot.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='inactive_collector')
env={};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'stat-gate','exec'),env)
class ResourceGateTests(unittest.TestCase):
    def gate(self,left=200,right=200,frames=15,duration=1.5,pid=1):
        return env['inactive_collector']({'raw':[left],'mono':0},{'raw':[right],'mono':duration},
            {'pid':1,'detected_frames':0},{'pid':pid,'detected_frames':frames})
    def test_stopped_retained_total_is_allowed(self):self.assertTrue(self.gate())
    def test_advancing_counter_is_rejected(self):self.assertFalse(self.gate(right=215))
    def test_no_real_dpu_progress_does_not_prove_inactivity(self):self.assertFalse(self.gate(frames=0))
    def test_short_or_cross_process_sample_is_rejected(self):
        self.assertFalse(self.gate(duration=.5));self.assertFalse(self.gate(pid=2))
if __name__=='__main__':unittest.main(verbosity=2)
