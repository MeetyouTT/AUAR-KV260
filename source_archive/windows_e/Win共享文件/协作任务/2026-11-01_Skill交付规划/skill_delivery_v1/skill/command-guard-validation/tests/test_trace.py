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

mod = load_module("guard_trace", "validate_trace.py")

class GuardTraceTests(unittest.TestCase):
    def setUp(self):
        self.trace = read("examples/trace_pass.json")
        self.profile = read("config/wide_contract.json")
    def result(self):
        return mod.audit(self.trace, self.profile)
    def test_public_positive_and_negative_decisions(self):
        result = self.result()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["accepted_commits"], 2)
        self.assertEqual(result["rejected_commits"], 2)
        self.assertFalse(result["device_accessed"])
    def test_replay_must_not_be_accepted(self):
        self.trace["events"][2]["accepted"] = True
        self.assertIn("replay", " ".join(self.result()["errors"]))
    def test_accepted_out_of_range(self):
        self.trace["events"][0]["target_us"] = 2501
        self.assertEqual(self.result()["status"], "FAIL")
    def test_accepted_lease_out_of_contract(self):
        self.trace["events"][0]["lease_ms"] = 501
        self.assertEqual(self.result()["status"], "FAIL")
    def test_stop_must_clear_arm(self):
        self.trace["events"][6]["armed"] = True
        self.assertIn("still armed", " ".join(self.result()["errors"]))
    def test_missing_stop_is_unknown(self):
        self.trace["events"] = self.trace["events"][:6]
        self.assertEqual(self.result()["status"], "UNKNOWN")
    def test_boot_context_must_match(self):
        self.trace["events"][0]["boot_id"] = "other"
        self.assertEqual(self.result()["status"], "FAIL")
    def test_clock_regression(self):
        self.trace["events"][1]["time_ms"] = -1
        self.assertEqual(self.result()["status"], "FAIL")
    def test_reject_everything_is_not_full_validation(self):
        self.trace["events"] = [
            dict(self.trace["events"][0], accepted=False, reason="fixture_reject"),
            self.trace["events"][6]]
        self.assertEqual(self.result()["status"], "UNKNOWN")
    def test_new_epoch_sequence_is_independent(self):
        self.trace["events"][5]["epoch"] = 2
        self.trace["events"][5]["sequence"] = 1
        self.assertEqual(self.result()["status"], "PASS")
    def test_expiry_does_not_assume_all_flags_zero(self):
        self.trace["events"][4]["flags"] = 8
        self.assertEqual(self.result()["status"], "PASS")
    def test_cli_rejects_bad_saved_trace(self):
        p = subprocess.run([sys.executable, "-B", str(ROOT/"scripts/validate_trace.py"),
                            "--trace", str(ROOT/"examples/trace_fail.json"),
                            "--profile", str(ROOT/"config/wide_contract.json")],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)["status"], "FAIL")

if __name__ == "__main__":
    unittest.main()
