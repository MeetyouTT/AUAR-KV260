"""Synthetic-only failure, ownership, concurrency and crash-recovery checks."""
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time

import pytest

from common.board_memory import (BoardMemoryStore, BoardMemoryWorker, CandidateRejected,
                                 IdempotencyConflict, MemoryBusy, ScopeDenied, StaleTurn,
                                 compaction_messages, parse_compaction_candidate)
from common.profile_access import ProfileAccess


SCOPE = {"kind": "conversation", "id": "synthetic-conversation"}
OTHER = {"kind": "conversation", "id": "synthetic-other"}
DIGEST = "a" * 64


class Clock:
    def __init__(self, value=1000.):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


@pytest.fixture
def fixture(tmp_path):
    clock = Clock()
    return BoardMemoryStore(tmp_path / "synthetic-board-memory.sqlite3", clock=clock), clock


def played(store, clock, name="turn-1", *, scope=SCOPE, user="用户说要休息", reply="好的，休息一下", metadata=None):
    turn = store.begin_turn(scope, name, user, generation=3, metadata=metadata)
    clock.advance(1)
    store.generated(name, reply, generation=3)
    store.bind_audio_receipt(name, generation=3, playback_token="audio-" + name, sha256=DIGEST, samples=24000)
    clock.advance(1)
    store.ack_played(name, generation=3, playback_token="audio-" + name, sha256=DIGEST, samples=24000)
    return turn


def candidate(prepared, text="用户说要休息，助手已完整回复同意休息"):
    return {"schema_version": 1, "scope": prepared["scope"], "topic": prepared["topic"],
            "start_utc": prepared["start_utc"], "end_utc": prepared["end_utc"],
            "source_refs": [{"event_id": s["event_id"], "revision": s["revision"]}
                            for s in prepared["sources"] if s["include_in_summary"]],
            "summary": text, "keywords": ["休息"], "claims": copy.deepcopy(prepared["required_claims"])}


def compact(store, text="用户说要休息，助手已完整回复同意休息"):
    prepared = store.prepare_compaction()
    assert prepared is not None
    result = store.commit_compaction(prepared["task_id"], prepared["lease_token"], candidate(prepared, text))
    assert result["committed"]
    return prepared, result


def test_last_closure_not_created_time_controls_exact_five_minute_boundary(fixture):
    store, clock = fixture
    store.begin_turn(SCOPE, "slow-turn", "用户说要休息", generation=1)
    clock.advance(301)
    assert store.prepare_compaction() is None  # Still open, despite old creation.
    store.generated("slow-turn", "好的", generation=1)
    store.bind_audio_receipt("slow-turn", generation=1, playback_token="audio", sha256=DIGEST, samples=24000)
    clock.advance(9)
    store.ack_played("slow-turn", generation=1, playback_token="audio", sha256=DIGEST, samples=24000)
    clock.advance(299.999)
    assert store.prepare_compaction() is None
    clock.advance(.001)
    assert len(store.prepare_compaction()["sources"]) == 2


def test_success_publishes_durable_summary_but_deletes_only_bodies(fixture):
    store, clock = fixture
    turn = played(store, clock)
    clock.advance(301)
    prepared, result = compact(store)
    health = store.health()
    assert health["active_bodies"] == 0 and health["valid_summaries"] == 1
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM bm_events").fetchone()[0] == 2
        assert db.execute("SELECT body_hash FROM bm_events WHERE event_id=?", (turn["user_event_id"],)).fetchone()[0]
        assert db.execute("SELECT count(*) FROM bm_summary_sources").fetchone()[0] == 2
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    reopened = BoardMemoryStore(store.path, clock=clock)
    assert reopened.context(SCOPE)["messages"] == []
    assert reopened.context(SCOPE)["summaries"][0]["summary_id"] == result["summary_id"]
    assert reopened.history(SCOPE)[0]["detail_available"] is False
    assert reopened.prepare_compaction() is None
    assert reopened.commit_compaction(prepared["task_id"], prepared["lease_token"], candidate(prepared))["idempotent"]


