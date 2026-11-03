"""Execute the actual rollback program/finalizer against temporary files only."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_sface_retry_ab_20261022_v2.py')
tree=ast.parse(SOURCE.read_text())
definition=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='rollback_program')
namespace={};exec(compile(ast.Module(body=[definition],type_ignores=[]),str(SOURCE),'exec'),namespace)
run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_ab')
main_try=next(n for n in run.body if isinstance(n,ast.Try) and n.finalbody)
finalizer=compile(ast.Module(body=copy.deepcopy(main_try.finalbody),type_ignores=[]),str(SOURCE),'exec')


class RollbackTests(unittest.TestCase):
    def exercise(self,current,*,change_during_stop=False):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);unit=root/'camera.service'
            for name,value in [('original',b'original'),('A',b'variant A'),('B',b'variant B')]:
                (root/('camera.service.'+name)).write_bytes(value)
            unit.write_bytes(current);calls=[]
            script=namespace['rollback_program']({}).replace('ROOT_VALUE',repr(str(root)))
            script=script.replace("'/etc/systemd/system/aura-camera-ui.service'",repr(str(unit)))
            def command(args,**kwargs):
                calls.append(args)
                if change_during_stop and args[1]=='stop':unit.write_bytes(b'unrelated later unit')
            with patch('subprocess.run',side_effect=command):
                rollback_namespace={}
                try:
                    if current not in (b'original',b'variant A',b'variant B') or change_during_stop:
                        with self.assertRaises(AssertionError):exec(compile(script,'actual-rollback-test','exec'),rollback_namespace)
                        self.assertNotEqual(unit.read_bytes(),b'original')
                    else:
                        exec(compile(script,'actual-rollback-test','exec'),rollback_namespace)
                        self.assertEqual(unit.read_bytes(),b'original')
                        self.assertEqual([x[1] for x in calls],['stop','daemon-reload','start'])
                finally:
                    # The real rollback owns a process lifetime. This in-process
                    # harness closes that process-owned fd after each execution.
                    if 'lock' in rollback_namespace:rollback_namespace['lock'].close()
            return calls
    def test_original_unit_is_valid(self):self.exercise(b'original')
    def test_variant_a_restores(self):self.exercise(b'variant A')
    def test_variant_b_restores(self):self.exercise(b'variant B')
    def test_unrelated_unit_is_never_stopped_or_overwritten(self):self.assertFalse(self.exercise(b'unrelated'))
    def test_unit_changed_during_stop_is_not_overwritten(self):
        self.assertEqual(len(self.exercise(b'variant A',change_during_stop=True)),1)


class FinalizerTests(unittest.TestCase):
    def execute(self,current,*,fail_restore=False):
        calls=[];report={}
        def restore():
            calls.append('restore')
            if fail_restore:raise RuntimeError('synthetic failed restoration')
            return {'pid':123}
        values=dict(report=report,UNIT=SimpleNamespace(read_bytes=lambda:current),original=b'original',
            pinned=lambda:calls.append('audit') or {'pid':123},restore=restore,
            preserved=lambda:calls.append('protected-audit'),save=lambda:None,
            service=lambda *args:calls.append(args),timer='owned-timer',armed=True)
        exec(finalizer,values)
        return report,calls
    def test_already_original_is_audited_without_another_restart(self):
        report,calls=self.execute(b'original')
        self.assertNotIn('restore',calls);self.assertIn('audit',calls)
        self.assertTrue(report['rollback_verified']);self.assertFalse(report['rollback_timer_left_armed'])
    def test_candidate_restores_once(self):
        report,calls=self.execute(b'variant A')
        self.assertEqual(calls.count('restore'),1);self.assertTrue(report['rollback_verified'])
    def test_failed_restoration_keeps_independent_timer_armed(self):
        report,calls=self.execute(b'variant B',fail_restore=True)
        self.assertFalse(report['rollback_verified']);self.assertTrue(report['rollback_timer_left_armed'])
        self.assertNotIn(('stop','owned-timer.timer'),calls)


if __name__=='__main__':unittest.main(verbosity=2)
