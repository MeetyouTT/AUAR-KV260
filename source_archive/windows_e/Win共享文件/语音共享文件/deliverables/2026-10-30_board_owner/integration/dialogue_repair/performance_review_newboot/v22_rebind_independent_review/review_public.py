"""Offline public proof of the camera-owner rebind transaction and dispatch."""
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
CANDIDATE = HERE.parent.parent / "release_v22_camera_rebind_candidate"
sys.path.insert(0, str(CANDIDATE))
import rebind_common as common
import test_rebind as author
import seal_rebind


class DispatchFixture:
    def __init__(self):
        self.spec = author.public_applied()
        transaction = {"applied_spec_sha256": common.sha(common.encoded(self.spec))}
        self.raw = common.encoded(transaction)
        self.state = {
            "target_startup_sha256": self.spec["startup_sha256"],
            "camera_rebind": {
                "state": "APPLIED",
                "stage": self.spec["camera_rebind"]["stage"],
                "binding_sha256": common.sha(common.encoded(self.spec["camera_rebind"]["binding"])),
                "transaction_sha256": common.sha(self.raw),
            },
        }
        self.calls = []

    def read(self, path, expected):
        self.assert_transaction_path(path)
        common.need(common.sha(self.raw) == expected, "public_transaction_pin_changed")
        return self.raw

    def assert_transaction_path(self, path):
        common.need(path == Path(self.spec["camera_rebind"]["stage"]) / "transaction.json",
                    "public_exact_transaction_path_required")

    def invoke(self, action):
        tree = ast.parse(common.publisher_remote(self.spec))
        dispatch = [node for node in tree.body if isinstance(node, ast.With)][-1]
        def lifecycle():
            self.calls.append(action)
            return {"status": "PUBLIC_LIFECYCLE_CALLED"}
        namespace = dict(
            ACTION=action, SPEC=self.spec, Path=Path, need=common.need,
            journal=lambda: copy.deepcopy(self.state), lock=io.BytesIO(),
            fcntl=types.SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2),
            c=types.SimpleNamespace(sha=common.sha, encoded=common.encoded, parse=json.loads, read=self.read),
            start=lifecycle, ready=lifecycle,
        )
        # Execute the exact generated locked dispatch body. No remote globals,
        # imports, SSH, filesystem locks or service actions are executed.
        exec(compile(ast.Module(body=dispatch.body, type_ignores=[]), "<public-exact-dispatch>", "exec"), namespace)
        return namespace["result"]