def test_failed_model_and_rejected_candidate_keep_all_detail(fixture):
    store, clock = fixture
    played(store, clock); clock.advance(301)
    p = store.prepare_compaction()
    assert store.fail_compaction(p["task_id"], p["lease_token"], "private model output must not be logged")["reason"] == "compaction_failed"
    p = store.prepare_compaction()
    bad = candidate(p); bad["source_refs"] = []
    with pytest.raises(CandidateRejected):
        store.commit_compaction(p["task_id"], p["lease_token"], bad)
    assert store.health()["active_bodies"] == 2 and store.health()["valid_summaries"] == 0
    with sqlite3.connect(store.path) as db:
        assert "private model output" not in json.dumps(db.execute("SELECT * FROM bm_tasks").fetchall())


def test_sqlite_publish_failure_rolls_back_summary_and_cleanup(fixture):
    store, clock = fixture
    played(store, clock); clock.advance(301)
    p = store.prepare_compaction()
    with sqlite3.connect(store.path) as db:
        db.executescript("CREATE TRIGGER synthetic_disk_failure BEFORE DELETE ON bm_bodies BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END;")
    with pytest.raises(sqlite3.IntegrityError):
        store.commit_compaction(p["task_id"], p["lease_token"], candidate(p))
    assert store.health()["active_bodies"] == 2 and store.health()["valid_summaries"] == 0
    with sqlite3.connect(store.path) as db:
        db.execute("DROP TRIGGER synthetic_disk_failure")
    assert store.commit_compaction(p["task_id"], p["lease_token"], candidate(p))["committed"]


def test_new_dialogue_globally_preempts_inflight_compaction_without_locking(fixture):
    store, clock = fixture
    played(store, clock); clock.advance(301)
    entered = threading.Event(); release = threading.Event(); cancellation_seen = []
    def model(snapshot, cancelled):
        entered.set()
        assert release.wait(3)
        cancellation_seen.append(cancelled())
        return candidate(snapshot)
    worker = BoardMemoryWorker(store, model, idle=lambda: True)
    thread = threading.Thread(target=worker.step)
    thread.start(); assert entered.wait(2)
    start = time.monotonic()
    store.begin_turn(OTHER, "new-dialogue", "新对话", generation=8)
    assert time.monotonic() - start < .5
    release.set(); thread.join(3)
    assert not thread.is_alive() and cancellation_seen == [True]
    assert store.health()["valid_summaries"] == 0 and store.health()["active_bodies"] == 3
    assert store.context(OTHER)["messages"] == [{"role": "user", "content": "新对话"}]


def test_busy_dialogue_accumulates_backlog_then_idle_worker_cleans_it(fixture):
    store, clock = fixture
    played(store, clock); clock.advance(301)
    idle = [False]; calls = []
    def model(snapshot, cancelled):
        calls.append(snapshot["task_id"])
        return candidate(snapshot)
    worker = BoardMemoryWorker(store, model, idle=lambda: idle[0])
    assert not worker.step() and not calls and store.health()["backlog_events"] == 2
    idle[0] = True
    assert worker.step() and len(calls) == 1 and store.health()["backlog_events"] == 0


def test_restart_recovers_expired_lease_and_rejects_old_result(fixture):
    store, clock = fixture
    played(store, clock); clock.advance(301)
    first = store.prepare_compaction(worker_id="crashed", lease_seconds=5)
    reopened = BoardMemoryStore(store.path, clock=clock)
    assert reopened.prepare_compaction() is None
    clock.advance(5)
    retry = reopened.prepare_compaction(worker_id="restarted")
    assert retry["task_id"] == first["task_id"] and retry["lease_token"] != first["lease_token"]
    assert not store.commit_compaction(first["task_id"], first["lease_token"], candidate(first))["committed"]
    assert reopened.commit_compaction(retry["task_id"], retry["lease_token"], candidate(retry))["committed"]


