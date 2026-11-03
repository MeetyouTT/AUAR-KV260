"""Pinned ingestion metadata and public Store/summary reproduction only."""
import ast
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent.parent
R4 = REPAIR / "memory_negation_v23_candidate_r4"
BASE = REPAIR / "feature_trigger_collaboration/board_integration_v17/local_runtime_v17"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    spec_path = REPAIR / "release_v23_memory_summary_candidate/memory_summary_evidence/spec.json"
    spec = json.loads(spec_path.read_bytes())
    selected = {
        "common/board_memory.py": R4 / "after/common/board_memory.py",
        "board/runtime/board_memory_policy.py": R4 / "after/board/runtime/board_memory_policy.py",
        "board/runtime/board_business.py": REPAIR / "release_v20_identity_history_candidate/payload/board/runtime/board_business.py",
        "board/runtime/board_dialogue.py": REPAIR / "feature_trigger_collaboration/candidate_h01/after/board/runtime/board_dialogue.py",
        "board/runtime/audio/board_dialogue_jobs.py": BASE / "board/runtime/audio/board_dialogue_jobs.py",
        "board/runtime/visual_memory.py": BASE / "board/runtime/visual_memory.py",
        "board/runtime/visual_policy.py": BASE / "board/runtime/visual_policy.py",
        "board/visual_timeline.py": BASE / "board/visual_timeline.py",
    }
    pins = {}
    for relative, path in selected.items():
        pins[relative] = digest(path)
        assert pins[relative] == spec["component_sha256"][relative], relative
    jobs = ast.parse(selected["board/runtime/audio/board_dialogue_jobs.py"].read_bytes())
    metadata_nodes = [keyword.value for node in ast.walk(jobs)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                      and node.func.attr == "prepare_text" for keyword in node.keywords
                      if keyword.arg == "metadata"]
    assert len(metadata_nodes) == 1
    expression = compile(ast.Expression(body=metadata_nodes[0]), "<pinned-public-ingestion-metadata>", "eval")
    generated = [eval(expression, {"dict": dict, "job": SimpleNamespace(context_source_id=value)})
                 for value in (None, "public-source")]
    assert generated == [{"evidence": "statement"}, {"source_id": "public-source", "evidence": "statement"}]
    assert all("negated" not in metadata for metadata in generated)
    sys.path.insert(0, str(R4))
    definition = importlib.util.spec_from_file_location("public_r4_ingestion_support", R4 / "run_public_tests.py")
    public = importlib.util.module_from_spec(definition)
    sys.modules[definition.name] = public
    definition.loader.exec_module(public)
    cases = [
        ("ordinary_polar_question", "你会不会唱歌？", "用户询问助手是否会唱歌。", generated[1], True),
        ("explicit_negated_question_control", "你会不会唱歌？", "用户询问助手是否会唱歌。",
         dict(generated[1], negated=True), False),
        ("genuine_negative_reversal", "我不会唱歌。", "用户会唱歌。", generated[1], False),
        ("genuine_negative_preserved", "我不会唱歌。", "用户不会唱歌。", generated[1], True),
        ("unrecognized_faithful_negative_wording", "小林没有喝咖啡。", "小林没喝咖啡。", generated[1], False),
    ]
    outcomes = []
    for name, text, summary, metadata, accepted in cases:
        with tempfile.TemporaryDirectory(prefix="public-v23-ingestion-") as directory:
            now = [1000.0]
            store = public.STORE.BoardMemoryStore(Path(directory) / "synthetic.sqlite3", clock=lambda: now[0])
            store.begin_turn({"kind": "conversation", "id": "public"}, "public-turn", text,
                             generation=0, metadata=metadata)
            store.interrupt("public-turn", generation=0)
            with closing(sqlite3.connect(store.path)) as db:
                written = json.loads(db.execute("SELECT metadata FROM bm_events WHERE source='user_said'").fetchone()[0])
            assert written == metadata
            now[0] = 1400.0
            inference = public.FakeInference(summary)
            client = public.POLICY.BoardSummaryClient(inference, board_boot_id="public", final_summary_max_utf8_bytes=301)
            actual = public.STORE.BoardMemoryWorker(store, client, idle=lambda: True).step()
            assert actual is accepted, name
            with closing(sqlite3.connect(store.path)) as db:
                bodies = db.execute("SELECT COUNT(*) FROM bm_bodies").fetchone()[0]
                summaries = db.execute("SELECT COUNT(*) FROM bm_summaries").fetchone()[0]
            assert (bodies, summaries) == ((0, 1) if accepted else (1, 0)), name
            reasons = []
            try:
                public.STORE.validate_compaction_text(summary, [public.source(text, metadata)])
            except public.STORE.CandidateRejected as error:
                reasons = list(error.rejection_reasons)
            assert reasons == ([] if accepted else ["negation_missing"]), name
            outcomes.append(dict(case=name, public_source=text, public_summary=summary,
                metadata_keys=sorted(written), metadata_negated_true=written.get("negated") is True,
                worker_completed=actual, model_calls=len(inference.calls), rejection_reasons=reasons,
                pending_bodies=bodies, persisted_summaries=summaries, summary_attempt=client.failure_metadata()))
    report = dict(status="PASS", tested_cases=len(outcomes), cases=outcomes,
        actual_spec_sha256=digest(spec_path), source_sha256=pins,
        ordinary_ingestion_metadata_automatically_negated=False,
        metadata_true_control_is_explicitly_injected=True,
        actual_remaining_live_failure_cause="UNDETERMINED_WITHOUT_FAILED_SOURCE_SHAPE_COUNTERS",
        faithful_negative_paraphrase_rejection_reproduced=True,
        production_source_modified=False, private_database_accessed=False, model_or_device_accessed=False)
    destination = HERE / "PUBLIC_INGESTION_REVIEW.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status="PASS", cases=len(outcomes), report_sha256=digest(destination),
                         ordinary_ingestion_automatically_negated=False,
                         public_faithful_negative_paraphrase_rejected=True)))


if __name__ == "__main__":
    main()
