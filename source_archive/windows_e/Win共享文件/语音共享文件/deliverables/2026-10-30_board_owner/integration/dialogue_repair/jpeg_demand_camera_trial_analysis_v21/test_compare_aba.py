"""Public numeric fixtures only. These are not measured camera results."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import compare_aba as compare


def receipt(label, *, cpu=1.0, people=1, frame_rate=15, face_age=80, rss=20_000_000):
    order = {'A1': 0, 'B': 1, 'A2': 2}[label]
    pid, birth = [(1335, '2344'), (10000, '5000'), (20000, '8000')][order]
    argv = ['/usr/bin/python3', '-B', compare.BASE]
    if label == 'B':
        argv = ['/usr/bin/python3', '-B', compare.CANDIDATE, '--manifest-sha256', compare.MANIFEST]
    owner = {'pid': pid, 'birth': birth, 'argv': argv,
             'cmd_sha256': hashlib.sha256(('\0'.join(argv) + '\0').encode()).hexdigest()}
    rows = []
    for index in range(31):
        rows.append({
            'process': {'mono': 1000 + order * 100 + index, 'ticks': 1000 + round(index * 100 * cpu),
                        'birth': birth, 'rss_bytes': rss, 'system_busy_ticks': 10000 + 300 * index},
            'health': {'pid': pid, 'board_boot_id': compare.BOOT,
                       'service_epoch': 'public-service-' + label, 'camera_epoch': 'public-camera-' + label,
                       'capture_frames': 100 + index * frame_rate, 'detected_frames': 100 + index * frame_rate,
                       'preview_frames': 100 + index * frame_rate, 'preview_buffers': 8,
                       'capture_age_ms': 10, 'observation_age_ms': 20,
                       'people_count': people, 'face_source_age_ms': face_age, 'face_processed': 100 + index,
                       'native_primary_calls': 100 + index, 'native_primary_overruns': 0,
                       'native_optional_overruns': {'yunet': 0, 'sface': 0},
                       'camera_error_present': False, 'detector_error_present': False, 'preview_error_present': False},
        })
    return {'status': 'METADATA_SAMPLE_COMPLETE', 'label': label, 'owner': owner,
            'manifest_sha256': compare.MANIFEST, 'journal_sha256': hashlib.sha256(label.encode()).hexdigest(),
            'summary': {'seconds': 30, 'camera_cpu_cores': cpu, 'whole_system_busy_cores': 3,
                        'camera_rss_min_bytes': rss, 'camera_rss_max_bytes': rss,
                        'people_counts': [people] * 31, 'face_source_age_ms': [face_age] * 31,
                        'capture_frames_per_second': frame_rate, 'detected_frames_per_second': frame_rate,
                        'preview_frames_per_second': frame_rate},
            'samples': rows, 'GUI_normally_closed_all_samples': True,
            'sampler_JPEG_GET_requests': 0, 'camera_frames_or_private_database_read': False,
            'production_mutated': False, 'limits': ['Synthetic test fixture only']}


def triplet():
    return [receipt('A1'), receipt('B', cpu=.6), receipt('A2')]


class CompareTests(unittest.TestCase):
    def test_numeric_units_and_two_baselines(self):
        result = compare.comparison(*triplet())
        self.assertEqual(result['status'], 'DESCRIPTIVE_ABA_WITHOUT_THRESHOLD_FLAGS')
        self.assertTrue(result['B_CPU_lower_than_both_baselines'])
        self.assertEqual(len(result['B_against_each_baseline']), 2)
        self.assertEqual(result['B_against_each_baseline'][0]['B_relative_changes_percent']['camera_cpu_cores'], -40)
        self.assertEqual(result['arms'][1]['CPU_ms_per_capture_completion'], 40)
        self.assertEqual(result['arms'][1]['sampler_implied_clock_ticks_per_second'], 100)
        self.assertFalse(result['comparison_changes_production'])
        self.assertFalse(result['B_adoption_authorized_by_comparison'])

    def test_lower_cpu_with_less_work_has_confounding_flags(self):
        result = compare.comparison(receipt('A1'), receipt('B', cpu=.6, people=0, frame_rate=7), receipt('A2'))
        self.assertTrue(result['B_CPU_lower_than_both_baselines'])
        self.assertIn('B_vs_A1_person_count_distribution_changed', result['threshold_flags'])
        self.assertIn('B_vs_A2_detected_frames_per_second_changed', result['threshold_flags'])
        self.assertEqual(result['B_against_each_baseline'][0]['person_distribution_total_variation'], 1)

    def test_baseline_drift_is_reported(self):
        result = compare.comparison(receipt('A1'), receipt('B', cpu=.6), receipt('A2', cpu=.8))
        self.assertIn('A1_to_A2_baseline_CPU_changed', result['threshold_flags'])

    def test_unknown_person_and_face_coverage_are_reported(self):
        result = compare.comparison(receipt('A1'), receipt('B', people=None, face_age=None), receipt('A2'))
        self.assertIn('B_person_count_coverage_incomplete', result['threshold_flags'])
        self.assertIn('B_face_age_coverage_incomplete', result['threshold_flags'])
        self.assertEqual(result['arms'][1]['face_source_age'], {'valid': 0, 'missing': 31})

    def test_face_p95_and_rss_difference(self):
        result = compare.comparison(receipt('A1'), receipt('B', face_age=200, rss=28_000_000), receipt('A2'))
        self.assertIn('B_vs_A1_face_source_age_changed', result['threshold_flags'])
        self.assertEqual(result['B_against_each_baseline'][0]['B_peak_RSS_minus_baseline_bytes'], 8_000_000)
        self.assertEqual(result['arms'][1]['face_source_age']['p95_ms'], 200)

    def test_nonfinite_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"status":1,"status":2}', object_pairs_hook=compare.unique)
        self.assertFalse(compare.number(float('nan')))
        self.assertFalse(compare.number(float('inf')))
        self.assertFalse(compare.number(True))

    def test_receipt_inconsistencies_refuse(self):
        changes = [
            (['manifest_sha256'], '0' * 64),
            (['journal_sha256'], 'missing'),
            (['GUI_normally_closed_all_samples'], False),
            (['sampler_JPEG_GET_requests'], 1),
            (['summary', 'capture_frames_per_second'], 1),
            (['summary', 'seconds'], 31),
            (['summary', 'camera_rss_min_bytes'], 0),
            (['summary', 'whole_system_busy_cores'], 1),
            (['samples', 1, 'health', 'camera_epoch'], 'changed'),
            (['samples', 1, 'health', 'board_boot_id'], 'changed'),
            (['samples', 1, 'health', 'preview_error_present'], True),
            (['samples', 1, 'health', 'preview_buffers'], 9),
            (['samples', 1, 'process', 'mono'], 1000),
            (['samples', 1, 'process', 'birth'], 'new'),
            (['samples', 1, 'health', 'capture_frames'], 0),
            (['owner', 'pid'], 1336),
        ]
        for path, value in changes:
            with self.subTest(path=path):
                changed = receipt('A1')
                target = changed
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(ValueError):
                    compare.describe(changed, 'A1')

    def test_wrong_argv_same_journal_and_wrong_chronology_refuse(self):
        changed = triplet()
        changed[1]['owner']['argv'] = changed[0]['owner']['argv']
        with self.assertRaises(ValueError):
            compare.comparison(*changed)
        changed = triplet()
        changed[2]['journal_sha256'] = changed[1]['journal_sha256']
        with self.assertRaises(ValueError):
            compare.comparison(*changed)
        changed = triplet()
        for row in changed[1]['samples']:
            row['process']['mono'] -= 100
        with self.assertRaises(ValueError):
            compare.comparison(*changed)

    def test_cli_hashes_original_envelopes_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='public-aba-analysis-') as directory:
            root = Path(directory)
            paths = [root / (label + '.json') for label in ('A1', 'B', 'A2')]
            for path, value in zip(paths, triplet()):
                path.write_text(json.dumps({'returncode': 0, 'result': value}), encoding='utf-8')
            output = root / 'public-synthetic-comparison.json'
            command = [sys.executable, '-B', str(Path(compare.__file__)),
                       '--a1', str(paths[0]), '--b', str(paths[1]), '--a2', str(paths[2]),
                       '--result-member', 'result', '--output', str(output)]
            completed = subprocess.run(command, capture_output=True, text=True, check=True)
            result = json.loads(output.read_bytes())
            self.assertEqual(result['inputs'][0]['sha256'], hashlib.sha256(paths[0].read_bytes()).hexdigest())
            before = output.read_bytes()
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(output.read_bytes(), before)
            self.assertEqual(json.loads(completed.stdout)['sha256'], hashlib.sha256(before).hexdigest())


if __name__ == '__main__':
    unittest.main(verbosity=2)