def test_two_store_instances_cannot_lease_the_same_sources(fixture):
    store, clock = fixture
    played(store, clock); clock.advance(301)
    other = BoardMemoryStore(store.path, clock=clock)
    barrier = threading.Barrier(2); results = []
    def prepare(target):
        barrier.wait()
        results.append(target.prepare_compaction())
    threads = [threading.Thread(target=prepare, args=(target,)) for target in (store, other)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(2)
    assert len(results) == 2 and sum(r is not None for r in results) == 1


def test_unplayed_assistant_is_not_disclosed_to_summary_or_history(fixture):
    store, clock = fixture
    store.begin_turn(SCOPE, "tts-failed", "我计划散步", generation=1)
    store.generated("tts-failed", "未播放的私有回复", generation=1)
    store.interrupt("tts-failed", generation=1)
    clock.advance(301)
    p = store.prepare_compaction()
    assistant = next(s for s in p["sources"] if s["source"] == "assistant_reply")
    assert assistant["text"] is None and not assistant["include_in_summary"]
    assert "未播放的私有回复" not in json.dumps(p, ensure_ascii=False)
    c = candidate(p, "用户说计划散步；没有完整播放的助手回复")
    assert len(c["source_refs"]) == 1
    assert store.commit_compaction(p["task_id"], p["lease_token"], c)["deleted_bodies"] == 2
    assert "未播放的私有回复" not in json.dumps(store.history(SCOPE), ensure_ascii=False)


@pytest.mark.parametrize("change", [{"samples": 23999}, {"sha256": "b" * 64}, {"playback_token": "other"}, {"generation": 2}])
def test_full_playback_ack_requires_exact_bound_receipt(fixture, change):
    store, clock = fixture
    store.begin_turn(SCOPE, "receipt", "用户输入", generation=1)
    store.generated("receipt", "助手回答", generation=1)
    with pytest.raises(StaleTurn):
        store.ack_played("receipt", generation=1)
    store.bind_audio_receipt("receipt", generation=1, playback_token="audio", sha256=DIGEST, samples=24000)
    fields = {"generation": 1, "playback_token": "audio", "sha256": DIGEST, "samples": 24000}
    fields.update(change)
    with pytest.raises(StaleTurn):
        store.ack_played("receipt", **fields)
    assert store.context(SCOPE)["messages"] == [{"role": "user", "content": "用户输入"}]
    fields.update({"generation": 1, "playback_token": "audio", "sha256": DIGEST, "samples": 24000})
    assert store.ack_played("receipt", **fields)["status"] == "played"
    assert store.ack_played("receipt", **fields)["status"] == "played"


def test_input_and_explicit_memory_commit_survive_tts_failure(fixture):
    store, clock = fixture
    store.begin_turn(SCOPE, "no-tts", "记住我的颜色是蓝色", generation=1)
    store.correct(SCOPE, "颜色", "蓝色", operation_id="remember-1")
    store.interrupt("no-tts", generation=1, reason="tts_failed")
    assert store.context(SCOPE)["messages"][0]["content"] == "记住我的颜色是蓝色"
    assert store.context(SCOPE)["facts"][0]["value"] == "蓝色"


def test_scope_and_topic_are_never_merged(fixture):
    store, clock = fixture
    store.append_event(SCOPE, "a", "user_said", "话题甲", topic="甲")
    store.append_event(SCOPE, "b", "user_said", "话题乙", topic="乙")
    store.append_event(OTHER, "c", "user_said", "另一会话", topic="甲")
    clock.advance(301)
    results = []
    for text in ("话题甲", "话题乙", "另一会话"):
        p = store.prepare_compaction()
        assert len(p["sources"]) == 1
        results.append(p)
        assert store.commit_compaction(p["task_id"], p["lease_token"], candidate(p, text))["committed"]
    assert len({(p["scope"]["id"], p["topic"]) for p in results}) == 3
    assert len(store.history(SCOPE)) == 2 and len(store.history(OTHER)) == 1


def test_forget_after_body_cleanup_revokes_summary_keywords_and_facts(fixture):
    store, clock = fixture
    event = store.append_event(SCOPE, "fact-source", "user_said", "蓝色")
    store.correct(SCOPE, "颜色", "蓝色", source_event_ids=[event["event_id"]], operation_id="set-color")
    clock.advance(301)
    # Fact operation deliberately has a separate topic; compact both blocks.
    while True:
        p = store.prepare_compaction()
        if p is None:
            break
        store.commit_compaction(p["task_id"], p["lease_token"], candidate(p, "用户明确记录颜色为蓝色"))
    assert store.health()["active_bodies"] == 0 and store.health()["valid_summaries"] == 2
    receipt = store.forget(SCOPE, fact_keys=["颜色"], operation_id="forget-color")
    assert store.forget(SCOPE, fact_keys=["颜色"], operation_id="forget-color") == receipt
    assert store.context(SCOPE)["facts"] == [] and store.history(SCOPE) == []
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM bm_summary_keywords").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM bm_summaries WHERE summary IS NOT NULL").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM bm_facts WHERE value IS NOT NULL").fetchone()[0] == 0
    assert store.fact_history(SCOPE, "颜色")[0]["value"] is None


