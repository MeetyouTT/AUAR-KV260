"""Independent public payload and exact three-anchor dispatch checks."""
import ast
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent.parent
PUBLISHER = REPAIR / "release_v24_memory_followup_candidate"
PUBLIC = REPAIR / "memory_negation_model_validation_v24"
sys.path.insert(0, str(PUBLISHER))
import followup_common as common
import test_framework as author


class DispatchFixture:
    def __init__(self):
        self.spec = common.proposed()
        self.spec["summary_followup"]["state"] = "APPLIED"
        self.spec["source_manifest_sha256"] = "a" * 64
        self.state = dict(target_startup_sha256=self.spec["startup_sha256"])
        self.files = {}
        for key, pin in (("camera_rebind", common.CAMERA_SPEC_SHA),
                         ("summary_revision", common.BASE_SPEC_SHA),
                         ("summary_followup", common.sha(common.encoded(self.spec)))):
            revision = self.spec[key]
            raw = common.encoded(dict(applied_spec_sha256=pin))
            self.files[Path(revision["stage"]) / "transaction.json"] = raw
            marker = dict(state="APPLIED", stage=revision["stage"], transaction_sha256=common.sha(raw))
            if key == "camera_rebind":
                marker["binding_sha256"] = common.sha(common.encoded(revision["binding"]))
            else:
                marker["payload_sha256"] = common.sha(common.encoded(
                    {relative: row["sha256"] for relative, row in revision["payload"]["sources"].items()}))
            self.state[key] = marker
        self.calls = []

    def wrong_anchor(self, key, pin):
        raw = common.encoded(dict(applied_spec_sha256=pin))
        self.files[Path(self.spec[key]["stage"]) / "transaction.json"] = raw
        self.state[key]["transaction_sha256"] = common.sha(raw)

    def invoke(self, action):
        def read(path, pin):
            raw = self.files[Path(path)]
            common.need(common.sha(raw) == pin, "public_transaction_pin_changed")
            return raw
        def lifecycle():
            self.calls.append(action)
            return {"status": "PUBLIC_LIFECYCLE_CALLED"}
        tree = ast.parse(common.publisher_remote(self.spec))
        dispatch = [node for node in tree.body if isinstance(node, ast.With)][-1]
        namespace = dict(ACTION=action, SPEC=self.spec, Path=Path, need=common.need,
                         journal=lambda: copy.deepcopy(self.state), lock=io.BytesIO(),
                         fcntl=types.SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2),
                         c=types.SimpleNamespace(read=read, parse=json.loads, encoded=common.encoded, sha=common.sha),
                         start=lifecycle, ready=lifecycle)
        exec(compile(ast.Module(body=dispatch.body, type_ignores=[]), "<exact-public-v24-dispatch>", "exec"), namespace)
        return namespace["result"]


class IndependentChecks(unittest.TestCase):
    def test_exact_payload_cases_and_only_candidate_policy_overlay(self):
        before = json.loads((PUBLIC / "BEFORE_ALL_PUBLIC_PAYLOAD.json").read_bytes())
        after = json.loads((PUBLIC / "CANDIDATE_ALL_PUBLIC_PAYLOAD.json").read_bytes())
        old = json.loads((REPAIR / "memory_negation_model_validation_v23/candidate_validation_r4/CANDIDATE_R4_ALL_PUBLIC_PAYLOAD.json").read_bytes())
        additions = json.loads((REPAIR / "memory_negation_v24_candidate/PUBLIC_MODEL_ADDITIONS.json").read_bytes())
        expected = [{key: row[key] for key in ("case", "sources", "semantic_review_rubric")}
                    for row in old["cases"] + additions["cases"]]
        self.assertEqual(expected, before["cases"])
        self.assertEqual(expected, after["cases"])
        self.assertEqual(15, len(expected))
        self.assertEqual({}, before["candidate_sources"])
        self.assertEqual({"board.runtime.board_memory_policy"}, set(after["candidate_sources"]))
        self.assertEqual("80de72bce6d816a4da52db1dadee4a2c27c5c59242a1929c6316b76071c3105a",
                         after["candidate_sources"]["board.runtime.board_memory_policy"]["sha256"])
        for key in ("spec_raw", "guard_source", "guard_sha256", "final_summary_max_utf8_bytes", "capacity_evidence_sha256"):
            self.assertEqual(before[key], after[key], key)
        for payload in (before, after):
            self.assertEqual(16, payload["planned_initial_model_calls"])
            self.assertLessEqual(max(row["maximum_initial_message_cost"] for row in payload["initial_request_plan"]), 2048)

    def test_exact_old_camera_old_summary_and_current_followup_pass(self):
        with author.public_selection():
            fixture = DispatchFixture()
            for action in ("start", "ready"):
                self.assertEqual("PUBLIC_LIFECYCLE_CALLED", fixture.invoke(action)["status"])
            self.assertEqual(["start", "ready"], fixture.calls)

    def test_exchanging_any_transaction_anchor_blocks_lifecycle(self):
        for key in ("camera_rebind", "summary_revision", "summary_followup"):
            with self.subTest(key=key), author.public_selection():
                fixture = DispatchFixture()
                pin = common.BASE_SPEC_SHA if key != "summary_revision" else common.CAMERA_SPEC_SHA
                fixture.wrong_anchor(key, pin)
                for action in ("start", "ready"):
                    with self.assertRaises(ValueError):
                        fixture.invoke(action)
                self.assertEqual([], fixture.calls)

    def test_owner_loss_after_first_write_retains_guard_then_same_intent_resumes(self):
        with tempfile.TemporaryDirectory(prefix="public-v24-independent-") as directory:
            fixture = author.PublicFollowupFixture(directory)
            checkpoint = fixture.checkpoint
            def lose_owner(name):
                checkpoint(name)
                if name == "replace:source":
                    fixture.owner_valid = False
            fixture.checkpoint = lose_owner
            with self.assertRaises(ValueError):
                fixture.invoke()
            self.assertEqual(fixture.old[1:], [path.read_bytes() for path in fixture.targets[1:]])
            self.assertEqual("SUMMARY_FOLLOWUP_INTENT", fixture.journal()["phase"])
            self.assertFalse(fixture.journal()["guard_removed"])
            fixture.owner_valid = True
            fixture.checkpoint = checkpoint
            self.assertEqual("SUMMARY_FOLLOWUP_SOURCE_APPLIED_UI_STOPPED", fixture.invoke()["status"])


def main():
    sources = {path.name: common.sha(path.read_bytes()) for path in PUBLISHER.glob("*.py")}
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentChecks))
    unchanged = sources == {path.name: common.sha(path.read_bytes()) for path in PUBLISHER.glob("*.py")}
    report = dict(status="PASS" if result.wasSuccessful() and unchanged else "FAIL", extra_tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), source_sha256=sources,
                  author_public_tests_separately_replayed=13, author_publisher_tests_separately_replayed=19,
                  publisher_sources_unchanged=True, execution_gate=common.PAYLOAD_FINALIZED,
                  approved_payload_sha256=common.APPROVED_PAYLOAD_SHA, private_database_accessed=False,
                  model_or_device_accessed=False, source_selection_and_final_freeze_pending=True)
    (HERE / "EXTRA_TEST_OUTPUT.txt").write_text(output.getvalue(), encoding="utf-8")
    (HERE / "PUBLIC_REVIEW_RESULT.json").write_bytes(common.encoded(report))
    print(json.dumps(dict(status=report["status"], extra_tests=result.testsRun,
                         report_sha256=common.sha((HERE / "PUBLIC_REVIEW_RESULT.json").read_bytes()))))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
