"""Existing public assertions plus targeted two-source regressions. No network."""
import ast
from contextlib import closing
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
BASE = REPAIR / "feature_trigger_collaboration/board_integration_v17/local_runtime_v17"
AURA = HERE.parents[4] / "aura"
SPEC = json.loads((REPAIR / "release_v22_camera_rebind_candidate/camera_rebind_evidence/spec.json").read_bytes())
MANIFEST = json.loads((HERE / "SOURCE_MANIFEST.json").read_bytes())
sys.path.insert(0, str(BASE))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    definition = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(definition)
    sys.modules[name] = module
    definition.loader.exec_module(module)
    return module


for relative, item in MANIFEST["sources"].items():
    assert digest(HERE / "before" / relative) == item["before_sha256"] == SPEC["component_sha256"][relative]
    assert digest(HERE / "after" / relative) == item["after_sha256"]
STORE = load("common.board_memory", HERE / "after/common/board_memory.py")
BEFORE_STORE = load("common.v23_before_memory", HERE / "before/common/board_memory.py")
dialogue = REPAIR / "feature_trigger_collaboration/candidate_h01/after/board/runtime/board_dialogue.py"
assert digest(dialogue) == SPEC["component_sha256"]["board/runtime/board_dialogue.py"]
load("board.runtime.board_dialogue", dialogue)
POLICY = load("board.runtime.board_memory_policy", HERE / "after/board/runtime/board_memory_policy.py")
from common.model_inference_wire import Owner, make_response


class FakeInference:
    def __init__(self, summary):
        self.summary = summary
        self.calls = []

    def request(self, kind, payload, **kwargs):
        assert kind == "llm" and payload["task"] == "summary"
        self.calls.append(payload)
        return make_response(Owner.from_dict(payload), result={"text": json.dumps(
            {"summary": self.summary, "keywords": ["公开测试"]}, ensure_ascii=False)})

    def cancel(self, owner):
        pass


def source(text, metadata=None):
    return dict(source="user_said", text=text, metadata=metadata or {}, include_in_summary=True)


