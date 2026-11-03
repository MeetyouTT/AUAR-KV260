"""Read-only source audit with public validator and fragment counterexamples."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import threading
import time
import uuid


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent.parent
ORIGINAL = REPAIR / "memory_negation_stability"
STORE_PATH = REPAIR / "release_v20_identity_history_candidate/payload/common/board_memory.py"
POLICY_PATH = REPAIR / "memory_observation_candidate_r2/after/board/runtime/board_memory_policy.py"
CANDIDATE_PATH = ORIGINAL / "prompt_candidate/after/board/runtime/board_memory_policy.py"
SPEC_PATH = REPAIR / "release_v22_camera_rebind_candidate/camera_rebind_evidence/spec.json"
PINS = {
    "common/board_memory.py": "05095d249caf3598802d5951910b412affe167b508933c7e831e3ffacc4fc0d0",
    "board/runtime/board_memory_policy.py": "410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5",
    "candidate": "ef45290c89ec72fcbcaf0a0ceac7dd76816ea5f3e59099477fe77f5d38b52825",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def exact_definitions(path, names, namespace):
    tree = ast.parse(path.read_bytes())
    selected = []
    found = set()
    for node in tree.body:
        name = getattr(node, "name", None)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        if name in names:
            selected.append(node)
            found.add(name)
    assert found == set(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return {getattr(node, "name", node.targets[0].id if isinstance(node, ast.Assign) else ""): sha(
        ast.dump(node, include_attributes=False).encode()) for node in selected}


def load_policy(path, store):
    namespace = dict(store, json=json, re=re, threading=threading, time=time, uuid=uuid)
    proof = exact_definitions(path, {"ContextLimitError", "message_cost", "BoardSummaryClient"}, namespace)
    return namespace, proof


def source(text, metadata=None):
    return dict(source="user_said", text=text, metadata=metadata or {}, include_in_summary=True)


def checked(store, text, sources):
    try:
        store["validate_compaction_text"](text, sources)
        return dict(accepted=True, reasons=[])
    except store["CandidateRejected"] as error:
        return dict(accepted=False, reasons=list(error.rejection_reasons))


def fragment_cut(namespace, phrase):
    client = namespace["BoardSummaryClient"](None, board_boot_id="public-offline-only")
    for prefix in range(1, 600):
        text = "填" * prefix + phrase + "补" * 400
        client.metrics = {"input_utf8_bytes": len(text.encode("utf-8"))}
        fragments = client._fragments([source(text)])
        boundaries = [entry[0]["part_start"] + len(entry[0]["text"]) for entry in fragments]
        cuts = [offset for offset in boundaries if prefix < offset < prefix + len(phrase)]
        if cuts:
            boundary = cuts[0]
            batches = list(client._batches(fragments))
            return dict(prefix_characters=prefix, phrase=phrase, phrase_start=prefix,
                        split_offset_in_phrase=boundary-prefix, first_piece=phrase[:boundary-prefix],
                        second_piece=phrase[boundary-prefix:], fragment_count=len(fragments),
                        batch_count=len(batches), all_bytes_covered=client.metrics["complete_source_coverage"],
                        max_request_cost=max(namespace["message_cost"](
                            client._messages([item[0] for item in batch], True), client.reserve) for batch in batches))
    raise AssertionError("Expected public split boundary was not reproduced")


def main():
    assert sha(STORE_PATH.read_bytes()) == PINS["common/board_memory.py"]
    assert sha(POLICY_PATH.read_bytes()) == PINS["board/runtime/board_memory_policy.py"]
    assert sha(CANDIDATE_PATH.read_bytes()) == PINS["candidate"]
    spec = json.loads(SPEC_PATH.read_bytes())
    assert all(spec["component_sha256"][key] == value for key, value in PINS.items() if key != "candidate")
    store = dict(re=re)
    store_ast = exact_definitions(STORE_PATH,
        {"NEGATION", "PLANNED", "COMPLETED", "OBSERVED", "NUMBER", "COMPACTION_REJECTION_REASONS",
         "CandidateRejected", "_text", "validate_compaction_text"}, store)
    before, before_ast = load_policy(POLICY_PATH, store)
    candidate, candidate_ast = load_policy(CANDIDATE_PATH, store)
    cases = [
        ("have_question_paraphrase", source("你有没有看到杯子？"), "用户询问是否看到杯子。", False,
         "faithful_question_paraphrase_rejected"),
        ("have_question_original_form", source("你有没有看到杯子？"), "用户询问有没有看到杯子。", True,
         "faithful_question_original_form"),
        ("metadata_negative_literal", source("该项未准备就绪。", {"negated": True}), "该项未准备就绪。", False,
         "faithful_literal_rejected_even_with_original_negative_expression"),
        ("metadata_negative_semantic_rephrase", source("该项未准备就绪。", {"negated": True}), "该项尚未准备就绪。", True,
         "faithful_explicit_incomplete_state"),
        ("double_negative_scope_loss", source("小林不是不去，只是还没确定时间。", {"names": ["小林"]}), "小林不去。", True,
         "wrong_double_negative_scope_mechanically_accepted"),
        ("quantifier_scope_loss", source("不是所有杯子都坏了。"), "所有杯子都不是坏的。", True,
         "wrong_not_all_to_none_mechanically_accepted"),
        ("conditional_to_fact", source("如果小林不能到场，就取消会议；目前还没确认能否到场。", {"names": ["小林"]}),
         "小林不能到场，会议取消。", True, "wrong_condition_to_confirmed_fact_mechanically_accepted"),
    ]
    results = []
    for name, item, text, expected, semantics in cases:
        result = checked(store, text, [item])
        assert result["accepted"] is expected
        results.append(dict(case=name, public_source=item, public_candidate=text, semantic_review=semantics, **result))
    timeline = [source("小林计划下午3点买42个杯子。", {"names": ["小林"], "numbers": [3, 42], "status": "planned"}),
                source("小林后来取消了这项购买计划，尚未购买。", {"names": ["小林"], "status": "cancelled", "negated": True})]
    timeline_bad = "小林计划下午3点买42个杯子，尚未取消。"
    result = checked(store, timeline_bad, timeline)
    assert result["accepted"] is True
    results.append(dict(case="timeline_cancellation_reversed", public_sources=timeline, public_candidate=timeline_bad,
                        semantic_review="wrong_cancelled_to_not_cancelled_mechanically_accepted", **result))
    cuts = {label: [fragment_cut(namespace, phrase) for phrase in ("能不能", "有没有", "不是不去")]
            for label, namespace in (("before", before), ("candidate", candidate))}
    original_probes = json.loads((ORIGINAL / "PUBLIC_MODEL_PROBE_INPUTS.json").read_bytes())
    assert len(original_probes["cases"]) == 6
    assert all(len(case["sources"]) == 1 for case in original_probes["cases"])
    additions = [
        ("question_have", [source("你有没有看到杯子？")],
         "保持询问及有没有形式，不写成已经看到或没有看到。"),
        ("metadata_only_negative", [source("该项未准备就绪。", {"negated": True})],
         "保持尚未准备就绪的状态，不补写无关否定或相反状态；另检查现有negation_missing是否仍拒绝。"),
        ("conditional_negative", [source("如果小林不能到场，就取消会议；目前还没确认能否到场。", {"names": ["小林"]})],
         "保留如果条件、到场状态尚未确认、取消会议尚未发生；不能把条件写成事实。"),
        ("ordered_plan_cancellation", timeline,
         "保留小林、3点、42个杯子，以及先计划、后取消、尚未购买的时间顺序和最终状态。"),
    ]
    probes = []
    for name, sources, rubric in additions:
        exported = [dict(source=item["source"], text=item["text"], protected=item["metadata"]) for item in sources]
        old_client = before["BoardSummaryClient"](None, board_boot_id="public-offline-only")
        new_client = candidate["BoardSummaryClient"](None, board_boot_id="public-offline-only")
        old_messages = old_client._messages(exported)
        new_messages = new_client._messages(exported)
        old_cost = before["message_cost"](old_messages, old_client.reserve)
        new_cost = candidate["message_cost"](new_messages, new_client.reserve)
        assert max(old_cost, new_cost) <= 2048
        probes.append(dict(case=name, sources=exported, semantic_review_rubric=rubric,
                           before_messages=old_messages, candidate_messages=new_messages,
                           before_estimated_context_cost=old_cost, candidate_estimated_context_cost=new_cost))
    report = dict(status="PUBLIC_COUNTEREXAMPLES_REPRODUCED", current_production_cause_confirmed=False,
                  current_spec_sha256=sha(SPEC_PATH.read_bytes()), source_sha256=PINS,
                  actual_validator_ast_sha256=store_ast, before_ast_sha256=before_ast, candidate_ast_sha256=candidate_ast,
                  original_six_are_single_source_small_context=True, validator_cases=results, fragment_boundaries=cuts,
                  private_database_opened=False, database_opened=False, devices_accessed=False, model_requests_executed=False,
                  frozen_sources_changed=False, script_sha256=sha(Path(__file__).read_bytes()))
    (HERE / "PUBLIC_REVIEW.json").write_bytes(encoded(report))
    addendum = dict(schema="aura.public-negation-prompt-comparison-addendum.v1", public_cases_only=True,
                    model_requests_executed=False, options={"num_predict": 384}, task="summary", budget_ms=30000,
                    context_limit=2048, candidate_source_sha256=PINS["candidate"], cases=probes,
                    adoption_requires="Complete JSON, unchanged validator, and manual scope/condition/timeline semantics check")
    (HERE / "PUBLIC_MODEL_ADDITIONS.json").write_bytes(encoded(addendum))
    print(json.dumps(dict(status=report["status"], validator_cases=len(results), fragment_variants=len(cuts)*3,
                          added_public_cases=len(probes), report_sha256=sha((HERE / "PUBLIC_REVIEW.json").read_bytes()),
                          additions_sha256=sha((HERE / "PUBLIC_MODEL_ADDITIONS.json").read_bytes())), ensure_ascii=True))


if __name__ == "__main__":
    main()
