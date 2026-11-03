"""Independent offline checks of exact v23 dispatch and interrupted apply."""
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
CANDIDATE = HERE.parent.parent / "release_v23_memory_summary_candidate"
sys.path.insert(0, str(CANDIDATE))
import summary_common as common
import test_framework as author


class DispatchFixture:
    def __init__(self):
        self.spec = common.proposed()
        self.spec["summary_revision"]["state"] = "APPLIED"
        self.spec["source_manifest_sha256"] = "a" * 64
        camera = self.spec["camera_rebind"]
        summary = self.spec["summary_revision"]
        camera_raw = common.encoded({"applied_spec_sha256": common.BASE_SPEC_SHA})
        summary_raw = common.encoded({"applied_spec_sha256": common.sha(common.encoded(self.spec))})
        self.camera_path = Path(camera["stage"]) / "transaction.json"
        self.summary_path = Path(summary["stage"]) / "transaction.json"
        self.files = {self.camera_path: camera_raw, self.summary_path: summary_raw}
        self.state = dict(target_startup_sha256=self.spec["startup_sha256"],
                          camera_rebind=dict(state="APPLIED", stage=camera["stage"],
                              binding_sha256=common.sha(common.encoded(camera["binding"])),
                              transaction_sha256=common.sha(camera_raw)),
                          summary_revision=dict(state="APPLIED", stage=summary["stage"],
                              payload_sha256=common.sha(common.encoded({name: row["sha256"]
                                  for name, row in summary["payload"]["sources"].items()})),
                              transaction_sha256=common.sha(summary_raw)))
        self.calls = []

    def read(self, path, expected):
        raw = self.files[Path(path)]
        common.need(common.sha(raw) == expected, "public_transaction_pin_changed")
        return raw

    def replace_transaction(self, which, applied_spec_sha):
        path = self.camera_path if which == "camera_rebind" else self.summary_path
        raw = common.encoded({"applied_spec_sha256": applied_spec_sha})
        self.files[path] = raw
        self.state[which]["transaction_sha256"] = common.sha(raw)

    def invoke(self, action):
        tree = ast.parse(common.publisher_remote(self.spec))
        dispatch = [node for node in tree.body if isinstance(node, ast.With)][-1]
        def lifecycle():
            self.calls.append(action)
            return dict(status="PUBLIC_LIFECYCLE_CALLED")
        namespace = dict(ACTION=action, SPEC=self.spec, Path=Path, need=common.need,
                         journal=lambda: copy.deepcopy(self.state), lock=io.BytesIO(),
                         fcntl=types.SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2),
                         c=types.SimpleNamespace(read=self.read, sha=common.sha, encoded=common.encoded, parse=json.loads),
                         start=lifecycle, ready=lifecycle)
        exec(compile(ast.Module(body=dispatch.body, type_ignores=[]), "<exact-public-v23-dispatch>", "exec"), namespace)
        return namespace["result"]


