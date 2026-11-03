"""Final frozen v23 byte/AST and public-fixture review. No device access."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent.parent
PACKAGE = REPAIR / "release_v23_memory_summary_candidate"
PRIOR = HERE.parent / "v23_publisher_independent_review"
EXPECTED = {
    "summary_common.py": "7b7227447bee67e38ed4371fc4d58979bdf56f2f36c3745c8fdd934e012d6a25",
    "test_framework.py": "bbc9bc22e6ba86884d9489888779d59b31c982885419317d69dc559801374e89",
    "apply_runtime.py": "5bb3c71da9a7a2907e9e580110d9af4a3dc83481bbd8b9ca827e1664d102dad4",
    "apply_summary_closed.py": "14e9355d2c96e9d5dd68cab5d6d4531f397548893800b43d2c356265f5003657",
    "prepare_summary.py": "053056e004908e950045a4e91c4e8b275d3039d062de9e0341f0696c319b2ae7",
    "publish_summary.py": "2160d1742a45297142a4b504480a6a9979f4c3791385e419a0a6aefb62f15429",
    "rollforward.py": "e44779489c356ab0709cad90b23e3de53631dd7635b48844900dd2ed2004a3d5",
    "seal_summary.py": "99a5906d2412216df0a45ccd9cc9fcb122c35c1b976bf2b9d48638eb7cfb1ef2",
}
PAYLOAD_SHA = "7a44c5d9fa115fa4be319184b215b8f1c4fd0e92746bd9f9aee15a0991c3e809"
DECISION_SHA = "8925ca91287561dc756b1aecd2874f57d7d1f5c0b97cbd66d6642e85ec527657"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def static_checks():
    for name, pin in EXPECTED.items():
        assert file_sha(PACKAGE / name) == pin, name
    raw = (PACKAGE / "summary_common.py").read_bytes()
    restored = raw.replace(b"PAYLOAD_FINALIZED = True", b"PAYLOAD_FINALIZED = False")
    restored = restored.replace(("APPROVED_PAYLOAD_SHA = '" + PAYLOAD_SHA + "'").encode(),
                                b"APPROVED_PAYLOAD_SHA = None")
    assert sha(restored) == "bf2d9c7570a8c70fc05bdd55bfaa7022b1059b279bb4ca7d46e0d028f5874840"
    tree = ast.parse(raw)
    gates = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("PAYLOAD_FINALIZED", "APPROVED_PAYLOAD_SHA"):
                gates[name] = ast.literal_eval(node.value)
                node.value = ast.Constant(value=None)
    assert gates == dict(PAYLOAD_FINALIZED=True, APPROVED_PAYLOAD_SHA=PAYLOAD_SHA)
    assert sha(ast.dump(tree, include_attributes=False).encode()) == "bb863ec0921c33a2ad5c8bce798ea1eda5a76f0ece42d7dfaa2305535dc3a19b"
    text = (PACKAGE / "test_framework.py").read_bytes().decode("utf-8")
    method = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef)
                  and n.name == "test_unselected_package_refuses_proposal_and_execution")
    lines = text.splitlines(keepends=True)
    old = """    def test_unselected_package_refuses_proposal_and_execution(self):
        self.assertIs(common.PAYLOAD_FINALIZED, False)
        self.assertIsNone(common.APPROVED_PAYLOAD_SHA)
        with self.assertRaisesRegex(ValueError, 'selection_pending'):
            common.proposed()
        with self.assertRaisesRegex(ValueError, 'final_root_selected'):
            common.execute_remote('', {})