def test_correction_after_cleanup_keeps_revisions_and_only_new_current_value(fixture):
    store, clock = fixture
    first = store.correct(SCOPE, "颜色", "蓝色", operation_id="old-color")
    clock.advance(301); compact(store, "用户明确记录颜色为蓝色")
    second = store.correct(SCOPE, "颜色", "绿色", operation_id="new-color")
    assert second["revision"] == 2
    assert store.correct(SCOPE, "颜色", "绿色", operation_id="new-color") == second
    assert store.context(SCOPE)["facts"] == [{"key": "颜色偏好", "revision": 2, "value": "绿色"}]
    assert "蓝色" not in json.dumps(store.history(SCOPE), ensure_ascii=False)
    revisions = store.fact_history(SCOPE, "颜色")
    assert [(r["revision"], r["state"], r["value"]) for r in revisions] == [(1, "superseded", "蓝色"), (2, "current", "绿色")]
    assert first["event_id"] in revisions[0]["source_event_ids"]


def test_concurrent_forget_invalidates_lease_and_prevents_resurrection(fixture):
    store, clock = fixture
    store.append_event(SCOPE, "private-event", "user_said", "合成秘密")
    clock.advance(301); p = store.prepare_compaction()
    other = BoardMemoryStore(store.path, clock=clock)
    other.forget(SCOPE, event_ids=["private-event"], operation_id="forget-during-llm")
    assert not store.commit_compaction(p["task_id"], p["lease_token"], candidate(p, "合成秘密"))["committed"]
    assert store.history(SCOPE) == [] and store.health()["valid_summaries"] == 0


def test_source_revision_rechecked_inside_commit_even_after_validation(fixture, monkeypatch):
    store, clock = fixture
    store.append_event(SCOPE, "revision-event", "user_said", "合成数据")
    clock.advance(301); p = store.prepare_compaction()
    validate = store._candidate
    def change_after_validation(c, task, sources):
        result = validate(c, task, sources)
        with sqlite3.connect(store.path) as db:
            db.execute("UPDATE bm_events SET revision=revision+1 WHERE event_id='revision-event'")
        return result
    monkeypatch.setattr(store, "_candidate", change_after_validation)
    result = store.commit_compaction(p["task_id"], p["lease_token"], candidate(p, "合成数据"))
    assert not result["committed"] and result["reason"] == "source_changed"
    assert store.health()["active_bodies"] == 1 and store.health()["valid_summaries"] == 0


@pytest.mark.parametrize("field,changed", [("scope", OTHER), ("topic", "another-topic"), ("start_utc", 0),
                                           ("source_refs", [{"event_id": "invented", "revision": 1}]),
                                           ("claims", []), ("schema_version", 2)])
def test_candidate_scope_schema_time_and_source_fail_closed(fixture, field, changed):
    store, clock = fixture
    store.append_event(SCOPE, "plain", "user_said", "合成数据")
    clock.advance(301); p = store.prepare_compaction(); c = candidate(p, "合成数据")
    c[field] = changed
    with pytest.raises(CandidateRejected):
        store.commit_compaction(p["task_id"], p["lease_token"], c)
    assert store.health()["active_bodies"] == 1


@pytest.mark.parametrize("summary", ["用户计划明天买3个杯子，尚未完成",  # Name dropped.
                                      "小林计划明天买4个杯子，尚未完成",  # Number changed.
                                      "小林已经买3个杯子",  # Negation and plan lost.
                                      "小林明天买3个杯子，尚未完成"])  # Plan claim absent in narrative.