class IndependentTests(unittest.TestCase):
    def fixture(self):
        directory = tempfile.TemporaryDirectory(prefix="public-independent-v23-")
        self.addCleanup(directory.cleanup)
        return author.PublicMemoryFixture(directory.name)

    def test_camera_attests_old_spec_summary_attests_current_spec(self):
        with author.public_selection():
            for action in ("start", "ready"):
                fixture = DispatchFixture()
                self.assertNotEqual(common.BASE_SPEC_SHA, common.sha(common.encoded(fixture.spec)))
                self.assertEqual("PUBLIC_LIFECYCLE_CALLED", fixture.invoke(action)["status"])
                self.assertEqual([action], fixture.calls)

    def test_swapping_camera_and_summary_spec_authority_is_rejected(self):
        with author.public_selection():
            for action in ("start", "ready"):
                for which in ("camera_rebind", "summary_revision"):
                    fixture = DispatchFixture()
                    wrong = common.sha(common.encoded(fixture.spec)) if which == "camera_rebind" else common.BASE_SPEC_SHA
                    fixture.replace_transaction(which, wrong)
                    with self.subTest(action=action, transaction=which), self.assertRaises(ValueError):
                        fixture.invoke(action)
                    self.assertEqual([], fixture.calls)

    def test_summary_marker_must_be_exact_applied_payload(self):
        with author.public_selection():
            for action in ("start", "ready"):
                for field, value in (("state", "INTENT"), ("stage", "/public-other-stage"),
                                     ("payload_sha256", "7" * 64), ("transaction_sha256", "8" * 64)):
                    fixture = DispatchFixture()
                    fixture.state["summary_revision"][field] = value
                    with self.subTest(action=action, field=field), self.assertRaises(ValueError):
                        fixture.invoke(action)
                    self.assertEqual([], fixture.calls)

    def test_prior_camera_binding_and_new_startup_are_still_mandatory(self):
        with author.public_selection():
            for changed in ("binding", "startup"):
                fixture = DispatchFixture()
                if changed == "binding":
                    fixture.state["camera_rebind"]["binding_sha256"] = "9" * 64
                else:
                    fixture.state["target_startup_sha256"] = common.BASE_STARTUP_SHA
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    fixture.invoke("start")
                self.assertEqual([], fixture.calls)

    def test_owner_loss_after_first_target_stops_and_same_intent_recovers(self):
        fixture = self.fixture()
        checkpoint = fixture.checkpoint
        def revoke(name):
            checkpoint(name)
            if name == "replace:memory":
                fixture.owner_valid = False
        fixture.checkpoint = revoke
        with self.assertRaisesRegex(ValueError, "public_owner_changed"):
            fixture.invoke()
        self.assertEqual(fixture.old[1:], [path.read_bytes() for path in fixture.targets[1:]])
        self.assertEqual("SUMMARY_SOURCE_INTENT", fixture.journal()["phase"])
        self.assertFalse(fixture.journal()["guard_removed"])
        fixture.owner_valid = True
        fixture.checkpoint = checkpoint
        self.assertEqual("SUMMARY_MEMORY_SOURCES_APPLIED_UI_STOPPED", fixture.invoke()["status"])

    def test_pause_change_during_apply_stops_without_rewriting_preference(self):
        fixture = self.fixture()
        checkpoint = fixture.checkpoint
        def revoke(name):
            checkpoint(name)
            if name == "replace:memory":
                fixture.pause = True
        fixture.checkpoint = revoke
        with self.assertRaisesRegex(ValueError, "saved_user_pause_required"):
            fixture.invoke()
        self.assertTrue(fixture.pause)
        self.assertEqual(fixture.old[1:], [path.read_bytes() for path in fixture.targets[1:]])
        self.assertFalse(fixture.journal()["guard_removed"])

    def test_external_gui_change_during_apply_blocks_remaining_writes(self):
        fixture = self.fixture()
        checkpoint = fixture.checkpoint
        def change(name):
            checkpoint(name)
            if name == "replace:memory":
                fixture.external.write_bytes(b"PUBLIC_OTHER_GUI_CONFIG")
        fixture.checkpoint = change
        with self.assertRaises(ValueError):
            fixture.invoke()
        self.assertEqual(b"PUBLIC_OTHER_GUI_CONFIG", fixture.external.read_bytes())
        self.assertEqual(fixture.old[1:], [path.read_bytes() for path in fixture.targets[1:]])
        self.assertEqual("SUMMARY_SOURCE_INTENT", fixture.journal()["phase"])

    def test_foreign_selected_file_in_owned_intent_is_never_overwritten(self):
        fixture = self.fixture()
        fixture.fail_at = "replace:memory"
        with self.assertRaises(RuntimeError):
            fixture.invoke()
        fixture.targets[1].write_bytes(b"PUBLIC_UNRELATED_POLICY")
        before = [path.read_bytes() for path in fixture.targets]
        with self.assertRaisesRegex(ValueError, "outside_reviewed_old_new"):
            fixture.invoke()
        self.assertEqual(before, [path.read_bytes() for path in fixture.targets])
        self.assertFalse(fixture.journal()["guard_removed"])

    def test_original_port_release_wait_and_normal_close_bodies_are_exact(self):
        with author.public_selection():
            old = common.v22.publisher_remote(common.baseline())
            new = common.publisher_remote(common.proposed())
        names = ("boot", "ownerless", "_ownerless_process_snapshot", "_control_port_has_listener",
                 "inactive", "writer_and_ui_leases_free", "close", "start", "ready", "ready_state")
        functions = lambda code: {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(code).body
                                  if isinstance(node, ast.FunctionDef)}
        before, after = functions(old), functions(new)
        for name in names:
            self.assertEqual(before[name], after[name])
        self.assertIn("deadline=time.monotonic()+70.0", new)
        self.assertIn("sock.bind(('127.0.0.1',8783))", new)


def source_hashes():
    return {path.name: common.sha(path.read_bytes()) for path in sorted(CANDIDATE.glob("*.py"))}


if __name__ == "__main__":
    before = source_hashes()
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(author),
                               unittest.defaultTestLoader.loadTestsFromTestCase(IndependentTests)))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = source_hashes()
    report = dict(status="PASS" if result.wasSuccessful() and before == after else "FAIL", tests_run=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                  author_sources_unchanged=before == after, source_sha256=after,
                  execution_gate=common.PAYLOAD_FINALIZED, approved_payload_sha256=common.APPROVED_PAYLOAD_SHA,
                  private_database_accessed=False, models_invoked=False, devices_accessed=False,
                  scope="public IO fixtures and exact generated dispatch; real model selection and deployment remain pending",
                  independent_test_sha256=common.sha(Path(__file__).read_bytes()))
    (HERE / "PUBLIC_TEST_OUTPUT.txt").write_text(output.getvalue(), encoding="utf-8")
    (HERE / "PUBLIC_REVIEW_RESULT.json").write_bytes(common.encoded(report))
    print(json.dumps(report, ensure_ascii=True))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
