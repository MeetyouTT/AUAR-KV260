import ast,json
from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest

SOURCE=Path(__file__).resolve().parents[1]/'trace_optional_phases_vision.py'
node=next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='cleanup')
code=compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'cleanup','exec')

class VisionCleanupTests(unittest.TestCase):
    def check(self,page='vision',phase='IDLE',pid=7):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'ownership.json').write_text(json.dumps({'gui_pid':7,'original_page':'main'}))
            calls=[]
            g=SimpleNamespace(GUI='gui',ui=lambda:{'ui_page':page,'phase':phase,'playing':False},
                prop=lambda *a:str(pid),set_page=lambda v:calls.append(v))
            env={'ROOT':root,'json':json,'h':SimpleNamespace(cleanup=lambda:{'passed':True}),'gui':lambda:g}
            exec(code,env);return env['cleanup'](),calls
    def test_restores_owned_idle_page(self):
        result,calls=self.check();self.assertTrue(result['passed']);self.assertEqual(calls,['main'])
    def test_never_overrides_independent_page_change(self):self.assertFalse(self.check(page='settings')[1])
    def test_never_overrides_active_user_operation(self):self.assertFalse(self.check(phase='SPEAKING')[1])
    def test_changed_gui_process_receives_no_page_command(self):self.assertFalse(self.check(pid=8)[1])

if __name__=='__main__':unittest.main(verbosity=2)