def test_protected_names_numbers_negation_and_plan_reject_changed_candidates(fixture, summary):
    store, clock = fixture
    store.append_event(SCOPE, "plan", "user_said", "小林计划明天买3个杯子，尚未完成",
                       metadata={"names": ["小林"], "numbers": [3], "negated": True, "status": "planned", "evidence": "statement"})
    clock.advance(301); p = store.prepare_compaction()
    with pytest.raises(CandidateRejected):
        store.commit_compaction(p["task_id"], p["lease_token"], candidate(p, summary))
    assert store.health()["active_bodies"] == 1


def test_structured_observation_cannot_silently_become_user_statement(fixture):
    store, clock = fixture
    store.append_event(SCOPE, "visual", "camera_observed", "观察到2个杯子", metadata={"numbers": [2]})
    clock.advance(301); p = store.prepare_compaction()
    c = candidate(p, "用户有2个杯子")
    with pytest.raises(CandidateRejected):
        store.commit_compaction(p["task_id"], p["lease_token"], c)
    c["summary"] = "相机观察到2个杯子，未确认归属"
    assert store.commit_compaction(p["task_id"], p["lease_token"], c)["committed"]


def test_grants_isolate_profiles_and_restart_or_speaker_cannot_unlock(tmp_path):
    clock = Clock(); access = ProfileAccess("9" * 64, clock=clock)
    store = BoardMemoryStore(tmp_path / "synthetic-profile.sqlite3", clock=clock, profile_access=access)
    actor = {"board_boot_id": "synthetic-boot", "session_id": "synthetic-session"}
    _, grant = access.issue("a" * 32, actor)
    scope = {"kind": "profile", "id": "a" * 32, "grant": grant}
    store.correct(scope, "项目", "合成项目", operation_id="profile-fact")
    with pytest.raises(PermissionError):
        store.context({"kind": "profile", "id": "a" * 32})
    with pytest.raises(PermissionError):
        store.context({"kind": "profile", "id": "b" * 32, "grant": grant})
    assert store.context(SCOPE)["facts"] == []
    store.append_event(SCOPE, "speaker-candidate", "device_event", "候选说话人", metadata={"speaker_known": True})
    with pytest.raises(PermissionError):
        store.context({"kind": "profile", "id": "a" * 32})
    access.revoke(actor)
    with pytest.raises(PermissionError):
        store.context(scope)
    restarted = BoardMemoryStore(store.path, clock=clock, profile_access=ProfileAccess("9" * 64, clock=clock))
    with pytest.raises(PermissionError):
        restarted.context(scope)


def test_cross_scope_mutation_and_dependency_are_denied(fixture):
    store, clock = fixture
    store.append_event(OTHER, "other-source", "user_said", "别的会话")
    with pytest.raises(ScopeDenied):
        store.forget(SCOPE, event_ids=["other-source"])
    with pytest.raises(ScopeDenied):
        store.correct(SCOPE, "项目", "项目A", source_event_ids=["other-source"])
    store.begin_turn(SCOPE, "wrong-dependency", "问题", generation=1)
    with pytest.raises(ScopeDenied):
        store.generated("wrong-dependency", "回答", generation=1, source_event_ids=["other-source"])


def test_idempotent_turns_and_events_do_not_duplicate_and_conflicts_fail(fixture):
    store, clock = fixture
    first = store.begin_turn(SCOPE, "same", "同一输入", generation=1)
    assert store.begin_turn(SCOPE, "same", "同一输入", generation=1) == first
    with pytest.raises(IdempotencyConflict):
        store.begin_turn(SCOPE, "same", "不同输入", generation=1)
    store.generated("same", "同一回答", generation=1)
    store.generated("same", "同一回答", generation=1)
    with pytest.raises(IdempotencyConflict):
        store.generated("same", "不同回答", generation=1)
    store.append_event(SCOPE, "same-event", "user_said", "内容")
    store.append_event(SCOPE, "same-event", "user_said", "内容")
    with pytest.raises(IdempotencyConflict):
        store.append_event(OTHER, "same-event", "user_said", "内容")
    assert store.health()["active_bodies"] == 3


