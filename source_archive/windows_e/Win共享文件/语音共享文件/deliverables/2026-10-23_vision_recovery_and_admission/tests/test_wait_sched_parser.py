import ast
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'trace_wait_sched.py'
tree=ast.parse(SOURCE.read_text());names=('native_enter','native_return','restore_enter','restore_return',
    'wait_enter','wait_native_enter','wait_native_return','wait_cleanup_end')
env={'re':re,'h':SimpleNamespace(NAMES=names,GROUP='fixture')}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('parse','parse_switches')]
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'wait-sched','exec'),env)
def switch(t,prev,state,nextpid):
    return 'python-7 [000] .... '+t+': sched_switch: prev_comm=python prev_pid='+str(prev)+' prev_prio=120 prev_state='+state+' ==> next_comm=python next_pid='+str(nextpid)+' next_prio=120'
def wake(t,pid):return 'python-8 [001] .... '+t+': sched_wakeup: comm=python pid='+str(pid)+' prio=120 target_cpu=000'

class WaitSchedParserTests(unittest.TestCase):
    def test_eight_phase_cycle_splits_native_wait_and_cleanup(self):
        times=('1.000000','1.020000','1.020010','1.020100','1.021000','1.021100','1.021101','1.030000')
        raw='\n'.join('python-7 [000] .... '+t+': '+name+': (0x1)' for t,name in zip(times,names))
        result=env['parse'](raw,{7});self.assertEqual(len(result['cycles']),1)
        c=result['cycles'][0];self.assertEqual(c['wait_native_ms'],.001)
        self.assertEqual(c['wait_cleanup_ms'],8.899);self.assertEqual(c['native_ms'],20.)
    def test_runnable_switch_is_distinct_from_sleep_and_wakeup_queue(self):
        raw='\n'.join([switch('1.000000',7,'R+',8),switch('1.010000',8,'R',7),
            switch('2.000000',7,'S',8),wake('2.002000',7),switch('2.003000',8,'R',7)])
        result=env['parse_switches'](raw,7)
        self.assertEqual(result['off_cpu_intervals'],[[1000000000,1010000000,'R+',1000000000],
            [2000000000,2003000000,'S',2002000000]])
    def test_missing_wakeup_keeps_off_cpu_reason_unknown(self):
        result=env['parse_switches']('\n'.join([switch('1.000000',7,'S',8),switch('1.010000',8,'R',7)]),7)
        self.assertIsNone(result['off_cpu_intervals'][0][3])
    def test_other_threads_do_not_become_target_events(self):
        result=env['parse_switches']('\n'.join([switch('1.000000',8,'S',9),wake('1.001000',8)]),7)
        self.assertEqual(result['scheduler_events'],[])
    @unittest.skipUnless(Path('/home/ghmd/aura-native-wait-20261023/exact-runtime/vart.so').exists(),'Private exact ELF required')
    def test_eight_instruction_words_match_exact_elf(self):
        node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='POINTS' for t in n.targets))
        raw=Path('/home/ghmd/aura-native-wait-20261023/exact-runtime/vart.so').read_bytes()
        for off,word in ast.literal_eval(node.value).values():self.assertEqual(int.from_bytes(raw[off:off+4],'little'),word)
if __name__=='__main__':unittest.main(verbosity=2)
