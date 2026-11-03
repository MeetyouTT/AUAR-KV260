"""Read-only helper review: pure AST and temporary-file fake runpy only."""
import ast
import copy
import hashlib
import importlib.util
import io
from pathlib import Path
import runpy
import tarfile
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path('/home/ghmd/aura-post-power-20261022')
SHORT = Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_light_live_usb3_20261022.py')


def load(path):
    spec = importlib.util.spec_from_file_location('review_long_transform', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class LongTests(unittest.TestCase):
    def test_600_and_1800_window_indices_and_restore_are_exact(self):
        module = load(ROOT/'make_long_trial.py'); raw = SHORT.read_bytes()
        original = next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='main')
        old_guard = next(n for n in original.body if isinstance(n,ast.Try) and n.finalbody)
        for seconds in (600, 1800):
            changed = module.extend(raw, seconds)
            guard = next(n for n in changed.body if isinstance(n,ast.Try) and n.finalbody)
            loop = next(n for n in guard.body if isinstance(n,ast.For))
            tail = next(n for n in loop.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
                and isinstance(n.test.left,ast.Name) and n.test.left.id=='index')
            self.assertEqual(ast.literal_eval(loop.iter.args[0]), seconds//5+1)
            self.assertEqual(ast.literal_eval(tail.test.comparators[0]), seconds//5)
            self.assertEqual(ast.dump(ast.Module(body=old_guard.finalbody,type_ignores=[])),
                ast.dump(ast.Module(body=guard.finalbody,type_ignores=[])))
            self.assertEqual(changed.name, 'long_trial')

    def test_only_window_scope_and_timer_constants_change(self):
        module = load(ROOT/'make_long_trial.py'); raw = SHORT.read_bytes()
        original = next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='main')
        for seconds in (600,1800):
            changed = module.extend(raw, seconds)
            before = [n.value for n in ast.walk(original) if isinstance(n,ast.Constant)]
            after = [n.value for n in ast.walk(changed) if isinstance(n,ast.Constant)]
            self.assertEqual(len(before), len(after))
            for old,new in zip(before,after):
                if old == new: continue
                allowed = ((type(old) is int and ((old,new) in (
                    (25,seconds//5+1),(24,seconds//5),(120,seconds))))
                    or (old=='--on-active=360s' and new=='--on-active='+str(seconds+600)+'s')
                    or (isinstance(old,str) and new==old.replace('_120S_','_'+str(seconds)+'S_').replace('_SHORT_','_WINDOW_'+str(seconds)+'S_')))
                self.assertTrue(allowed, (old,new))

    def test_generated_600_pins_exact_short(self):
        helper = Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_postpower_metrics_live_600_20261022.py')
        tree = ast.parse(helper.read_text())
        constants = {n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
            and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('EXPECTED','SECONDS','GROUP')}
        self.assertEqual(constants['EXPECTED'], hashlib.sha256(SHORT.read_bytes()).hexdigest())
        self.assertEqual(constants['SECONDS'], 600)
        self.assertIn('sys._getframe().f_code.co_filename', helper.read_text())

    def test_updated_1800_precondition_requires_600_scope(self):
        source = (ROOT/'make_long_trial.py').read_text()
        tree = ast.parse(source)
        body = next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.AugAssign)
            and isinstance(n.target,ast.Name) and n.target.id=='code' and isinstance(n.value,ast.Constant))
        assignment = next(n for n in ast.walk(ast.parse(body)) if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='required_scope' for t in n.targets))
        expression = compile(ast.Expression(assignment.value),'<review-scope-only>','eval')
        short_scope = 'FRESHNESS_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED'
        self.assertEqual(eval(expression,{'SHORT_SCOPE':short_scope,'SECONDS':600}),short_scope)
        self.assertEqual(eval(expression,{'SHORT_SCOPE':short_scope,'SECONDS':1800}),
            'FRESHNESS_1MS_DUAL_MODEL_600S_ALWAYS_RESTORED')

    def test_frame_filename_identifies_run_source_instead_of_old_module_file(self):
        namespace = {'__file__':'/review/old-source.py'}
        exec(compile('import sys; captured=sys._getframe().f_code.co_filename',
            '/review/current-source.py','exec'),namespace)
        self.assertEqual(namespace['captured'],'/review/current-source.py')


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.boot = self.root/'boot'; self.boot.write_text('review-boot')
        tree = ast.parse((ROOT/'stage_helper_bundle.py').read_text())
        body = next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets)
            and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))
        remote = ast.parse(body)
        remote.body = [n for n in remote.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
        self.program = compile(remote,'<review-only-tempfiles>','exec')
        self.calls = []
        self.raw = b'# fake helper, never executed\n'

    def archive(self, *, symlink=False, extra=False, raw=None):
        raw = self.raw if raw is None else raw
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
            info = tarfile.TarInfo('source.py'); info.size = len(raw)
            if symlink: info.type=tarfile.SYMTYPE;info.linkname='/outside'
            archive.addfile(info,None if symlink else io.BytesIO(raw))
            if extra: archive.addfile(tarfile.TarInfo('extra'))
        path = self.root/'bundle.tar.gz'; path.write_bytes(buffer.getvalue()); return path

    def execute(self, path, *, boot='review-boot', source_sha=None, bundle_sha=None, target=None):
        def mapped(value):
            if str(value)=='/proc/sys/kernel/random/boot_id':return self.boot
            if str(value)=='/home/root/aura-post-power-20261022/helpers':return self.root/'namespace'
            return Path(value)
        values = {'hashlib':hashlib,'tarfile':tarfile,'Path':mapped,
            'runpy':SimpleNamespace(run_path=lambda *a,**kw:self.calls.append((a,kw))),
            'BOOT':boot,'BUNDLE':str(path),'BUNDLE_SHA':bundle_sha or hashlib.sha256(path.read_bytes()).hexdigest(),
            'SOURCE_SHA':source_sha or hashlib.sha256(self.raw).hexdigest(),
            'TARGET':str(target or self.root/'namespace/hash/source.py')}
        exec(self.program,values)

    def test_regular_pinned_source_reaches_fake_runpy(self):
        self.execute(self.archive()); self.assertEqual(len(self.calls),1)
        self.assertEqual((self.root/'namespace/hash/source.py').read_bytes(),self.raw)

    def test_wrong_boot_bundle_and_source_are_rejected(self):
        for kwargs in ({'boot':'other'}, {'bundle_sha':'0'*64}, {'source_sha':'0'*64}):
            with self.assertRaises(AssertionError):self.execute(self.archive(),**kwargs)
        self.assertEqual(self.calls,[])

    def test_tar_symlink_extra_member_and_300000_bytes_are_rejected(self):
        for kwargs in ({'symlink':True},{'extra':True},{'raw':b'x'*300000}):
            with self.assertRaises(AssertionError):self.execute(self.archive(**kwargs))
        self.assertEqual(self.calls,[])

    def test_existing_different_target_and_final_symlink_are_preserved(self):
        target=self.root/'namespace/hash/existing.py';target.parent.mkdir(parents=True);target.write_bytes(b'original')
        with self.assertRaises(AssertionError):self.execute(self.archive(),target=target)
        self.assertEqual(target.read_bytes(),b'original')
        link=target.with_name('link.py');link.symlink_to(target)
        with self.assertRaises(AssertionError):self.execute(self.archive(),target=link)
        self.assertEqual(target.read_bytes(),b'original')

    def test_parent_symlink_is_rejected_before_namespace_escape(self):
        outside=self.root/'outside';outside.mkdir()
        namespace=self.root/'namespace';namespace.mkdir()
        (namespace/'hash').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(AssertionError):self.execute(self.archive(),target=namespace/'hash/source.py')
        self.assertFalse((outside/'source.py').exists())
        self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main(verbosity=2)