def test_forgetting_source_revokes_untracked_later_assistant_paraphrase(fixture):
    store, clock = fixture
    source = played(store, clock, user="合成秘密", reply="已听到")
    played(store, clock, name="later", user="再解释", reply="关于合成秘密的建议")
    store.forget(SCOPE, event_ids=[source["user_event_id"]], operation_id="forget-source")
    context = store.context(SCOPE)
    assert "合成秘密" not in json.dumps(context, ensure_ascii=False)
    assert context["messages"] == [{"role": "user", "content": "再解释"}]


def test_sqlite_busy_is_bounded_and_does_not_delete_data(fixture):
    store, clock = fixture
    store.append_event(SCOPE, "busy-event", "user_said", "保持原文")
    with sqlite3.connect(store.path, isolation_level=None) as lock:
        lock.execute("BEGIN IMMEDIATE")
        start = time.monotonic()
        with pytest.raises(MemoryBusy):
            store.append_event(SCOPE, "blocked-event", "user_said", "尚未写入")
        assert time.monotonic() - start < .75
        lock.rollback()
    assert store.health()["active_bodies"] == 1


def test_refuses_foreign_or_production_databases_and_non_synthetic_origin(tmp_path):
    foreign = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(str(foreign)) as db:
        db.execute("CREATE TABLE turns(seq INTEGER,user TEXT)")
        db.execute("INSERT INTO turns VALUES(1,'existing content')")
    before = foreign.read_bytes()
    with pytest.raises(ValueError):
        BoardMemoryStore(foreign)
    assert foreign.read_bytes() == before
    with pytest.raises(ValueError):
        BoardMemoryStore(tmp_path / "production.sqlite3", data_origin="production")
    assert not (tmp_path / "production.sqlite3").exists()


def test_profile_revocation_blocks_generated_audio_and_ack_callbacks(tmp_path):
    clock = Clock(); access = ProfileAccess("9" * 64, clock=clock)
    store = BoardMemoryStore(tmp_path / "synthetic-revocation.sqlite3", clock=clock, profile_access=access)
    actor = {"board_boot_id": "synthetic-boot", "session_id": "synthetic-session"}
    _, grant = access.issue("a" * 32, actor)
    scope = {"kind": "profile", "id": "a" * 32, "grant": grant}
    store.begin_turn(scope, "private-turn", "私有问题", generation=1)
    store.generated("private-turn", "私有回答", generation=1)
    store.bind_audio_receipt("private-turn", generation=1, playback_token="private-audio", sha256=DIGEST, samples=24000)
    access.revoke(actor)
    with pytest.raises(PermissionError):
        store.generated("private-turn", "私有回答", generation=1)
    with pytest.raises(PermissionError):
        store.bind_audio_receipt("private-turn", generation=1, playback_token="private-audio", sha256=DIGEST, samples=24000)
    with pytest.raises(PermissionError):
        store.ack_played("private-turn", generation=1, playback_token="private-audio", sha256=DIGEST, samples=24000)
    # Startup recovery does not require or resurrect a private grant.
    reopened = BoardMemoryStore(store.path, clock=clock, profile_access=access)
    assert reopened.recover_interrupted_turns() == {"recovered_turns": 1}
    assert reopened.health()["open_turns"] == 0


def test_startup_recovery_closes_pending_turn_and_preserves_user_input(fixture):
    store, clock = fixture
    store.begin_turn(SCOPE, "before-crash", "已接收的用户输入", generation=7)
    store.generated("before-crash", "没有播放完成的回答", generation=7)
    reopened = BoardMemoryStore(store.path, clock=clock)
    assert reopened.recover_interrupted_turns()["recovered_turns"] == 1
    with pytest.raises(StaleTurn):
        reopened.generated("before-crash", "迟来的回答", generation=7)
    assert reopened.context(SCOPE)["messages"] == [{"role": "user", "content": "已接收的用户输入"}]
    clock.advance(300)
    p = reopened.prepare_compaction()
    assert p is not None and len([s for s in p["sources"] if s["include_in_summary"]]) == 1


