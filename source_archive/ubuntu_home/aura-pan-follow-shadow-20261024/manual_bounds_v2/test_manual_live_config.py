import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from manual_live_config import current_config

class LiveConfigTests(unittest.TestCase):
    def test_live_bounds_reload_is_pinned_and_does_not_change_platform(self):
        with tempfile.TemporaryDirectory() as t:
            n=Path(t);a=n/'runtime/aura';(a/'config').mkdir(parents=True);(n/'startup').mkdir()
            base=dict(boot_id='boot',fdt_sha256='fdt',face_follow_config='same',enabled=True,maximum_step_us=20,
                maximum_duration_s=2,manual_minimum_us=1425,manual_maximum_us=1505)
            path=a/'config/pan_manual.local.json';startup=n/'startup/config.json'
            def write(value):
                path.write_text(json.dumps(value));startup.write_text(json.dumps({'component_sha256':{'config/pan_manual.local.json':hashlib.sha256(path.read_bytes()).hexdigest()}}))
            write(dict(base,manual_minimum_us=1400,manual_maximum_us=1600))
            self.assertEqual(current_config(base,aura=a)['manual_maximum_us'],1600)
            self.assertEqual(base['manual_maximum_us'],1505)
            for changes in ({'boot_id':'other'},{'fdt_sha256':'other'},{'manual_maximum_us':1601},{'maximum_duration_s':3}):
                write(dict(base,**changes))
                with self.assertRaises(RuntimeError):current_config(base,aura=a)
            write(base);path.write_text('{}')
            with self.assertRaises(RuntimeError):current_config(base,aura=a)

if __name__=='__main__':unittest.main()
