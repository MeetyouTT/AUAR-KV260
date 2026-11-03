"""Synthetic SQLite regressions for scoped search and complete atomic clear.

These tests do not open models, services, sockets, identity galleries or devices.
"""
import sqlite3

import pytest

from common.board_memory import BoardMemoryStore, BoardMemoryWorker, IdempotencyConflict, StaleTurn
from common.profile_access import ProfileAccess
from tests.framework.test_board_memory import Clock, candidate


SCOPE = {"kind": "conversation", "id": "synthetic-main"}
OTHER = {"kind": "conversation", "id": "synthetic-other"}
DIGEST = "a" * 64


@pytest.fixture
def memory(tmp_path):
    clock = Clock()
    return BoardMemoryStore(tmp_path / "synthetic-search-clear.sqlite3", clock=clock), clock


def archive(store, clock, name, text, summary=None, *, keywords=None, scope=SCOPE, topic=""):
    store.append_event(scope, name, "user_said", text, topic=topic)
    clock.advance(301.)
    prepared = store.prepare_compaction(max_events=1)
    assert prepared is not None
    value = candidate(prepared, summary or text)
    value["keywords"] = keywords or ["合成"]
    receipt = store.commit_compaction(prepared["task_id"], prepared["lease_token"], value)
    assert receipt["committed"]
    return receipt["summary_id"]


def test_old_keyword_only_summary_is_found_before_twenty_new_unrelated_blocks(memory):
    store, clock = memory
    old = archive(store, clock, "old-cup", "杯子放在架子上", "物品留在架子上", keywords=["杯子"])
    for index in range(25):
        archive(store, clock, "weather-" + str(index), "天气晴朗", keywords=["天气"])
    assert old not in {r["summary_id"] for r in store.history(SCOPE, limit=20)}
    found = store.history(SCOPE, search="杯子", limit=1)
    assert len(found) == 1 and found[0]["summary_id"] == old
    assert found[0]["text"] == "物品留在架子上" and found[0]["keywords"] == ["杯子"]
    assert store.health()["active_bodies"] == 0


def test_old_detail_match_is_not_hidden_by_more_than_twenty_new_nonmatches(memory):
    store, clock = memory
    store.append_event(SCOPE, "old-detail", "user_said", "杯子放在架子上")
    for index in range(25):
        clock.advance(1)
        store.append_event(SCOPE, "new-detail-" + str(index), "user_said", "天气晴朗")
    assert "old-detail" not in {r["event_id"] for r in store.history(SCOPE)}
    assert [r["event_id"] for r in store.history(SCOPE, search="杯子")] == ["old-detail"]
    assert store.history(SCOPE, search=None) == store.history(SCOPE, search="")


def test_exact_topic_and_search_are_independent_and_date_constraints_still_apply(memory):
    store, clock = memory
    store.append_event(SCOPE, "kitchen-cup", "user_said", "杯子在架子上", topic="kitchen")
    original_time = clock()
    clock.advance(1)
    store.append_event(SCOPE, "study-cup", "user_said", "杯子在书桌上", topic="study")
    assert {r["event_id"] for r in store.history(SCOPE, search="杯子")} == {"kitchen-cup", "study-cup"}
    assert [r["event_id"] for r in store.history(SCOPE, topic="kitchen", search="杯子")] == ["kitchen-cup"]
    assert store.history(SCOPE, topic="杯子") == []
    assert store.history(SCOPE, search="杯子", end=original_time - .1) == []


def test_forgetting_compacted_source_removes_text_and_keyword_search_hits(memory):
    store, clock = memory
    archive(store, clock, "forgotten-source", "杯子放在架子上", "物品留在架子上", keywords=["杯子"])
    assert store.history(SCOPE, search="杯子")
    store.forget(SCOPE, event_ids=["forgotten-source"], operation_id="forget-cup")
    assert store.history(SCOPE, search="杯子") == []
    assert store.history(SCOPE, search="物品") == []
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM bm_summary_keywords").fetchone()[0] == 0


def test_search_never_crosses_profile_grants_or_anonymous_scope(tmp_path):
    clock = Clock(); access = ProfileAccess("9" * 64, clock=clock)
    store = BoardMemoryStore(tmp_path / "synthetic-profiles.sqlite3", clock=clock, profile_access=access)
    actors = [{"board_boot_id": "boot", "session_id": value} for value in ("one", "two")]
    _, first = access.issue("a" * 32, actors[0]); _, second = access.issue("b" * 32, actors[1])
    one = {"kind": "profile", "id": "a" * 32, "grant": first}
    two = {"kind": "profile", "id": "b" * 32, "grant": second}
    store.append_event(one, "profile-one", "user_said", "杯子在架子上")
    store.append_event(two, "profile-two", "user_said", "杯子在书桌上")
    store.append_event(SCOPE, "anonymous", "user_said", "杯子在桌上")
    assert [r["event_id"] for r in store.history(one, search="杯子")] == ["profile-one"]
    assert [r["event_id"] for r in store.history(two, search="杯子")] == ["profile-two"]
    assert [r["event_id"] for r in store.history(SCOPE, search="杯子")] == ["anonymous"]
    with pytest.raises(PermissionError):
        store.history({"kind": "profile", "id": "b" * 32, "grant": first}, search="杯子")
    with pytest.raises(PermissionError):
        store.history({"kind": "profile", "id": "a" * 32}, search="%")
    access.revoke(actors[0])
    with pytest.raises(PermissionError):
        store.history(one, search="杯子")