def test_process_death_inside_body_cleanup_recovers_hot_journal(fixture):
    store, clock = fixture
    played(store, clock); clock.advance(301)
    p = store.prepare_compaction()
    with sqlite3.connect(store.path) as db:
        db.executescript("CREATE TRIGGER synthetic_process_death BEFORE DELETE ON bm_bodies BEGIN SELECT synthetic_crash(); END;")
    script = '''
from contextlib import contextmanager
import json, os, sys
from common.board_memory import BoardMemoryStore
class CrashStore(BoardMemoryStore):
    @contextmanager
    def _db(self, write=False):
        with super()._db(write) as db:
            db.create_function("synthetic_crash", 0, lambda: os._exit(23))
            yield db
store = CrashStore(sys.argv[1], clock=lambda: float(sys.argv[5]))
store.commit_compaction(sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
'''
    process = subprocess.run([sys.executable, "-B", "-c", script, store.path, p["task_id"], p["lease_token"],
                              json.dumps(candidate(p), ensure_ascii=False), str(clock())],
                             capture_output=True, timeout=8, cwd=str(Path(__file__).resolve().parents[2]))
    assert process.returncode == 23, process.stderr.decode("utf-8", errors="replace")
    reopened = BoardMemoryStore(store.path, clock=clock)
    assert reopened.health()["active_bodies"] == 2 and reopened.health()["valid_summaries"] == 0
    with sqlite3.connect(store.path) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        db.execute("DROP TRIGGER synthetic_process_death")
    assert reopened.commit_compaction(p["task_id"], p["lease_token"], candidate(p))["committed"]


def test_prompt_uses_request_aliases_and_omits_private_ids_and_incomplete_reply(fixture):
    store, clock = fixture
    store.append_event(SCOPE, "opaque-real-source", "user_said", "普通业务内容", metadata={"source_id": "private-camera-identity"})
    clock.advance(301); p = store.prepare_compaction()
    messages = compaction_messages(p)
    rendered = json.dumps(messages, ensure_ascii=False)
    for private in (SCOPE["id"], "opaque-real-source", "private-camera-identity", p["task_id"], p["lease_token"]):
        assert private not in rendered
    content = json.loads(messages[1]["content"])
    response = content["template"]
    response["summary"] = "用户陈述普通业务内容"; response["keywords"] = ["业务"]
    decoded = parse_compaction_candidate(json.dumps(response), p)
    assert decoded["scope"] == SCOPE and decoded["source_refs"][0]["event_id"] == "opaque-real-source"
    assert store.commit_compaction(p["task_id"], p["lease_token"], decoded)["committed"]


@pytest.mark.parametrize("response", ['{"scope":{},"scope":{}}', '{"x":NaN}', '```json\n{}\n```'])
def test_model_json_duplicate_fields_non_finite_and_code_fences_are_rejected(fixture, response):
    store, clock = fixture
    store.append_event(SCOPE, "json-source", "user_said", "合成内容")
    clock.advance(301); p = store.prepare_compaction()
    with pytest.raises(CandidateRejected):
        parse_compaction_candidate(response, p)


def test_compaction_group_does_not_split_turn_when_standalone_events_interleave(fixture):
    store, clock = fixture
    store.begin_turn(SCOPE, "group-turn", "用户输入", generation=1)
    for n in range(8):
        clock.advance(1)
        store.append_event(SCOPE, "interleave-" + str(n), "device_event", "设备事件")
    store.generated("group-turn", "助手回复", generation=1)
    store.bind_audio_receipt("group-turn", generation=1, playback_token="group-audio", sha256=DIGEST, samples=24000)
    store.ack_played("group-turn", generation=1, playback_token="group-audio", sha256=DIGEST, samples=24000)
    # Give all events the same final closure to exercise grouping under ties.
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE bm_events SET closed_utc=?", (clock(),))
    clock.advance(301)
    p = store.prepare_compaction(max_events=1)
    assert {s["source"] for s in p["sources"]} == {"user_said", "assistant_played"}