class IndependentTests(unittest.TestCase):
    def fixture(self):
        directory = tempfile.TemporaryDirectory(prefix="public-independent-rebind-")
        self.addCleanup(directory.cleanup)
        return author.PublicApplyFixture(directory.name)

    def test_start_and_ready_require_exact_applied_transaction(self):
        for action in ("start", "ready"):
            fixture = DispatchFixture()
            with self.subTest(action=action):
                self.assertEqual("PUBLIC_LIFECYCLE_CALLED", fixture.invoke(action)["status"])
                self.assertEqual([action], fixture.calls)

    def test_start_and_ready_reject_each_unbound_marker(self):
        for action in ("start", "ready"):
            for field, value in (("state", "INTENT"), ("stage", "/public-other"),
                                 ("binding_sha256", "7" * 64), ("transaction_sha256", "8" * 64)):
                fixture = DispatchFixture()
                fixture.state["camera_rebind"][field] = value
                with self.subTest(action=action, field=field), self.assertRaises(ValueError):
                    fixture.invoke(action)
                self.assertEqual([], fixture.calls)

    def test_start_and_ready_reject_other_applied_spec_and_startup(self):
        for action in ("start", "ready"):
            for field in ("applied_spec", "startup"):
                fixture = DispatchFixture()
                if field == "applied_spec":
                    fixture.raw = common.encoded({"applied_spec_sha256": "9" * 64})
                    fixture.state["camera_rebind"]["transaction_sha256"] = common.sha(fixture.raw)
                else:
                    fixture.state["target_startup_sha256"] = "9" * 64
                with self.subTest(action=action, field=field), self.assertRaises(ValueError):
                    fixture.invoke(action)
                self.assertEqual([], fixture.calls)

    def test_loss_of_owner_after_first_target_stops_then_recovers(self):
        fixture = self.fixture()
        checkpoint = fixture.checkpoint
        def revoke(name):
            checkpoint(name)
            if name == "replace:gui":
                fixture.owner_valid = False
        fixture.checkpoint = revoke
        with self.assertRaisesRegex(ValueError, "public_owner_changed"):
            fixture.invoke()
        self.assertEqual(["replace:gui"], [name for name in fixture.events if name.startswith("replace:")])
        self.assertEqual("CAMERA_REBIND_INTENT", fixture.journal()["phase"])
        self.assertFalse(fixture.journal()["guard_removed"])
        fixture.owner_valid = True
        fixture.checkpoint = checkpoint
        result = fixture.invoke()
        self.assertEqual("CAMERA_OWNER_REBOUND_UI_STOPPED", result["status"])
        self.assertEqual(fixture.old[0], fixture.external.read_bytes())

    def test_pause_change_after_first_target_stops_without_rewriting_preference(self):
        fixture = self.fixture()
        checkpoint = fixture.checkpoint
        def revoke(name):
            checkpoint(name)
            if name == "replace:gui":
                fixture.pause = True
        fixture.checkpoint = revoke
        with self.assertRaisesRegex(ValueError, "saved_user_pause_required"):
            fixture.invoke()
        self.assertTrue(fixture.pause)
        self.assertEqual(["replace:gui"], [name for name in fixture.events if name.startswith("replace:")])
        self.assertFalse(fixture.journal()["guard_removed"])

    def test_other_product_change_after_first_target_stops_then_recovers(self):
        fixture = self.fixture()
        checkpoint = fixture.checkpoint
        component = next(path for path in fixture.readonly if path.endswith("component_0.py"))
        original = fixture.readonly[component]
        def corrupt(name):
            checkpoint(name)
            if name == "replace:gui":
                fixture.readonly[component] = b"PUBLIC_FOREIGN_COMPONENT"
        fixture.checkpoint = corrupt
        with self.assertRaisesRegex(ValueError, "public_pin_mismatch"):
            fixture.invoke()
        self.assertEqual(["replace:gui"], [name for name in fixture.events if name.startswith("replace:")])
        fixture.readonly[component] = original
        fixture.checkpoint = checkpoint
        self.assertEqual("CAMERA_OWNER_REBOUND_UI_STOPPED", fixture.invoke()["status"])

    def test_seal_refuses_integer_boolean_aliases(self):
        mutations = (("saved_listening_preference", "version", True),
                     ("saved_listening_preference", "enabled", 0),
                     ("listening", "enabled", 0), ("listening", "microphone_open", 0))
        for section, field, value in mutations:
            spec, ready, installed, mapping, _ = author.public_seal_inputs()
            mapping[section][field] = value
            with self.subTest(section=section, field=field), self.assertRaises(ValueError):
                seal_rebind.validate_mapping(mapping, spec, ready, installed)


def candidate_pins():
    return {path.name: common.sha(path.read_bytes()) for path in sorted(CANDIDATE.glob("*.py"))}


if __name__ == "__main__":
    before = candidate_pins()
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(author),
                               unittest.defaultTestLoader.loadTestsFromTestCase(IndependentTests)))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    after = candidate_pins()
    report = dict(status="PASS" if result.wasSuccessful() and before == after else "FAIL",
                  tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  skipped=len(result.skipped), author_sources_unchanged=before == after,
                  candidate_source_sha256=after, independent_test_sha256=common.sha(Path(__file__).read_bytes()),
                  private_data_opened=False, device_accessed=False, models_invoked=False,
                  scope="offline exact apply function, locked dispatcher and metadata seal with public IO fixtures")
    (HERE / "PUBLIC_REVIEW_RESULT.json").write_bytes(common.encoded(report))
    (HERE / "PUBLIC_TEST_OUTPUT.txt").write_text(stream.getvalue(), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