"""
    old_text = "".join(lines[:method.lineno - 1]) + old + "".join(lines[method.end_lineno:])
    assert sha(old_text.encode()) == "f6fb2960ce72bda3bb74e011a2825e4fde1eca2f10312933b9e57a125db8e8c4"
    assert file_sha(PACKAGE / "APPROVED_PAYLOAD.json") == PAYLOAD_SHA
    selected = json.loads((PACKAGE / "APPROVED_PAYLOAD.json").read_bytes())
    assert selected["decision"]["sha256"] == DECISION_SHA
    assert file_sha(selected["decision"]["path"]) == DECISION_SHA
    decision = json.loads(Path(selected["decision"]["path"]).read_bytes())
    assert decision["status"] == "ROOT_SELECTS_R4_FOR_GUARDED_TWO_SOURCE_DEPLOYMENT"
    assert decision["selected_sources"] == selected["sources"]
    assert decision["actual_public_comparison"]["after_cases_accepted"] == 11
    assert decision["root_semantic_review"]["cases_passed"] == 11
    for evidence in decision["evidence"]:
        assert file_sha(evidence["path"]) == evidence["sha256"], evidence["path"]
    for row in selected["sources"].values():
        assert file_sha(row["local_source"]) == row["sha256"]
    return selected


def main():
    selected = static_checks()
    definition = importlib.util.spec_from_file_location("prior_independent_v23", PRIOR / "review_public.py")
    review = importlib.util.module_from_spec(definition)
    sys.modules[definition.name] = review
    definition.loader.exec_module(review)
    common = review.common
    assert common.approved_payload() == selected
    base, spec = common.baseline(), common.proposed()
    proposed_path = PACKAGE / "proposed_spec_1793514342921841100.json"
    assert file_sha(proposed_path) == "7cac13357b51743e4d6b048939019ebd1117b961e5b7e84419e034916b9d24e8"
    assert json.loads(proposed_path.read_bytes()) == spec
    assert spec["startup_sha256"] == "d848dc90cf9a890fb8bc66b2c494b78c2ae39a7e22a4743fe0ab917ca3edbae8"
    assert len(spec["component_sha256"]) == 380
    changed = [name for name in spec["component_sha256"] if spec["component_sha256"][name] != base["component_sha256"][name]]
    assert set(changed) == {"common/board_memory.py", "board/runtime/board_memory_policy.py"}
    for name in ("configuration_sha256", "minor_prepared_configuration_path", "camera_owner", "camera_rebind",
                 "face_readback", "expected_final_listening_enabled"):
        assert spec[name] == base[name], name
    functions = lambda code: {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(code).body
                             if isinstance(node, ast.FunctionDef)}
    remote = common.publisher_remote(spec)
    assert functions(remote) == functions(common.publisher_remote(base))
    for code in (remote, review.author.apply_summary_closed.build_remote(spec), review.author.seal_summary.build_remote(spec)):
        ast.parse(code, feature_version=(3, 9))
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(review.author),
                               unittest.defaultTestLoader.loadTestsFromTestCase(review.IndependentTests)))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    static_checks()
    assert common.PAYLOAD_FINALIZED is True and common.APPROVED_PAYLOAD_SHA == PAYLOAD_SHA
    report = dict(status="PASS" if result.wasSuccessful() else "FAIL", tests_run=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                  source_sha256=EXPECTED, common_only_two_gate_values_changed=True,
                  common_exact_byte_reversal_to_reviewed_before=True, test_only_first_case_mock_changed=True,
                  test_exact_byte_reversal_to_reviewed_before=True, approved_payload_sha256=PAYLOAD_SHA,
                  decision_sha256=DECISION_SHA, root_evidence_files_match=True,
                  component_count=380, changed_components=sorted(changed),
                  configuration_camera_and_paused_authority_unchanged=True, lifecycle_function_ast_unchanged=True,
                  code_bytes_unchanged_by_tests=True, execution_gate=True,
                  private_database_accessed=False, models_invoked=False, devices_accessed=False,
                  independent_test_sha256=file_sha(__file__))
    (HERE / "PUBLIC_TEST_OUTPUT.txt").write_text(output.getvalue(), encoding="utf-8")
    (HERE / "FINAL_REVIEW_RESULT.json").write_bytes(common.encoded(report))
    print(json.dumps(dict(status=report["status"], tests_run=result.testsRun, failures=len(result.failures),
                         errors=len(result.errors), report_sha256=file_sha(HERE / "FINAL_REVIEW_RESULT.json"))))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
