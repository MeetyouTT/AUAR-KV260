import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_measured_run import audit, read_table


class MeasuredWindowTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / "examples" / "measured"
        self.llm, self.tts, self.gpu = [read_table(folder, f) for f in
            ("llm_cases.csv", "tts_cases.csv", "windows_gpu_timeseries.csv")]
        self.receipt = json.loads((folder / "reference.json").read_text(encoding="utf-8"))

    def check(self):
        return audit(self.llm, self.tts, self.gpu, self.receipt)

    def test_real_window(self):
        result = self.check()
        self.assertEqual(result["admitted_cases"], [1, 2, 3, 5, 6])
        self.assertAlmostEqual(result["tts"]["rpc_ms"]["median"], 718.002261, places=5)
        self.assertEqual(result["device_gpu"]["free_mib"]["min"], 5002)

    def test_skip_is_not_a_measurement(self):
        self.receipt["skipped_cases"] = []
        with self.assertRaises(ValueError):
            self.check()

    def test_cached_call_cannot_join_cohort(self):
        self.tts[0]["cache_hit"] = "True"
        with self.assertRaises(ValueError):
            self.check()

    def test_pcm_samples_must_match_duration(self):
        self.tts[0]["samples"] = "200"
        with self.assertRaises(ValueError):
            self.check()

    def test_duplicate_device_sample(self):
        self.gpu[1]["host_mono"] = self.gpu[0]["host_mono"]
        with self.assertRaises(ValueError):
            self.check()

    def test_changed_token_rate(self):
        self.llm[0]["decode_tokens_per_second"] = "83"
        with self.assertRaises(ValueError):
            self.check()

    def test_changed_receipt(self):
        self.receipt["llm"]["rpc_ms"]["median"] = 50
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
