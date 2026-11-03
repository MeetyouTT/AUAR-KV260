"""Independent benchmark formula and source checks; standard library only."""
import ast
import base64
import bisect
import gzip
import hashlib
import math
from pathlib import Path
import random
import unittest

ROOT = Path(__file__).resolve().parents[1]


def histogram_quantile(values, quantile=.99):
    histogram = [0] * 256
    for value in values:
        histogram[value] += 1
    cumulative = []
    total = 0
    for count in histogram:
        total += count
        cumulative.append(total)
    rank = quantile * (len(values) - 1)
    lo, hi = math.floor(rank), math.ceil(rank)
    low, high = bisect.bisect_right(cumulative, lo), bisect.bisect_right(cumulative, hi)
    return low + (high - low) * (rank - lo)


class BenchmarkFormulaTests(unittest.TestCase):
    def test_exact_linear_quantile_for_ties_and_edges(self):
        samples = [[0], [255], [0, 255], [0] * 99 + [255],
                   [0] * 100 + [1], list(range(256)), [17] * 111]
        rng = random.Random(20261023)
        samples.extend([rng.choices(range(256), k=count) for count in (2, 3, 17, 99, 100, 101, 999)])
        for values in samples:
            ordered = sorted(values)
            rank = .99 * (len(values) - 1)
            lo, hi = math.floor(rank), math.ceil(rank)
            expected = ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)
            self.assertEqual(histogram_quantile(values), expected)

    def test_staged_payload_matches_reviewed_script_and_candidate(self):
        parsed = ast.parse((ROOT / 'exact_helper.py').read_text())
        assignments = {node.targets[0].id: ast.literal_eval(node.value)
                       for node in parsed.body if isinstance(node, ast.Assign)
                       and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id in ('PAYLOAD', 'SOURCE_SHA')}
        raw = gzip.decompress(base64.b64decode(assignments['PAYLOAD']))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), assignments['SOURCE_SHA'])
        script = raw.decode()
        self.assertEqual(script[script.index('"""One asset'):], (ROOT / 'compare_exact.py').read_text())
        tree = ast.parse(script)
        candidate = next(ast.literal_eval(node.value) for node in tree.body
                         if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                         and node.targets[0].id == 'CANDIDATE')
        for relative, encoded in candidate.items():
            self.assertEqual(base64.b64decode(encoded), (ROOT / 'candidate/aura' / relative).read_bytes())
        cpp = next(ast.literal_eval(node.value) for node in parsed.body
                   if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                   and node.targets[0].id == 'CPP')
        self.assertEqual(base64.b64decode(cpp), (ROOT / 'candidate/aura/tools/native_pixels.cpp').read_bytes())

    def test_predeclared_thresholds_and_process_cpu_abba(self):
        script = (ROOT / 'compare_exact.py').read_text()
        self.assertIn("('baseline','candidate','candidate','baseline')", script)
        self.assertIn('used=time.process_time()', script)
        self.assertIn("'pixel_max':2", script)
        self.assertIn("'pixel_p99':1", script)
        self.assertIn("'pixel_mean':.1", script)
        self.assertIn("'idle_cpu_reduction':.10", script)


if __name__ == '__main__':
    unittest.main(verbosity=2)
