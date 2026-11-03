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

mod = load_module("dpu_metadata", "validate_metadata.py")

class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.meta = read("examples/sface_metadata.json")
        self.profiles = read("config/model_profiles.json")
    def result(self, artifact=None):
        return mod.audit(self.meta, self.profiles, "sface", artifact)
    def dpu(self):
        return next(x for x in self.meta["partitions"] if x["device"] == "DPU")
    def test_two_frozen_model_metadata_examples(self):
        for kind in ("sface", "yunet"):
            result = mod.audit(read("examples/"+kind+"_metadata.json"), self.profiles, kind)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["artifact_check"], "NOT_RUN")
            self.assertFalse(result["inference_executed"])
    def test_fingerprint_mismatch(self):
        self.dpu()["fingerprint"] = "0xdead"
        self.assertIn("fingerprint", " ".join(self.result()["errors"]))
    def test_shape_mismatch(self):
        self.dpu()["inputs"][0]["dims"] = [1, 80, 80, 3]
        self.assertEqual(self.result()["status"], "FAIL")
    def test_quantization_interface_mismatch(self):
        self.dpu()["inputs"][0]["fix_point"] = 0
        self.assertEqual(self.result()["status"], "FAIL")
    def test_wrong_model_version(self):
        self.meta["sha256"] = "a"*64
        self.assertEqual(self.result()["status"], "FAIL")
    def test_missing_dpu_partition(self):
        self.meta["partitions"] = [p for p in self.meta["partitions"] if p["device"] != "DPU"]
        self.assertEqual(self.result()["status"], "FAIL")
    def test_cpu_partitions_are_reported_not_hidden(self):
        self.assertGreater(self.result()["cpu_partitions"], 0)
        self.assertFalse(self.result()["runtime_backend_verified"])
    def test_speaker_mapping_pending(self):
        result = mod.audit(self.meta, self.profiles, "speaker")
        self.assertEqual(result["status"], "UNKNOWN")
    def test_missing_interface_is_unknown(self):
        self.dpu()["inputs"] = []
        self.assertEqual(self.result()["status"], "UNKNOWN")
    def test_wrong_artifact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"wrong.xmodel"
            path.write_bytes(b"not a model")
            self.assertEqual(self.result(path)["status"], "FAIL")
    def test_inspector_envelope_and_shape_spelling(self):
        for part in self.meta["partitions"]:
            for tensor in part.get("inputs", []):
                tensor["shape"] = tensor.pop("dims")
        result = mod.audit({"models":[self.meta]}, self.profiles, "sface")
        self.assertEqual(result["status"], "PASS")
    def test_cli_reads_real_saved_metadata_without_xir(self):
        p = subprocess.run([sys.executable, "-B", str(ROOT/"scripts/validate_metadata.py"),
                            "--metadata", str(ROOT/"examples/sface_metadata.json"),
                            "--profiles", str(ROOT/"config/model_profiles.json"),
                            "--model-kind", "sface"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertFalse(json.loads(p.stdout)["inference_executed"])

if __name__ == "__main__":
    unittest.main()