def test_search_escapes_literal_underscore_and_does_not_expand_punctuation(memory):
    store, clock = memory
    store.append_event(SCOPE, "literal", "user_said", "alpha_beta")
    store.append_event(SCOPE, "other", "user_said", "alphaXbeta")
    assert [r["event_id"] for r in store.history(SCOPE, search="_")] == ["literal"]
    assert store.history(SCOPE, search="%") == []
    assert store.history(SCOPE, search="' OR 1=1 --") == []


@pytest.mark.parametrize("search", [1, "a" * 129, "bad\nsearch", "bad\x00search"])
def test_unbounded_or_invalid_search_is_rejected(memory, search):
    store, clock = memory
    with pytest.raises(ValueError):
        store.history(SCOPE, search=search)


def test_clear_reaches_more_than_history_limit_and_scrubs_all_old_values(memory):
    store, clock = memory
    archive(store, clock, "archived", "杯子留在架子上", keywords=["杯子"])
    for index in range(125):
        store.append_event(SCOPE, "raw-" + str(index), "user_said", "待清空的合成内容")
    store.correct(SCOPE, "项目", "旧值", operation_id="old-fact")
    store.correct(SCOPE, "项目", "当前值", operation_id="current-fact")
    store.append_event(OTHER, "other-source", "user_said", "其他范围保留")
    store.correct(OTHER, "项目", "其他范围事实", operation_id="other-fact")
    receipt = store.clear(SCOPE, operation_id="clear-all")
    assert receipt["cleared_events"] > 100 and receipt["cleared_summaries"] == 1 and receipt["cleared_facts"] == 1
    assert store.history(SCOPE) == [] and store.context(SCOPE)["facts"] == []
    assert all(r["value"] is None for r in store.fact_history(SCOPE, "项目"))
    assert store.history(SCOPE, search="杯子") == []
    assert store.context(OTHER)["facts"][0]["value"] == "其他范围事实"
    assert any(r["text"] == "其他范围保留" for r in store.history(OTHER))
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM bm_bodies b JOIN bm_events e USING(event_id) WHERE e.scope_id=?", (SCOPE["id"],)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM bm_summary_keywords k JOIN bm_summaries s USING(summary_id) WHERE s.scope_id=?", (SCOPE["id"],)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM bm_events WHERE scope_id=? AND (state!='forgotten' OR metadata!='{}')", (SCOPE["id"],)).fetchone()[0] == 0


def test_clear_preserves_current_command_reply_full_ack_and_idempotent_retry(memory):
    store, clock = memory
    store.correct(SCOPE, "项目", "旧值", operation_id="old-fact")
    store.begin_turn(SCOPE, "clear-turn", "清空本次对话记忆", generation=3)
    result = store.clear(SCOPE, operation_id="clear-command", operation_turn_id="clear-turn")
    assert store.context(SCOPE)["messages"] == [{"role": "user", "content": "清空本次对话记忆"}]
    assert store.context(SCOPE)["facts"] == []
    store.generated("clear-turn", "已清空这个范围的可检索记忆", generation=3)
    store.bind_audio_receipt("clear-turn", generation=3, playback_token="clear-audio", sha256=DIGEST, samples=480)
    assert store.ack_played("clear-turn", generation=3, playback_token="clear-audio", sha256=DIGEST, samples=480)["status"] == "played"
    store.append_event(SCOPE, "newer-input", "user_said", "较新的内容")
    store.correct(SCOPE, "项目", "较新事实", operation_id="newer-fact")
    assert store.clear(SCOPE, operation_id="clear-command", operation_turn_id="clear-turn") == result
    assert store.context(SCOPE)["facts"][0]["value"] == "较新事实"
    assert any(r.get("event_id") == "newer-input" for r in store.history(SCOPE))


def test_clear_commits_independently_of_tts_and_rejects_old_generated_output(memory):
    store, clock = memory
    store.begin_turn(SCOPE, "old-turn", "旧问题", generation=1)
    store.generated("old-turn", "旧回答", generation=1)
    store.bind_audio_receipt("old-turn", generation=1, playback_token="old-audio", sha256=DIGEST, samples=480)
    store.clear(SCOPE, operation_id="direct-clear")
    with pytest.raises(StaleTurn):
        store.ack_played("old-turn", generation=1, playback_token="old-audio", sha256=DIGEST, samples=480)
    store.correct(SCOPE, "项目", "还需清除", operation_id="other-value")
    store.begin_turn(SCOPE, "clear-turn", "清空本次对话记忆", generation=2)
    store.clear(SCOPE, operation_id="tts-independent-clear", operation_turn_id="clear-turn")
    store.interrupt("clear-turn", generation=2, reason="tts_failed")
    assert store.context(SCOPE)["facts"] == []
    assert store.context(SCOPE)["messages"] == [{"role": "user", "content": "清空本次对话记忆"}]