def counts(path):
    with closing(sqlite3.connect(path)) as db:
        return (db.execute("SELECT COUNT(*) FROM bm_bodies").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM bm_summaries").fetchone()[0])


class NegationTests(unittest.TestCase):
    def test_new_bounded_forms_accept_literal_and_reject_affirmative_reversal(self):
        pairs = (("该项未准备就绪。", "该项已准备就绪。"),
                 ("小林未能到场。", "小林已到场。"),
                 ("声纹未校准。", "声纹已校准。"),
                 ("身份未确认。", "身份已确认。"),
                 ("杯子未购买。", "杯子已购买。"),
                 ("指令未执行。", "指令已执行。"),
                 ("声纹无法确认身份。", "声纹可以确认身份。"),
                 ("这并非小林。", "这是小林。"),
                 ("小林并未购买杯子。", "小林已经购买杯子。"),
                 ("小林从未购买杯子。", "小林购买过杯子。"),
                 ("小林未曾购买杯子。", "小林购买过杯子。"),
                 ("小林不再参与。", "小林继续参与。"))
        for negative, affirmative in pairs:
            with self.subTest(negative=negative):
                STORE.validate_compaction_text(negative, [source(negative)])
                with self.assertRaises(STORE.CandidateRejected) as caught:
                    STORE.validate_compaction_text(affirmative, [source(negative)])
                self.assertEqual(("negation_missing",), caught.exception.rejection_reasons)

    def test_all_original_negation_alternatives_remain(self):
        original = BEFORE_STORE.NEGATION.pattern
        self.assertTrue(STORE.NEGATION.pattern.startswith(original + "|"))
        for text in ("没有", "不要", "不能", "不会", "不是", "尚未", "未完成", "不去", "不买", "不做", "not", "never", "no"):
            self.assertIsNotNone(STORE.NEGATION.search(text))

    def test_new_forms_are_explicit_and_not_arbitrary_un_prefix(self):
        for text in ("未来", "未知", "未央", "准备就绪", "校准完成", "确认身份", "可以购买"):
            self.assertIsNone(STORE.NEGATION.search(text))
        self.assertNotIn("未.*", STORE.NEGATION.pattern)

    def test_metadata_negative_original_text_passes_while_missing_negation_rejects(self):
        records = [source("该项未准备就绪。", {"negated": True})]
        with self.assertRaises(BEFORE_STORE.CandidateRejected):
            BEFORE_STORE.validate_compaction_text("该项未准备就绪。", records)
        STORE.validate_compaction_text("该项未准备就绪。", records)
        for value in ("该项准备就绪。", "该项仍待准备。"):
            with self.assertRaises(STORE.CandidateRejected):
                STORE.validate_compaction_text(value, records)

    def test_metadata_only_fragment_remains_a_constraint(self):
        client = POLICY.BoardSummaryClient(None, board_boot_id="public")
        with self.assertRaises(STORE.CandidateRejected):
            client._validate_narrative("只有来源信息。", [source("", {"negated": True})])

    def test_actual_worker_metadata_literal_commits_after_summary_exists(self):
        with tempfile.TemporaryDirectory(prefix="public-v23-metadata-") as directory:
            now = [1000.]
            store = STORE.BoardMemoryStore(Path(directory) / "public.sqlite3", clock=lambda: now[0])
            store.append_event({"kind": "conversation", "id": "public"}, "public-event", "user_said",
                               "该项未准备就绪。", metadata={"negated": True})
            self.assertEqual((1, 0), counts(store.path))
            now[0] = 1400.
            inference = FakeInference("该项未准备就绪。")
            summary = POLICY.BoardSummaryClient(inference, board_boot_id="public")
            worker = STORE.BoardMemoryWorker(store, summary, idle=lambda: True)
            self.assertTrue(worker.step())
            self.assertEqual((0, 1), counts(store.path))
            self.assertEqual(1, len(inference.calls))

    def test_actual_worker_affirmative_reversal_preserves_body(self):
        with tempfile.TemporaryDirectory(prefix="public-v23-rejection-") as directory:
            now = [1000.]
            store = STORE.BoardMemoryStore(Path(directory) / "public.sqlite3", clock=lambda: now[0])
            store.append_event({"kind": "conversation", "id": "public"}, "public-event", "user_said",
                               "声纹未校准，无法确认身份。", metadata={"negated": True})
            now[0] = 1400.
            inference = FakeInference("声纹已校准，可以确认身份。")
            summary = POLICY.BoardSummaryClient(inference, board_boot_id="public")
            self.assertFalse(STORE.BoardMemoryWorker(store, summary, idle=lambda: True).step())
            self.assertEqual((1, 0), counts(store.path))
            self.assertEqual(("negation_missing",), summary.failure_metadata()["rejection_reasons"])


class FragmentTests(unittest.TestCase):
    def fragments(self, text):
        client = POLICY.BoardSummaryClient(None, board_boot_id="public")
        client.metrics = {"input_utf8_bytes": len(text.encode("utf-8"))}
        items = client._fragments([source(text)])
        self.assertEqual(text, "".join(item[0].get("text", "") for item in items))
        self.assertTrue(client.metrics["complete_source_coverage"])
        for batch in client._batches(items):
            self.assertLessEqual(POLICY.message_cost(client._messages([item[0] for item in batch], True), client.reserve), 2048)
        return items

    def assert_protected(self, phrase):
        capacity = len(self.fragments("填" * 500)[0][0]["text"])
        for prefix in range(capacity-len(phrase)-3, capacity+4):
            text = "填" * prefix + phrase + "补" * 400
            items = self.fragments(text)
            boundaries = [item[0]["part_start"] + len(item[0]["text"]) for item in items]
            self.assertFalse(any(prefix < boundary < prefix+len(phrase) for boundary in boundaries),
                             (phrase, prefix, boundaries))

    def test_whole_alternative_questions_never_split(self):
        for phrase in ("去不去", "买不买", "做不做", "要不要", "能不能", "会不会", "是不是", "有没有", "可不可以"):
            with self.subTest(phrase=phrase):
                self.assert_protected(phrase)

    def test_whole_double_negations_and_overlapping_forms_never_split(self):
        for phrase in ("不是不去", "不是不能", "不是没有", "并非没有", "并不是无法", "不是未准备",
                       "是不是不去", "是不是不是不去", "不是不是不去", "不是 不去",
                       "不能不去", "不会不做", "不得不买", "是不是不能不去", "会不会不做"):
            with self.subTest(phrase=phrase):
                self.assert_protected(phrase)

    def test_new_negative_tokens_never_split(self):
        for phrase in MANIFEST["added_bounded_negation_forms"]:
            with self.subTest(phrase=phrase):
                self.assert_protected(phrase)

    def test_unsplittable_expression_refuses_instead_of_truncating(self):
        client = POLICY.BoardSummaryClient(None, board_boot_id="public")
        client.metrics = {"input_utf8_bytes": len("不是不去".encode("utf-8"))}
        with patch.object(client, "_fits", side_effect=lambda records: len(records[0].get("text", "")) <= 2):
            with self.assertRaises(POLICY.ContextLimitError):
                client._fragments([source("不是不去")])


PUBLIC_CASES = json.loads((REPAIR / "memory_negation_stability/PUBLIC_MODEL_PROBE_INPUTS.json").read_bytes())["cases"]
PUBLIC_CASES += json.loads((REPAIR / "performance_review_newboot/memory_negation_v22_review/PUBLIC_MODEL_ADDITIONS.json").read_bytes())["cases"]
FAITHFUL = {
    "question_will": "用户询问会不会唱歌。",
    "question_can": "用户询问能不能识别声纹。",
    "negative_capability": "声纹尚未校准，不能可靠确认身份。",
    "contrasting_subjects": "小林没有喝咖啡，小王已经喝了咖啡。",
    "question_identity": "用户询问是不是雪妃。",
    "cancelled_plan": "小林原计划下午3点买42个杯子，后来取消了，尚未购买。",
    "question_have": "用户询问有没有看到杯子。",
    "metadata_only_negative": "该项未准备就绪。",
    "conditional_negative": "如果小林不能到场，就取消会议；目前尚未确认能否到场。",
    "ordered_plan_cancellation": "小林原计划下午3点买42个杯子，后来取消了这项计划，尚未购买。",
}


class PublicCaseTests(unittest.TestCase):
    def test_two_fixed_330_byte_fragments_fit_reduction_budget(self):
        client = POLICY.BoardSummaryClient(None, board_boot_id="public")
        text = "用户陈述普通背景资料。" * 10
        self.assertEqual(330, len(text.encode("utf-8")))
        records = [dict(source="summary_fragment", text=text), dict(source="summary_fragment", text=text)]
        self.assertLessEqual(POLICY.message_cost(client._messages(records, True), client.reserve), 2048)

    def test_ten_public_inputs_fit_and_faithful_fake_outputs_commit(self):
        self.assertEqual(10, len(PUBLIC_CASES))
        for case in PUBLIC_CASES:
            with self.subTest(case=case["case"]), tempfile.TemporaryDirectory(prefix="public-v23-case-") as directory:
                now = [1000.]
                store = STORE.BoardMemoryStore(Path(directory) / "public.sqlite3", clock=lambda: now[0])
                for index, item in enumerate(case["sources"]):
                    store.append_event({"kind": "conversation", "id": "public"}, "event-"+str(index),
                                       item["source"], item["text"], topic="public", metadata=item["protected"])
                now[0] = 1400.
                inference = FakeInference(FAITHFUL[case["case"]])
                client = POLICY.BoardSummaryClient(inference, board_boot_id="public")
                self.assertTrue(STORE.BoardMemoryWorker(store, client, idle=lambda: True).step())
                self.assertEqual((0, 1), counts(store.path))
                self.assertEqual(1, len(inference.calls))
                self.assertLessEqual(POLICY.message_cost(inference.calls[0]["messages"], client.reserve), 2048)
                prompt = inference.calls[0]["messages"][0]["content"]
                for phrase in ("条件不作事实", "先后状态不混淆", "主客体", "极性", "双重否定不拆", "正反问原词照录"):
                    self.assertIn(phrase, prompt)


def completion_regressions():
    names = ("test_long_closed_source_is_fully_covered_without_transcript_truncation",
             "test_partial_long_summary_never_publishes_or_deletes_source",
             "test_multiple_model_calls_renew_short_leases_only_between_requests",
             "test_irreducible_numeric_source_does_not_starve_other_closed_groups",
             "test_large_fragment_aggregate_is_reduced_without_exceeding_context",
             "test_fragment_boundaries_never_cut_decimal_number_or_protected_name")
    namespace = dict(json=json, re=re, sqlite3=sqlite3, BoardMemoryStore=STORE.BoardMemoryStore,
                     BoardMemoryWorker=STORE.BoardMemoryWorker, NUMBER=STORE.NUMBER, NEGATION=STORE.NEGATION,
                     PLANNED=STORE.PLANNED, BoardSummaryClient=POLICY.BoardSummaryClient,
                     message_cost=POLICY.message_cost, Owner=Owner, make_response=make_response)
    helper_file = AURA / "tests/framework/test_board_memory.py"
    helpers = [node for node in ast.parse(helper_file.read_bytes()).body
               if isinstance(node, ast.ClassDef) and node.name == "Clock"
               or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in ("SCOPE", "OTHER") for target in node.targets)]
    exec(compile(ast.Module(body=helpers, type_ignores=[]), str(helper_file), "exec"), namespace)
    test_file = AURA / "tests/framework/test_board_memory_completion.py"
    nodes = [node for node in ast.parse(test_file.read_bytes()).body
             if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names + ("FragmentClient", "long_text")]
    proof = {}
    for node in nodes:
        node.decorator_list = []
        proof[node.name] = hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
    assert len(nodes) == len(names)+2
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(test_file), "exec"), namespace)
    suite = unittest.TestSuite()
    cleanup = []
    def call_original(function, arguments):
        def run():
            temporary = tempfile.TemporaryDirectory(prefix="public-v23-existing-")
            connections = []
            connect = sqlite3.connect
            def tracked_connect(*args, **kwargs):
                connection = connect(*args, **kwargs)
                connections.append(connection)
                return connection
            try:
                with patch.object(sqlite3, "connect", side_effect=tracked_connect):
                    function(Path(temporary.name), **arguments)
            finally:
                for connection in connections:
                    connection.close()
                temporary.cleanup()
                cleanup.append(not Path(temporary.name).exists())
        return run
    for name in names:
        variants = ({"mode": mode} for mode in ("failure", "new-input", "bad-number", "call-limit")) if "partial_long" in name else ({},)
        for arguments in variants:
            suite.addTest(unittest.FunctionTestCase(call_original(namespace[name], arguments), description=name+str(arguments)))
    return suite, proof, cleanup


