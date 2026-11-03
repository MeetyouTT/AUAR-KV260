"""Startup failure must preserve fallback without loading GL or audio devices."""
from pathlib import Path
from types import SimpleNamespace
import json,shutil,tempfile,unittest
from native_yuki import prepare_portrait

PHASE=Path(__file__).parent.parent
class PreparationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=str(PHASE),prefix='_prepare_test_')
        cls.root=Path(cls.temp.name).resolve()
        assert cls.root.is_relative_to(PHASE.resolve())
        shutil.copytree(PHASE/'runtime_assets',cls.root/'assets/yuki')
        (cls.root/'tools').mkdir()
        for name in ('native_yuki.py','egl_window.py'):
            shutil.copyfile(PHASE/'host'/name,cls.root/'tools'/name)
        (cls.root/'tools/libaura_yuki.so').write_bytes(b'path-validation-fixture-only; never executed')
        cls.config=dict(fps=24,library='tools/libaura_yuki.so',model='assets/yuki/model.runtime.json',
          resx='assets/yuki/yuk_0.ems.resx.json',resource_root='assets/yuki')
    @classmethod
    def tearDownClass(cls):
        assert cls.root.is_relative_to(PHASE.resolve())
        cls.temp.cleanup()
    def prepare(self,**changes):
        hashes={};mailbox,config=prepare_portrait(self.root,self.config|changes,SimpleNamespace(),hashes)
        return mailbox,config,hashes
    def test_valid_profile_pins_actual_resources_and_adapter(self):
        mailbox,config,hashes=self.prepare()
        self.assertIsNotNone(config);self.assertEqual(mailbox.error,'')
        self.assertIn('assets/yuki/model.source.ems.json',hashes)
        self.assertIn('assets/yuki/yuk_0.ems/tex-texture.png',hashes)
        self.assertIn('tools/libaura_yuki.so',hashes)
    def test_missing_model_keeps_local_fallback(self):
        mailbox,config,hashes=self.prepare(model='assets/yuki/missing.json')
        self.assertIsNone(config);self.assertEqual(mailbox.status()['mode'],'local');self.assertTrue(mailbox.error)
        self.assertEqual(hashes,{})
    def test_corrupt_texture_is_rejected_without_partial_pins(self):
        path=self.root/'assets/yuki/yuk_0.ems/tex-texture.png';original=path.read_bytes()
        try:
            path.write_bytes(original+b'corrupted')
            mailbox,config,hashes=self.prepare()
            self.assertIsNone(config);self.assertIn('hash mismatch',mailbox.error);self.assertEqual(hashes,{})
        finally:path.write_bytes(original)
    def test_asset_escape_is_rejected(self):
        mailbox,config,_=self.prepare(library=str(PHASE/'host/native_yuki.py'))
        self.assertIsNone(config);self.assertIn('escapes pinned runtime',mailbox.error)
    def test_missing_profile_keeps_local_fallback(self):
        empty=self.root/'assets/empty';empty.mkdir(exist_ok=True)
        mailbox,config,_=self.prepare(resource_root='assets/empty')
        self.assertIsNone(config);self.assertEqual(mailbox.status()['mode'],'local')
    def test_invalid_rate_keeps_local_fallback(self):
        mailbox,config,_=self.prepare(fps=60)
        self.assertIsNone(config);self.assertIn('Unsupported native frame rate',mailbox.error)
    def test_malformed_profile_keeps_local_fallback(self):
        path=self.root/'assets/yuki/source_profile.json';original=path.read_bytes()
        try:
            path.write_text('[]',encoding='utf8')
            mailbox,config,_=self.prepare()
            self.assertIsNone(config);self.assertIn('Unsupported Yuki source profile',mailbox.error)
        finally:path.write_bytes(original)
    def test_missing_texture_manifest_entry_keeps_fallback(self):
        path=self.root/'assets/yuki/source_profile.json';original=path.read_bytes()
        try:
            profile=json.loads(original);del profile['files']['yuk_0.ems/tex-texture.png']
            path.write_text(json.dumps(profile),encoding='utf8')
            mailbox,config,_=self.prepare()
            self.assertIsNone(config);self.assertIn('Incomplete Yuki profile',mailbox.error)
        finally:path.write_bytes(original)

if __name__=='__main__':unittest.main()