def test_clear_cancels_inflight_compaction_and_prevents_old_candidate_resurrection(memory):
    store, clock = memory
    store.append_event(SCOPE, "old", "user_said", "旧内容")
    clock.advance(301.)
    prepared = store.prepare_compaction()
    store.clear(SCOPE, operation_id="clear-during-model")
    result = store.commit_compaction(prepared["task_id"], prepared["lease_token"], candidate(prepared, "旧内容"))
    assert not result["committed"] and store.history(SCOPE) == []
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT status,error_code FROM bm_tasks").fetchone() == ("cancelled", "scope_cleared")


def test_clear_wrong_scope_operation_turn_or_reused_operation_id_fails_without_changes(memory):
    store, clock = memory
    store.correct(SCOPE, "项目", "保留事实", operation_id="already-used")
    store.begin_turn(OTHER, "other-turn", "其他范围的当前操作", generation=1)
    with pytest.raises(StaleTurn):
        store.clear(SCOPE, operation_id="wrong-turn", operation_turn_id="other-turn")
    with pytest.raises(IdempotencyConflict):
        store.clear(SCOPE, operation_id="already-used")
    assert store.context(SCOPE)["facts"][0]["value"] == "保留事实"


def test_clear_profile_isolation_and_revocation(tmp_path):
    clock = Clock(); access = ProfileAccess("9" * 64, clock=clock)
    store = BoardMemoryStore(tmp_path / "synthetic-profile-clear.sqlite3", clock=clock, profile_access=access)
    actors = [{"board_boot_id": "boot", "session_id": value} for value in ("one", "two")]
    _, first = access.issue("a" * 32, actors[0]); _, second = access.issue("b" * 32, actors[1])
    one = {"kind": "profile", "id": "a" * 32, "grant": first}
    two = {"kind": "profile", "id": "b" * 32, "grant": second}
    store.correct(one, "项目", "档案甲", operation_id="profile-one")
    store.correct(two, "项目", "档案乙", operation_id="profile-two")
    store.clear(one, operation_id="clear-one")
    assert store.context(one)["facts"] == [] and store.context(two)["facts"][0]["value"] == "档案乙"
    access.revoke(actors[1])
    with pytest.raises(PermissionError):
        store.clear(two, operation_id="revoked-clear")
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT value FROM bm_facts WHERE scope_id=? AND state='current'", (two["id"],)).fetchone()[0] == "档案乙"


def test_clear_failure_rolls_back_bodies_summaries_keywords_facts_and_operation(memory):
    store, clock = memory
    old = archive(store, clock, "old-summary", "杯子留在架子上", keywords=["杯子"])
    store.append_event(SCOPE, "raw", "user_said", "待保留的合成原文")
    store.correct(SCOPE, "项目", "保留事实", operation_id="original-fact")
    before = store.history(SCOPE)
    with sqlite3.connect(store.path) as db:
        db.executescript("CREATE TRIGGER synthetic_clear_failure BEFORE UPDATE ON bm_facts BEGIN SELECT RAISE(ABORT,'synthetic failure'); END;")
    with pytest.raises(sqlite3.IntegrityError):
        store.clear(SCOPE, operation_id="failed-clear")
    assert store.history(SCOPE) == before
    assert store.history(SCOPE, search="杯子")[0]["summary_id"] == old
    assert store.context(SCOPE)["facts"][0]["value"] == "保留事实"
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM bm_operations WHERE operation_id='failed-clear'").fetchone()[0] == 0


def test_default_worker_leases_one_complete_short_turn_at_a_time(memory):
    store, clock = memory
    for name in ("first", "second"):
        store.begin_turn(SCOPE, name, "合成输入", generation=1)
        store.generated(name, "合成回答", generation=1)
        store.bind_audio_receipt(name, generation=1, playback_token="audio-" + name, sha256=DIGEST, samples=480)
        store.ack_played(name, generation=1, playback_token="audio-" + name, sha256=DIGEST, samples=480)
        clock.advance(1.)
    clock.advance(301.)
    sizes = []
    def model(prepared, cancelled):
        sizes.append(len(prepared["sources"]))
        return candidate(prepared, "用户与助手进行了合成交流")
    worker = BoardMemoryWorker(store, model, idle=lambda: True)
    assert worker.step() and sizes == [2] and store.health()["active_bodies"] == 2
    assert worker.step() and sizes == [2, 2] and store.health()["active_bodies"] == 0
