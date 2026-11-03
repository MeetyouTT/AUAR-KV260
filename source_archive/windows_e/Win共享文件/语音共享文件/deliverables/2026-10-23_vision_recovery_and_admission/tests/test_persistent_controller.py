import ast
from pathlib import Path
import tempfile,unittest
from types import SimpleNamespace

SOURCE=Path(__file__).resolve().parents[1]/'deploy_control.py'
tree=ast.parse(SOURCE.read_text())
env={'Path':Path,'PARENT_UNIT_SHA':'base'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('dropin','override_path','rollback_path','effective_marker')]
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'controller-functions','exec'),env)
rollback_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='rollback')
rollback_code=compile(ast.fix_missing_locations(ast.Module(body=[rollback_node],type_ignores=[])),'rollback','exec')

class PersistentControllerTests(unittest.TestCase):
    def test_persistent_candidate_and_runtime_rollback_are_distinct_owned_files(self):
        a=env['override_path'](Path('/task/token'));b=env['rollback_path'](Path('/task/token'))
        self.assertEqual(a.parent,Path('/etc/systemd/system/aura-camera-ui.service.d'))
        self.assertEqual(b.parent,Path('/run/systemd/system/aura-camera-ui.service.d'))
        self.assertGreater(b.name,a.name)
    def test_parent_dropin_execstart_reset_is_not_treated_as_second_command(self):
        result=env['dropin'](b'[Service]\nExecStart=\nExecStart=/python /entry\nWorkingDirectory=/root\n')
        self.assertEqual(result,b'[Service]\nExecStart=\nExecStart=/python /entry\nWorkingDirectory=/root\n')
    def test_two_real_commands_are_rejected(self):
        with self.assertRaises(AssertionError):env['dropin'](b'ExecStart=/a\nExecStart=/b\nWorkingDirectory=/root\n')
    def test_runtime_rollback_has_marker_priority_without_rewriting_original_unit(self):
        old=dict(env)
        try:
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);a=root/'candidate';b=root/'rollback';a.write_text('candidate');b.write_text('rollback')
                unit=root/'unit';unit.write_text('base')
                env.update(UNIT=unit,digest=lambda p:p.read_text(),override_path=lambda r:a,rollback_path=lambda r:b)
                self.assertEqual(env['effective_marker'](root),'rollback')
                b.unlink();self.assertEqual(env['effective_marker'](root),'candidate')
        finally:env.clear();env.update(old)
    def rollback_fixture(self,folder,*,fenced=False):
        root=Path(folder);persistent=root/'candidate';persistent.write_text('candidate')
        foreign=root/'foreign.conf';foreign.write_text('keep');runtime=root/'runtime'
        unit=root/'unit';unit.write_text('base');(root/'unit.rollback').write_bytes(b'protected')
        calls=[]
        def prop(service,name):
            if name=='ActiveState':return 'active' if fenced and service=='camera' else 'inactive'
            if name=='Result':return 'success'
            if name=='MainPID':return '22'
            raise AssertionError(name)
        g=SimpleNamespace(CAMERA='camera',GUI='gui',prop=prop,pcm_closed=lambda:calls.append('pcm'),
            command=lambda args:calls.append(args))
        helper=SimpleNamespace(start_gui=lambda *a:calls.append('gui-start'),set_page=lambda *a:None,
            restore=lambda *a:{'passed':True})
        ns=dict(env,g=g,UNIT=unit,digest=lambda p:p.read_text(),override_path=lambda r:persistent,
            rollback_path=lambda r:runtime,get_health=lambda:{'dpu_schedule':{'owner_fenced':fenced}},
            stop_services=lambda *a:calls.append('stop'),atomic_bytes=lambda p,b:p.write_bytes(b),
            wait_camera=lambda r:{'pid':33,'dpu_schedule':{'rollback_holds_both_optional_tasks':True,
                'optional':{'yunet':{'disabled':True},'sface':{'disabled':True}}}},
            gui_context_for=lambda *a:(root/'gui',helper,{}),save=lambda *a:None)
        # The extracted helper uses its own globals, not env's earlier bindings.
        exec(compile(ast.fix_missing_locations(ast.Module(body=[next(n for n in nodes if n.name=='effective_marker')],type_ignores=[])),'marker','exec'),ns)
        exec(rollback_code,ns)
        report={'candidate_unit_sha256':'candidate','rollback_unit_sha256':'protected','original_page':'main'}
        return root,report,ns,calls,persistent,runtime,foreign

    def test_persistent_rollback_removes_only_own_verified_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root,report,ns,calls,persistent,runtime,foreign=self.rollback_fixture(folder)
            ns['rollback'](root,report)
            self.assertFalse(persistent.exists());self.assertEqual(runtime.read_text(),'protected')
            self.assertEqual(foreign.read_text(),'keep');self.assertTrue(report['rolled_back'])

    def test_unknown_native_owner_is_checked_before_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            root,report,ns,calls,persistent,runtime,foreign=self.rollback_fixture(folder,fenced=True)
            with self.assertRaises(AssertionError):ns['rollback'](root,report)
            self.assertEqual(calls,[]);self.assertTrue(persistent.exists());self.assertFalse(runtime.exists())

if __name__=='__main__':unittest.main(verbosity=2)
