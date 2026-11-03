import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_counters import audit


class PublicTraceTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "examples/public_counters.json").read_text())
        self.rows = self.data["records"]

    def test_independent_crosscheck(self):
        result = audit(self.data)
        self.assertEqual(result["sample_count_after_baseline"], 90)
        self.assertAlmostEqual(result["counter_interval_s"], 179.77388517899817, places=8)
        for key, calls, hz, ms in (("yolo", 1781, 9.906889414, 15.923683025),
                                  ("yunet", 1773, 9.862389069, 2.411370108),
                                  ("sface", 133, 0.739818244, 8.422059256)):
            m = result["models"][key]
            self.assertEqual(m["counter_delta"], calls)
            self.assertEqual(m["stage_count_delta"], calls)
            self.assertAlmostEqual(m["observed_rate_hz"], hz, places=7)
            self.assertAlmostEqual(m["stage_mean_ms"], ms, places=7)

    def test_process_switch(self):
        self.rows[1]["pid"] += 1
        with self.assertRaises(ValueError):
            audit(self.data)

    def test_counter_reset_in_middle(self):
        self.rows[1]["models"]["sface"]["count"] = 0
        with self.assertRaises(ValueError):
            audit(self.data)

    def test_interval_must_advance(self):
        self.rows[2]["finished_mono_s"] = self.rows[1]["finished_mono_s"]
        with self.assertRaises(ValueError):
            audit(self.data)

    def test_unknown_values_stay_null(self):
        for row in self.rows:
            row["models"] = copy.deepcopy(self.rows[0]["models"])
        result = audit(self.data)
        self.assertIsNone(result["models"]["sface"]["stage_mean_ms"])
        self.assertIsNone(result["per_job_source_to_consume_p99_ms"])
        self.assertIsNone(result["dpu_hardware_utilization"])
