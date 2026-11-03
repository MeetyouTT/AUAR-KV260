"""Negative cases for importing and recomputing preserved board evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('board_evidence_verifier', ROOT/'board/verify_evidence.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class EvidenceReplayTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='auar-evidence-negative-')
        self.root = Path(self.temporary.name)
        shutil.copytree(str(ROOT/'board'), str(self.root/'board'))
        (self.root/'data').mkdir()
        shutil.copytree(str(ROOT/'data/board_reference'), str(self.root/'data/board_reference'))

    def tearDown(self):
        self.temporary.cleanup()

    def replace_json_and_update_import_hash(self, rel, modify):
        path = self.root/rel
        value = json.loads(path.read_text())
        modify(value)
        path.write_text(json.dumps(value))
        manifest = self.root/'board/evidence_sources.json'
        source = json.loads(manifest.read_text())
        item = next(row for row in source['records'] if row['file']==rel)
        item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(source))

    def failed(self, name):
        result = verifier.evaluate(self.root)
        self.assertEqual(result['status'], 'FAIL')
        return next(row for row in result['checks'] if row['check']==name)

    def test_original_records_recompute(self):
        self.assertEqual(verifier.evaluate(self.root)['status'], 'PASS')

    def test_two_lsb_error_is_rejected_even_with_updated_file_hash(self):
        self.replace_json_and_update_import_hash(
            'board/evidence/dpu_20261021/yunet_fixed.public.json',
            lambda value: value['core']['agreement'][0]['heads'][0].update(max_integer_difference=2))
        self.assertFalse(self.failed('yunet_0_1x40x40x51_within_1_lsb')['passed'])

    def test_different_release_is_rejected_even_with_updated_file_hash(self):
        self.replace_json_and_update_import_hash(
            'board/evidence/runtime_9a4f/release_result.public.json',
            lambda value: value.update(startup_sha256='0'*64))
        self.assertFalse(self.failed('historical_9a4f_startup')['passed'])

    def test_false_dpu_summary_does_not_replace_tensor_checks(self):
        self.replace_json_and_update_import_hash(
            'board/evidence/dpu_20261021/sface_three_fixed.public.json',
            lambda value: value['core']['agreement'][0].update(maximum_integer_difference=3))
        self.assertFalse(self.failed('sface_0_within_1_lsb')['passed'])

    def test_reference_statistics_are_recomputed(self):
        self.replace_json_and_update_import_hash(
            'data/board_reference/performance_summary.public.json',
            lambda value: value['cpu_total_percent'].update(mean=1.0))
        self.assertFalse(self.failed('cpu_mean_percent')['passed'])


if __name__ == '__main__':
    unittest.main()

