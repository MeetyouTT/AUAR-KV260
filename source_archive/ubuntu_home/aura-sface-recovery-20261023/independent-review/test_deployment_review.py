"""Controller pure-function checks only; no imports with systemctl side effects."""
import ast
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'deploy_control.py'
tree=ast.parse(SOURCE.read_text())
context={'Path':Path,'PARENT_UNIT_SHA':'fixture-sha'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('dropin','override_path','effective_marker')]
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(SOURCE),'exec'),context)


class DeploymentReviewTests(unittest.TestCase):
    def test_dropin_resets_exec_and_preserves_only_service_command_fields(self):
        raw=b'[Unit]\nDescription=fixture\n[Service]\nType=simple\nWorkingDirectory=/parent\nExecStart=/python /parent/runtime_entry.py /parent/aura/entry.py\nRestart=on-failure\n[Install]\nWantedBy=multi-user.target\n'
        result=context['dropin'](raw)
        self.assertEqual(result,b'[Service]\nExecStart=\nWorkingDirectory=/parent\nExecStart=/python /parent/runtime_entry.py /parent/aura/entry.py\n')
        self.assertNotIn(b'Restart=',result)
        self.assertNotIn(b'[Install]',result)

    def test_dropin_rejects_ambiguous_multiple_execs(self):
        with self.assertRaises(AssertionError):
            context['dropin'](b'WorkingDirectory=/parent\nExecStart=/a\nExecStart=/b\n')

    def test_own_override_lives_only_in_runtime_namespace(self):
        value=context['override_path'](Path('/owned/fixture-token'))
        self.assertEqual(value,Path('/run/systemd/system/aura-camera-ui.service.d/zz-aura-sface-recovery-fixture-token.conf'))

    def test_effective_marker_refuses_changed_etc_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=context.copy()
            try:
                context['UNIT']=Path(tmp)/'unit';context['digest']=lambda p:'changed'
                with self.assertRaises(AssertionError):context['effective_marker'](Path(tmp))
            finally:context.clear();context.update(original)

    def test_controller_never_writes_etc_unit(self):
        # Mutations must write owned path, not full persistent unit.
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='atomic_bytes']
        self.assertEqual(len(calls),2)
        for call in calls:
            self.assertIsInstance(call.args[0],ast.Name)
            self.assertEqual(call.args[0].id,'path')
        self.assertNotIn('atomic_bytes(UNIT',SOURCE.read_text())


if __name__=='__main__':unittest.main(verbosity=2)