def test_forget_revokes_model_output_that_had_not_created_an_assistant_event(fixture):
    store, clock = fixture
    store.correct(SCOPE, "项目", "旧项目", operation_id="old-project")
    store.begin_turn(SCOPE, "inflight-no-output", "根据项目给建议", generation=2)
    store.forget(SCOPE, fact_keys=["项目"], operation_id="forget-inflight")
    with pytest.raises(StaleTurn):
        store.generated("inflight-no-output", "关于旧项目的建议", generation=2)
    assert store.context(SCOPE)["messages"] == [{"role": "user", "content": "根据项目给建议"}]
    clock.advance(301)
    assert store.prepare_compaction() is not None


def test_correction_revokes_pending_audio_but_preserves_its_user_input(fixture):
    store, clock = fixture
    store.correct(SCOPE, "项目", "旧项目", operation_id="old-project")
    store.begin_turn(SCOPE, "inflight-audio", "给建议", generation=2)
    store.generated("inflight-audio", "关于旧项目的建议", generation=2)
    store.bind_audio_receipt("inflight-audio", generation=2, playback_token="stale-audio", sha256=DIGEST, samples=24000)
    store.correct(SCOPE, "项目", "新项目", operation_id="new-project")
    with pytest.raises(StaleTurn):
        store.ack_played("inflight-audio", generation=2, playback_token="stale-audio", sha256=DIGEST, samples=24000)
    assert store.context(SCOPE)["messages"] == [{"role": "user", "content": "给建议"}]
    assert store.context(SCOPE)["facts"][0]["value"] == "新项目"


def test_explicit_memory_command_can_keep_its_own_reply_after_write(fixture):
    store, clock = fixture
    store.correct(SCOPE, "颜色", "蓝色", operation_id="first-color")
    store.begin_turn(SCOPE, "memory-command-turn", "忘记颜色", generation=1)
    store.forget(SCOPE, fact_keys=["颜色"], operation_id="forget-own-command", operation_turn_id="memory-command-turn")
    assert store.generated("memory-command-turn", "已忘记这条明确记忆", generation=1)["status"] == "awaiting_playback"
    assert store.context(SCOPE)["facts"] == []


def test_forgotten_values_are_removed_from_structured_metadata_too(fixture):
    store, clock = fixture
    store.append_event(SCOPE, "meta-private", "user_said", "小林计划买3个杯子", topic="小林",
                       metadata={"names": ["小林"], "numbers": [3], "fact_keys": ["称呼"],
                                 "claims": [{"field": "fact_value", "value": "小林"}]})
    store.forget(SCOPE, event_ids=["meta-private"], operation_id="forget-meta")
    with sqlite3.connect(store.path) as db:
        metadata, topic = db.execute("SELECT metadata,topic FROM bm_events WHERE event_id='meta-private'").fetchone()
        assert metadata == "{}" and topic == ""


def test_worker_passes_configurable_segment_size_without_splitting_turn(fixture):
    store, clock = fixture
    played(store, clock)
    store.append_event(SCOPE, "extra-source", "user_said", "另一个事件")
    clock.advance(301); seen = []
    def model(p, cancelled):
        seen.append(len(p["sources"]))
        return candidate(p)
    worker = BoardMemoryWorker(store, model, idle=lambda: True, max_events=1, lease_seconds=8)
    assert worker.step() and seen == [2]
    assert store.health()["active_bodies"] == 1


def test_forget_after_correction_updates_tombstone_revision_and_wipes_all_fact_values(fixture):
    store, clock = fixture
    old = store.correct(SCOPE, "项目", "旧值", operation_id="revision-old")
    store.correct(SCOPE, "项目", "新值", operation_id="revision-new")
    with sqlite3.connect(store.path) as db:
        before = db.execute("SELECT revision FROM bm_events WHERE event_id=?", (old["event_id"],)).fetchone()[0]
    store.forget(SCOPE, fact_keys=["项目"], operation_id="forget-both-revisions")
    with sqlite3.connect(store.path) as db:
        after, state, meta = db.execute("SELECT revision,state,metadata FROM bm_events WHERE event_id=?", (old["event_id"],)).fetchone()
        assert after > before and state == "forgotten" and meta == "{}"
    assert [(r["state"], r["value"]) for r in store.fact_history(SCOPE, "项目")] == [("forgotten", None), ("forgotten", None)]
