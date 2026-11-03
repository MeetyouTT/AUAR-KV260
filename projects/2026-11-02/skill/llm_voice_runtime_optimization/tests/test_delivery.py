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

mod = load_module("delivery_trace", "validate_delivery_trace.py")

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.data = read("examples/delivery_pass.json")
    def result(self):
        return mod.audit(self.data)
    def test_public_ack_and_validated_summary_chain(self):
        r = self.result()
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["accepted_complete_acks"], 1)
        self.assertEqual(r["validated_summaries"], 1)
        self.assertFalse(r["actual_semantic_recall_verified"])
    def test_wrong_pcm_hash_cannot_be_confirmed(self):
        self.data["events"][4]["sha256"] = "f"*64
        self.assertIn("mismatched", " ".join(self.result()["errors"]))
    def test_wrong_samples_cannot_be_confirmed(self):
        self.data["events"][4]["samples"] = 33
        self.assertEqual(self.result()["status"], "FAIL")
    def test_missing_segment_prevents_complete_ack(self):
        del self.data["events"][3]
        self.assertEqual(self.result()["status"], "FAIL")
    def test_duplicate_accepted_segment_rejected(self):
        self.data["events"][3]["segment_index"] = 0
        self.assertEqual(self.result()["status"], "FAIL")
    def test_cancelled_result_cannot_be_accepted(self):
        self.data["events"].insert(4, {"kind":"cancel","time_ms":12,"scope":"public_scope_a",
                                      "request_id":"public_r1","generation":1})
        self.assertIn("cancelled", " ".join(self.result()["errors"]))
    def test_expired_ack_rejected(self):
        self.data["events"][0]["deadline_ms"] = 15
        self.assertEqual(self.result()["status"], "FAIL")
    def test_cross_scope_ack_rejected(self):
        self.data["events"][4]["scope"] = "other_scope"
        self.assertEqual(self.result()["status"], "FAIL")
    def test_assistant_memory_cannot_precede_playback_ack(self):
        event = self.data["events"].pop(5)
        event["time_ms"] = 12
        self.data["events"].insert(4, event)
        self.assertEqual(self.result()["status"], "FAIL")
    def test_raw_body_cannot_be_deleted_before_valid_summary(self):
        self.data["events"][7]["summary_id"] = "not_committed"
        self.assertIn("raw deletion", " ".join(self.result()["errors"]))
    def test_summary_requires_semantic_validation_marker(self):
        self.data["events"][6]["validated"] = False
        self.assertEqual(self.result()["status"], "FAIL")
    def test_invalidated_source_cannot_be_resurrected(self):
        self.data["events"][9]["accepted"] = True
        self.assertIn("stale", " ".join(self.result()["errors"]))
    def test_unauthorized_memory_read_rejected(self):
        self.data["events"].insert(6, {"kind":"memory_read","time_ms":22,"scope":"public_scope_a",
                                      "request_id":"public_r1","generation":1,
                                      "accepted":True,"authorized":False})
        self.assertIn("unauthorized", " ".join(self.result()["errors"]))
    def test_no_positive_ack_is_unknown(self):
        self.data["events"] = [self.data["events"][0]]
        self.assertEqual(self.result()["status"], "UNKNOWN")
    def test_missing_input_provenance_is_unknown(self):
        del self.data["events"][0]["source_dependencies"]
        self.assertEqual(self.result()["status"], "UNKNOWN")
    def test_invalidation_blocks_inflight_result(self):
        new_request = copy.deepcopy(self.data["events"][0])
        new_request.update(request_id="public_r2", time_ms=22,
                           source_dependencies=[{"source_id":"public_user_1", "version":1}])
        invalidation = {"kind":"source_invalidate", "time_ms":23, "scope":"public_scope_a",
                        "source_id":"public_user_1"}
        chunk = {"kind":"chunk_decision", "time_ms":24, "scope":"public_scope_a",
                 "request_id":"public_r2", "generation":1, "accepted":True, "segment_index":0}
        self.data["events"] = self.data["events"][:6] + [new_request, invalidation, chunk]
        self.assertIn("stale", " ".join(self.result()["errors"]))

if __name__ == "__main__":
    unittest.main()
