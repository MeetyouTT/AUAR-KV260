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

mod = load_module("schedule_analysis", "analyze_schedule.py")

class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.data = read("examples/jobs_pass.json")
    def result(self):
        return mod.audit(self.data)
    def test_job_denials_remain_in_arrival_denominator(self):
        r = self.result()
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["tasks"]["sface"]["timely_rate_all_arrivals"], .5)
        self.assertEqual(r["tasks"]["yunet"]["timely_rate_all_arrivals"], .5)
    def test_missing_validity_not_silently_zero(self):
        self.data["jobs"][0]["consumed_ms"] = None
        r = self.result()["tasks"]["yolo"]
        self.assertIsNone(r["timely_rate_all_arrivals"])
        self.assertEqual(r["validity_unknown"], 1)
    def test_missing_source_age_is_null(self):
        for job in self.data["jobs"]:
            job["source_ms"] = None
        r = self.result()
        self.assertIsNone(r["tasks"]["yolo"]["consumed_source_age_ms"]["median"])
    def test_unmapped_clocks_rejected(self):
        self.data["jobs"][0]["clock_domain"] = "unmapped_windows"
        self.assertEqual(self.result()["status"], "FAIL")
    def test_duplicate_identity_rejected(self):
        self.data["jobs"].append(copy.deepcopy(self.data["jobs"][0]))
        self.assertEqual(self.result()["status"], "FAIL")
    def test_time_order_rejected(self):
        self.data["jobs"][0]["end_ms"] = 1
        self.assertEqual(self.result()["status"], "FAIL")
    def test_bad_numeric_field(self):
        self.data["jobs"][0]["queued_ms"] = "one"
        self.assertEqual(self.result()["status"], "FAIL")
    def test_boot_mismatch(self):
        self.data["jobs"][0]["boot_id"] = "other"
        self.assertEqual(self.result()["status"], "FAIL")
    def test_deadline_equality_is_timely(self):
        self.data["jobs"][0]["deadline_ms"] = self.data["jobs"][0]["consumed_ms"]
        self.assertEqual(self.result()["tasks"]["yolo"]["timely_consumed"], 2)
    def test_no_jobs_is_unknown(self):
        self.data["jobs"] = []
        self.assertEqual(self.result()["status"], "UNKNOWN")

if __name__ == "__main__":
    unittest.main()
