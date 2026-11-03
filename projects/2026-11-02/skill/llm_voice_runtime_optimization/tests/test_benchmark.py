import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def read(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))

mod = load_module("voice_bench", "analyze_benchmarks.py")

class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.data = read("examples/benchmarks.json")
    def result(self):
        return mod.audit(self.data)
    def candidate(self):
        return next(x for x in self.result()["groups"] if x["platform_id"] == "demo_platform_a"
                    and x["variant"] == "candidate" and not x["tts_cache_hit"])
    def test_machines_cache_and_variants_stay_separate(self):
        r = self.result()
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(len(r["groups"]), 4)
    def test_fast_wrong_answer_not_counted_as_speed(self):
        r = self.candidate()
        self.assertEqual(r["declared_invalid_answers"], 1)
        self.assertEqual(r["metrics"]["first_pcm_ms"]["median_ms"], 1850)
    def test_cached_answer_not_merged_into_uncached(self):
        self.assertFalse(self.candidate()["tts_cache_hit"])
        self.assertEqual(self.candidate()["metrics"]["first_pcm_ms"]["count"], 2)
    def test_second_machine_not_merged(self):
        r = next(x for x in self.result()["groups"] if x["platform_id"]=="demo_platform_b")
        self.assertEqual(r["metrics"]["first_pcm_ms"]["median_ms"], 900)
    def test_string_cache_flag_is_invalid(self):
        self.data["records"][0]["tts_cache_hit"] = "true"
        self.assertEqual(self.result()["status"], "FAIL")
    def test_missing_warm_state_is_unknown(self):
        del self.data["records"][0]["warm_state"]
        self.assertEqual(self.result()["status"], "UNKNOWN")
    def test_negative_duration_rejected(self):
        self.data["records"][0]["first_pcm_ms"] = -1
        self.assertEqual(self.result()["status"], "FAIL")
    def test_duplicate_trial_rejected(self):
        self.data["records"].append(copy.deepcopy(self.data["records"][0]))
        self.assertEqual(self.result()["status"], "FAIL")
    def test_missing_ack_metric_is_null(self):
        for r in self.data["records"]:
            r["complete_ack_ms"] = None
        self.assertIsNone(self.candidate()["metrics"]["complete_ack_ms"]["median_ms"])
    def test_no_data_is_unknown(self):
        self.data["records"] = []
        self.assertEqual(self.result()["status"], "UNKNOWN")

if __name__ == "__main__":
    unittest.main()
