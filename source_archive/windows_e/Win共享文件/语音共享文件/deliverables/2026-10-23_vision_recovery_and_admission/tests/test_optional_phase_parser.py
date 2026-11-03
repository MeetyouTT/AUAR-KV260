"""Pure parser/opcode checks without importing the board-only controller."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'trace_optional_phases.py').read_text())
context={'re':re,'h':SimpleNamespace(GROUP='fixture',NAMES=('native_enter','native_return','restore_enter','restore_return'))}
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse')
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'phase-parser','exec'),context)

def line(tid,stamp,name):return 'python-'+str(tid)+' [001] .... '+stamp+': '+name+': (0x0)'

class OptionalParserTests(unittest.TestCase):
    def test_interleaved_threads_pair_independently(self):
        rows=[]
        for name,stamp in zip(context['h'].NAMES,('1.000001','1.004001','1.004003','1.024003')):
            rows.append(line(10,stamp,name));rows.append(line(11,stamp,name))
        result=context['parse']('\n'.join(rows),{10,11})
        self.assertEqual(len(result['cycles']),2)
        self.assertEqual(result['cycles'][0]['native_ms'],4.)
        self.assertEqual(result['cycles'][0]['restore_ms'],20.)
        self.assertEqual(result['fraction_digits'],[6])

    def test_unrecorded_thread_or_reversed_clock_rejects(self):
        with self.assertRaises(AssertionError):context['parse'](line(12,'1.000000','native_enter'),{10})
        rows=[line(10,t,n) for n,t in zip(context['h'].NAMES,('1.000004','1.000003','1.000005','1.000006'))]
        with self.assertRaises(AssertionError):context['parse']('\n'.join(rows),{10})

    def test_partial_and_missing_phase_never_form_fake_call(self):
        result=context['parse']('\n'.join(line(10,'1.000001',n) for n in ('native_return','native_enter','restore_enter','restore_return')),{10})
        self.assertFalse(result['cycles']);self.assertGreater(result['partial_sequences'],0)

    @unittest.skipUnless(Path('/home/ghmd/aura-native-wait-20261023/exact-runtime/vart.so').is_file(),
                         'Exact board ELF stays private; binary check requires its verified local copy')
    def test_exact_elf_opcodes_still_match(self):
        raw=Path('/home/ghmd/aura-native-wait-20261023/exact-runtime/vart.so').read_bytes()
        assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='POINTS' for t in n.targets))
        for off,opcode in ast.literal_eval(assignment.value).values():
            self.assertEqual(int.from_bytes(raw[off:off+4],'little'),opcode)

if __name__=='__main__':unittest.main(verbosity=2)
