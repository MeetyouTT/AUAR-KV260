import ast,os
from pathlib import Path
from types import SimpleNamespace
import unittest
source=Path(__file__).resolve().parents[1]/'trace_wait_sched_nice.py'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='restore_nice')
code=compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'nice-restore','exec')
class NiceRestoreTests(unittest.TestCase):
    def run_restore(self,changed=False):
        rows={'10':{'birth':1,'nice':-5},'11':{'birth':3,'nice':-5},'12':{'birth':4,'nice':-10},'13':{'birth':5,'nice':-5}}
        calls=[]
        def put(kind,tid,value):calls.append((tid,value));rows[str(tid)]['nice']=value
        env={'Path':Path,'birth':lambda pid:99 if changed else 7,'thread_states':lambda pid:rows,
            'TRIAL_NICE':-5,'os':SimpleNamespace(PRIO_PROCESS=0,setpriority=put)}
        exec(code,env)
        result=env['restore_nice']({'nice_pid':os.getpid(),'nice_pid_birth':7,
            'thread_states':{'10':{'birth':1,'nice':0},'11':{'birth':2,'nice':0},'12':{'birth':4,'nice':0}}})
        return result,calls,rows
    def test_restores_owned_priority_and_inherited_new_threads(self):
        result,calls,rows=self.run_restore();self.assertIn((10,0),calls);self.assertIn((13,0),calls)
    def test_reused_thread_or_independent_nice_change_is_not_overwritten(self):
        result,calls,rows=self.run_restore();self.assertNotIn((11,0),calls);self.assertNotIn((12,0),calls)
        self.assertEqual(rows['12']['nice'],-10)
    def test_changed_process_has_no_priority_mutations(self):
        result,calls,rows=self.run_restore(changed=True);self.assertTrue(result['process_changed']);self.assertFalse(calls)
if __name__=='__main__':unittest.main(verbosity=2)
