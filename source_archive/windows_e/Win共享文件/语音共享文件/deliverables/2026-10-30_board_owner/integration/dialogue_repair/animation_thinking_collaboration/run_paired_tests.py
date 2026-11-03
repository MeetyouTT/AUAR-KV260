"""Validate the resealed overlay without changing the frozen candidate/tests."""
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import unittest

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PairingContract(unittest.TestCase):
    def setUp(self):
        self.receipt=json.loads((HERE/'paired_overlay/PAIRING_RECEIPT.json').read_text(encoding='utf-8'))
        self.old=json.loads((HERE/'before/aura/config/yuki_pair.formal.json').read_text(encoding='utf-8'))
        self.selection=HERE/'paired_overlay/aura/config/yuki_pair.formal.json'
        self.new=json.loads(self.selection.read_text(encoding='utf-8'))

    def test_selection_hash_matches_formal_adapter_and_startup_field(self):
        from tools.formal_yuki import PAIR_CONFIG_SHA256
        digest=sha(self.selection)
        self.assertEqual(PAIR_CONFIG_SHA256,digest)
        self.assertEqual(self.receipt['selection_sha256'],digest)
        self.assertEqual(self.receipt['required_startup_change']['character_pair.selection_sha256'],digest)

    def test_only_native_adapter_and_library_inner_pins_change(self):
        old=dict(self.old);new=dict(self.new)
        old_pins=old.pop('runtime_pins');new_pins=new.pop('runtime_pins')
        self.assertEqual(old,new)
        self.assertEqual(set(old_pins),set(new_pins))
        self.assertEqual({name for name in old_pins if old_pins[name]!=new_pins[name]},
                         {'tools/native_yuki.py','tools/libaura_yuki.so'})
        self.assertNotIn('tools/yuki_jobs_candidate.py',new_pins)

    def test_all_five_artifacts_match_pairing_receipt(self):
        self.assertEqual(len(self.receipt['files']),5)
        for relative,expected in self.receipt['files'].items():
            with self.subTest(path=relative):
                self.assertEqual(sha(HERE/'paired_overlay/aura'/relative),expected)

    def test_library_and_native_sources_match_cpu_pass_receipt(self):
        build=json.loads((HERE/'native_build_result/native_build_receipt.json').read_text(encoding='utf-8'))
        self.assertEqual(sha(HERE/'paired_overlay/aura/tools/libaura_yuki.so'),build['library_sha256'])
        self.assertEqual(sha(HERE/'candidate/native/yuki_host.cpp'),build['source_sha256'])
        self.assertEqual(sha(HERE/'candidate/native/yuki_host.h'),build['header_sha256'])
        self.assertEqual(build['native_policy_test']['status'],'PASS')
        self.assertFalse(build['production_installed'])
        self.assertFalse(build['gtk_or_egl_opened'])
        self.assertFalse(build['audio_device_opened'])


def main():
    pairing=json.loads((HERE/'paired_overlay/PAIRING_RECEIPT.json').read_text(encoding='utf-8'))
    baseline=json.loads((HERE/'SOURCE_BASELINE.json').read_text(encoding='utf-8'))
    mapping=json.loads(Path(baseline['source_mapping']).read_text(encoding='utf-8'))
    runtime=HERE/'paired_test_runtime'
    for path in (HERE/'runtime_v16').rglob('*'):
        if not path.is_file() or path.suffix not in ('.py','.json'):continue
        relative=path.relative_to(HERE/'runtime_v16').as_posix()
        if sha(path)!=mapping['component_pins'][relative]:
            raise ValueError('Frozen public baseline changed: '+relative)
        destination=runtime/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
    for relative,expected in pairing['files'].items():
        source=HERE/'paired_overlay/aura'/relative
        if sha(source)!=expected:raise ValueError('Resealed source changed: '+relative)
        if source.suffix not in ('.py','.json'):continue
        destination=runtime/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    sys.path.insert(0,str(runtime));sys.dont_write_bytecode=True
    suite=unittest.defaultTestLoader.discover(str(HERE/'tests'),pattern='test_*.py')
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(PairingContract))
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (HERE/'PAIRED_TEST_LOG.txt').write_text(log.getvalue(),encoding='utf-8')
    summary=dict(schema='aura.animation-thinking-paired-tests.v1',tests_run=result.testsRun,
        successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        files=pairing['files'],selection_sha256=pairing['selection_sha256'],
        pairing_receipt_sha256=sha(HERE/'paired_overlay/PAIRING_RECEIPT.json'),
        native_build_receipt_sha256=sha(HERE/'native_build_result/native_build_receipt.json'),
        frozen_candidate_unchanged=True,device_access=False,model_inference=False,
        microphone_opened=False,audio_device_opened=False,native_binary_executed_locally=False,
        physical_fps_measured=False,visual_preview_passed=False,production_installed=False)
    (HERE/'PAIRED_TEST_RESULTS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue())
    print(json.dumps(summary,ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':
    main()
