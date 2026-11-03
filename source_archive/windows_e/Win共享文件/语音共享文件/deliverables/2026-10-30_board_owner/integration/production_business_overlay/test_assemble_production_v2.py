"""Execute assemble() against complete PUBLIC source/resource fixtures.

Uses the actual304-source appearance snapshot, frozen438 source closure and
approved public selected-voice resources. No model import/DB/device/main mock.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]


def module(name):
    spec=importlib.util.spec_from_file_location('_fixture_'+name,HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,raw):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


class CompleteAssemblyTests(unittest.TestCase):
    def fixture(self,root,name='assemble_production_v2',*,presentation=False):
        assembler=module(name);base=root/'current'
        for path in (HERE/'fresh/aura').rglob('*'):
            if path.is_file():write(base/'runtime/aura'/path.relative_to(HERE/'fresh/aura'),path.read_bytes())
        startup=json.loads((HERE/'fresh/startup/config.json').read_bytes())
        startup['runtime']=base.as_posix()+'/runtime'
        raw=assembler.encoded(startup);write(base/'startup/config.json',raw)
        assembler.BASE=base.as_posix();assembler.STARTUP=sha(raw)
        original=json.loads((HERE.parent/'resume_ui_trial/actual_ui_baseline.json').read_text(encoding='utf8'))['launcher']['content'].encode()
        self.assertEqual(sha(original),assembler.LAUNCHER);write(base/'startup/launcher.py',original)
        voice='deliverables/2026-10-06_voice_selected_soft_young'
        for relative in ('selection.json','base_model_verification.json','reference/soft_young.wav'):
            write(base/'runtime'/voice/relative,(PROJECT/voice/relative).read_bytes())
        manifest=json.loads((HERE/'production_business.source_only.manifest.json').read_bytes())
        manifest['basis_startup_sha256']=assembler.STARTUP
        manifest_raw=assembler.encoded(manifest);manifest_path=root/'manifest.json';write(manifest_path,manifest_raw)
        config=json.loads((HERE/'production_config.stencil.json').read_bytes())
        config['board_business']['bootstrap_receipt_sha256']='a'*64
        config['board_business']['utc_bounds']=[1793300000.,1825100000.]
        config_raw=assembler.encoded(config);config_path=root/'root-public-config.json';write(config_path,config_raw)
        args=SimpleNamespace(manifest=str(manifest_path),manifest_sha256=sha(manifest_raw),
            overlay=str(HERE/'production_business.source_only.overlay.zip'),config=str(config_path),config_sha256=sha(config_raw),
            target=assembler.PREFIX+'complete-source-fixture',allow_retention=False,extra_sources=None,extra_sources_sha256=None)
        if presentation:
            after=HERE.parent/'production_presentation_patch/after/aura'
            files={}
            for relative in ('tools/board_avatar_gtk.py','board/runtime/audio/board_dialogue_jobs.py','tools/production_memory_presentation.py'):
                path=after/relative;self.assertTrue(path.is_file());files['aura/'+relative]={'path':str(path.resolve()),'sha256':sha(path.read_bytes())}
            extra_raw=assembler.encoded({'schema':'aura.production-source-dependencies.v1','files':files})
            extra_path=root/'presentation-source-map.json';write(extra_path,extra_raw)
            args.extra_sources=str(extra_path);args.extra_sources_sha256=sha(extra_raw)
        return assembler,args

    def test_frozen_e4_original_reproduces_real_local_binding_failure(self):
        with tempfile.TemporaryDirectory(prefix='aura-assemble-public-') as tmp:
            assembler,args=self.fixture(Path(tmp),'assemble_production')
            with self.assertRaises(UnboundLocalError):assembler.assemble(args)

    def test_complete_source_assembly_includes_all_public_voice_and_startup(self):
        with tempfile.TemporaryDirectory(prefix='aura-assemble-public-') as tmp:
            assembler,args=self.fixture(Path(tmp));plan,payload=assembler.assemble(args)
            self.assertEqual(len(plan['component_pins']),367)
            for name in ('selection.json','base_model_verification.json','reference/soft_young.wav'):
                self.assertIn('runtime/deliverables/2026-10-06_voice_selected_soft_young/'+name,payload)
            self.assertEqual(plan['native_library_sha256'],assembler.LIBRARY)
            self.assertEqual(sha(payload['startup/launcher.py']),assembler.LAUNCHER)
            startup=json.loads(payload['startup/config.json'])
            self.assertEqual(startup['runtime'],args.target+'/runtime')
            self.assertEqual(startup['component_sha256'],plan['component_pins'])
            self.assertFalse(plan['retention_enabled']);self.assertFalse(plan['production_store_opened'])
            config=json.loads(payload['runtime/aura/config/board_avatar_gtk.json'])
            self.assertEqual(config['board_business']['data_origin'],'board')
            self.assertEqual(config['formal_stage_root'],json.loads((HERE/'fresh/aura/config/board_avatar_gtk.json').read_bytes())['formal_stage_root'])

    def test_complete_assembly_with_actual_presentation_source_map_recalculates_pins(self):
        with tempfile.TemporaryDirectory(prefix='aura-assemble-public-') as tmp:
            assembler,args=self.fixture(Path(tmp),presentation=True);plan,payload=assembler.assemble(args)
            self.assertEqual(len(plan['component_pins']),368)
            self.assertIn('runtime/aura/tools/production_memory_presentation.py',payload)
            self.assertEqual(plan['extra_sources_sha256'],args.extra_sources_sha256)
            for relative in ('tools/board_avatar_gtk.py','board/runtime/audio/board_dialogue_jobs.py'):
                after=HERE.parent/'production_presentation_patch/after/aura'/relative
                self.assertEqual(sha(payload['runtime/aura/'+relative]),sha(after.read_bytes()))
            self.assertEqual(plan['component_pins']['tools/libaura_yuki.so'],assembler.LIBRARY)
            self.assertFalse(plan['unit_or_gui_action'])


if __name__=='__main__':unittest.main()