def main():
    observation = load("public_v23_observation_tests", REPAIR / "memory_observation_candidate_r2/tests/test_observation_origin.py")
    observation.AFTER = POLICY
    original, ast_proof, cleanup = completion_regressions()
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(observation),
                               original,
                               unittest.defaultTestLoader.loadTestsFromTestCase(NegationTests),
                               unittest.defaultTestLoader.loadTestsFromTestCase(FragmentTests),
                               unittest.defaultTestLoader.loadTestsFromTestCase(PublicCaseTests)))
    before_threads = {thread.ident for thread in threading.enumerate()}
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    leaked = [thread.name for thread in threading.enumerate() if thread.ident not in before_threads]
    dependencies = {}
    mismatches = []
    for name, module in list(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        relative = name.replace(".", "/") + ("/__init__.py" if hasattr(module, "__path__") else ".py")
        if relative not in SPEC["component_sha256"]:
            continue
        expected = MANIFEST["sources"].get(relative, {}).get("after_sha256", SPEC["component_sha256"][relative])
        actual = digest(filename)
        dependencies[name] = dict(relative=relative, sha256=actual)
        if actual != expected:
            mismatches.append(relative)
    unchanged = all(digest(HERE / "after" / relative) == item["after_sha256"] for relative, item in MANIFEST["sources"].items())
    report = dict(status="PASS" if result.wasSuccessful() and not leaked and not mismatches and unchanged else "FAIL",
                  tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                  original_completion_ast=ast_proof, loaded_dependencies=dependencies, dependency_mismatches=mismatches,
                  original_test_fixture_directories_removed=all(cleanup), leaked_threads=leaked,
                  source_bytes_unchanged=unchanged, public_input_cases=10, inference="public_fake_only",
                  private_database_or_model_accessed=False, devices_accessed=False,
                  runner_sha256=digest(__file__))
    (HERE / "PUBLIC_TEST_OUTPUT.txt").write_text(output.getvalue(), encoding="utf-8")
    (HERE / "PUBLIC_TEST_RESULT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "tests_run", "failures", "errors", "skipped", "dependency_mismatches", "leaked_threads")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
