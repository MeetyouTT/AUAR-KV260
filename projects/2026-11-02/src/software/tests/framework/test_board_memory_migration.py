"""Synthetic legacy snapshots only; no production database or device access."""
import hashlib
import json
import sqlite3
from unittest.mock import patch

import pytest

from common.board_memory import BoardMemoryStore, StaleTurn
from common.board_memory_migration import LegacyMigrationRejected, migrate_legacy_snapshot
from common.profile_access import ProfileAccess
from common.timeline_conversations import TimelineConversationStore


CID = "a" * 32
OTHER = "b" * 32
DIGEST = hashlib.sha256(b"synthetic-audio").hexdigest()


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def meta(n):
    return {"request_id": "synthetic-request-" + str(n), "generation": n,
            "board_boot_id": "synthetic-boot", "session_id": "synthetic-session"}


def turn(source, n, text="普通合成问题", reply="普通合成回答", *, cid=CID, at=1000.,
         played=True, complete=True, dependencies=(), profile=None):
    owner = meta(n)
    with patch("time.time", return_value=at):
        source.begin(cid, owner, text, text, profile=profile)
        if complete:
            source.attach_sources(owner, dependencies, profile=profile, mark_complete=True)
        source.generated(owner, reply, 480, DIGEST)
    if played:
        with patch("time.time", return_value=at + 2):
            source.played(owner, 480, DIGEST)
    with sqlite3.connect(source.path) as db:
        return db.execute("SELECT seq FROM turns WHERE request_id=?", (owner["request_id"],)).fetchone()[0]


def command(source, n, text, *, cid=CID, profile=None, at=1100.):
    with patch("time.time", return_value=at):
        source.begin(cid, meta(n), text, text, profile=profile)
        source.memory_command(meta(n), text, profile=profile)


@pytest.fixture
def stores(tmp_path):
    source = TimelineConversationStore(tmp_path / "synthetic-legacy-snapshot.sqlite3")
    target = BoardMemoryStore(tmp_path / "synthetic-board-candidate.sqlite3", clock=lambda: 2000.)
    return source, target


def migrate(source, target, **options):
    return migrate_legacy_snapshot(source.path, target, expected_sha256=fingerprint(source.path),
                                   source_data_origin="synthetic", **options)


def test_import_preserves_times_receipts_sources_and_is_read_only(stores):
    source, target = stores
    first = turn(source, 1, at=1000.)
    second = turn(source, 2, at=1200., dependencies=[first])
    before = source.path.read_bytes()
    report = migrate(source, target)
    assert source.path.read_bytes() == before
    assert report["turns"] == 2 and report["assistant_recall_enabled"] == 2
    with sqlite3.connect(target.path) as db:
        mapping = db.execute("SELECT source_seq,user_event_id,assistant_event_id FROM bm_migration_turn_map ORDER BY source_seq").fetchall()
        assert [r[0] for r in mapping] == [first, second]
        user = db.execute("SELECT recorded_utc,closed_utc FROM bm_events WHERE event_id=?", (mapping[0][1],)).fetchone()
        assistant = db.execute("SELECT recorded_utc,playback FROM bm_events WHERE event_id=?", (mapping[0][2],)).fetchone()
        assert user == (1000., 1002.) and assistant == (1002., "complete")
        assert db.execute("SELECT count(*) FROM bm_event_dependencies").fetchone()[0] >= 2
    assert [m["role"] for m in target.context({"kind": "conversation", "id": CID})["messages"]] == ["user", "assistant", "user", "assistant"]
    rendered = json.dumps(report, ensure_ascii=False)
    assert "普通合成" not in rendered and CID not in rendered and str(source.path) not in rendered


def test_same_snapshot_retry_does_not_overwrite_new_board_memory(stores):
    source, target = stores
    turn(source, 1)
    first = migrate(source, target)
    target.append_event({"kind": "conversation", "id": CID}, "new-board-event", "device_event", "较新板端内容")
    assert migrate(source, target)["idempotent"]
    assert target.health()["active_bodies"] == first["bodies"] + 1
    turn(source, 2, at=1300.)
    with pytest.raises(LegacyMigrationRejected, match="target_not_empty"):
        migrate(source, target)
    assert target.health()["active_bodies"] == first["bodies"] + 1


def test_nonempty_target_refuses_import_without_overwrite(stores):
    source, target = stores
    turn(source, 1)
    target.append_event({"kind": "conversation", "id": CID}, "existing-board", "user_said", "保留较新记忆")
    with pytest.raises(LegacyMigrationRejected, match="target_not_empty"):
        migrate(source, target)
    assert target.health()["active_bodies"] == 1


def test_unknown_provenance_unplayed_and_visual_dependent_assistants_are_not_recalled(stores):
    source, target = stores
    turn(source, 1, "可保留用户一", "未知来源回答", complete=False)
    turn(source, 2, "可保留用户二", "尚未播完回答", played=False)
    seq = turn(source, 3, "可保留用户三", "依赖未迁移视觉回答")
    with sqlite3.connect(source.path) as db:
        db.execute("INSERT INTO timeline_visual_dependency VALUES(?,7)", (seq,))
    report = migrate(source, target)
    assert report["assistant_recall_enabled"] == 0 and report["assistant_recall_suppressed"] == 3
    context = target.context({"kind": "conversation", "id": CID})
    assert len(context["messages"]) == 3 and all(m["role"] == "user" for m in context["messages"])
    assert "未知来源回答" not in json.dumps(target.history({"kind": "conversation", "id": CID}), ensure_ascii=False)


def test_dependency_of_excluded_or_unknown_assistant_is_suppressed_transitively(stores):
    source, target = stores
    first = turn(source, 1, complete=False)
    second = turn(source, 2, dependencies=[first], at=1100.)
    turn(source, 3, dependencies=[second], at=1200.)
    assert migrate(source, target)["assistant_recall_enabled"] == 0


def test_current_facts_and_correction_history_survive_but_excluded_originals_do_not(stores):
    source, target = stores
    command(source, 1, "记住：颜色=蓝色", at=1000.)
    command(source, 2, "更正记忆：颜色=绿色", at=1100.)
    report = migrate(source, target)
    scope = {"kind": "conversation", "id": CID}
    assert target.context(scope)["facts"] == [{"key": "颜色偏好", "revision": 2, "value": "绿色"}]
    assert target.context(scope)["messages"] == []
    assert [r["state"] for r in target.fact_history(scope, "颜色")] == ["superseded", "current"]
    assert report["excluded_turns"] == 2
    assert target.health()["active_bodies"] == 0


def test_forgotten_fact_values_and_cleared_turn_bodies_are_not_restored(stores):
    source, target = stores
    command(source, 1, "记住：项目=需遗忘的合成值", at=1000.)
    turn(source, 2, "谈合成项目", "需遗忘的合成值的建议", at=1050.)
    command(source, 3, "忘记项目", at=1100.)
    migrate(source, target)
    scope = {"kind": "conversation", "id": CID}
    assert target.context(scope)["facts"] == [] and target.fact_history(scope, "项目") == []
    assert "需遗忘的合成值" not in json.dumps(target.history(scope), ensure_ascii=False)
    with sqlite3.connect(target.path) as db:
        assert db.execute("SELECT count(*) FROM bm_bodies WHERE instr(text,'需遗忘的合成值')>0").fetchone()[0] == 0


def test_profile_catalogue_preserved_without_templates_or_access_grants(stores):
    source, target = stores
    pid = source.create_profile("不可复制的合成姓名", consent=True)
    command(source, 1, "长期记住：项目=个人合成值", profile=pid, at=1000.)
    turn(source, 2, profile=pid, at=1200.)
    with sqlite3.connect(source.path) as db:
        db.execute("CREATE TABLE private_identity_templates(identity_id TEXT,template BLOB)")
        db.execute("INSERT INTO private_identity_templates VALUES('private-id',x'010203')")
    report = migrate(source, target)
    with pytest.raises(PermissionError):
        target.context({"kind": "profile", "id": pid})
    assert target.context({"kind": "conversation", "id": CID})["messages"] == []
    access = ProfileAccess("9" * 64, clock=lambda: 2000.)
    target.profile_access = access
    _, grant = access.issue(pid, {"board_boot_id": "board", "session_id": "session"})
    private = target.context({"kind": "profile", "id": pid, "grant": grant})
    assert private["facts"][0]["value"] == "个人合成值"
    assert report["profiles"] == 1
    with sqlite3.connect(target.path) as db:
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='private_identity_templates'").fetchone()[0] == 0
    assert target.profiles() == [{"id": pid, "name": "不可复制的合成姓名"}]
    target.require_profile(pid)
    assert "不可复制的合成姓名" not in json.dumps(report, ensure_ascii=False)
    assert pid not in json.dumps(report, ensure_ascii=False)


def target_path_bytes(target):
    from pathlib import Path
    return Path(target.path).read_bytes()


def test_profile_conversation_local_facts_are_explicitly_unsupported(stores):
    source, target = stores
    pid = source.create_profile("合成档案", consent=True)
    command(source, 1, "记住本次对话：项目=会话局部值", profile=pid)
    with pytest.raises(LegacyMigrationRejected, match="profile_conversation_local_facts_unsupported"):
        migrate(source, target)
    assert target.health()["active_bodies"] == 0


def test_old_digest_cache_is_never_imported_as_authoritative_history(stores):
    source, target = stores
    turn(source, 1)
    with sqlite3.connect(source.path) as db:
        db.execute("INSERT INTO timeline_digests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "c:" + CID, "legacy-digest", "day", "2026-01-01", 0, 86400, 1000, 1002,
            "不可复制的旧摘录缓存", json.dumps(['user:'+hashlib.sha256(meta(1)['request_id'].encode()).hexdigest()[:32]]), 1, 0, None, 1200))
    migrate(source, target)
    assert target.health()["valid_summaries"] == 0
    assert "不可复制的旧摘录缓存".encode() not in target_path_bytes(target)
    prepared = target.prepare_compaction()
    assert prepared is not None  # Old eligible bodies use the NEW lifecycle.


def test_target_transaction_failure_rolls_back_every_imported_row_and_marker(stores):
    source, target = stores
    turn(source, 1); turn(source, 2, at=1100.)
    with sqlite3.connect(target.path) as db:
        db.executescript("CREATE TRIGGER synthetic_import_failure BEFORE INSERT ON bm_bodies WHEN NEW.text='触发失败' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END;")
    with sqlite3.connect(source.path) as db:
        db.execute("UPDATE turns SET user='触发失败' WHERE seq=2")
    before = source.path.read_bytes()
    with pytest.raises(LegacyMigrationRejected, match="target_transaction_failed"):
        migrate(source, target)
    assert source.path.read_bytes() == before
    assert target.health()["active_bodies"] == 0
    with sqlite3.connect(target.path) as db:
        assert db.execute("SELECT count(*) FROM bm_scopes").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='bm_migrations'").fetchone()[0] == 0


@pytest.mark.parametrize("mutation,code", [
    ("ALTER TABLE turns ADD COLUMN unknown_forgetting_flag INTEGER", "unsupported_columns"),
    ("UPDATE conversation_facts SET source_seq=99999", "invalid_fact_source"),
    ("DELETE FROM timeline_played", None),
])
def test_unsupported_schema_or_broken_fact_source_fails_without_guessing(stores, mutation, code):
    source, target = stores
    command(source, 1, "记住：项目=当前值")
    turn(source, 2, at=1200.)
    with sqlite3.connect(source.path) as db:
        db.execute(mutation)
    if code:
        with pytest.raises(LegacyMigrationRejected, match=code):
            migrate(source, target)
        assert target.health()["active_bodies"] == 0
    else:
        assert migrate(source, target)["assistant_recall_enabled"] == 0


def test_changed_fingerprint_active_journal_and_real_origin_are_rejected(stores):
    source, target = stores
    turn(source, 1)
    with pytest.raises(LegacyMigrationRejected, match="source_fingerprint_mismatch"):
        migrate_legacy_snapshot(source.path, target, expected_sha256="0" * 64, source_data_origin="synthetic")
    with pytest.raises(LegacyMigrationRejected, match="invalid_data_origin"):
        migrate_legacy_snapshot(source.path, target, expected_sha256=fingerprint(source.path), source_data_origin="production")
    from pathlib import Path
    marker = Path(str(source.path) + "-journal")
    marker.write_bytes(b"synthetic active journal marker")
    try:
        with pytest.raises(LegacyMigrationRejected, match="source_not_quiescent_snapshot"):
            migrate(source, target)
    finally:
        marker.unlink()
    assert target.health()["active_bodies"] == 0


def test_source_hash_is_rechecked_before_target_transaction(stores, monkeypatch):
    source, target = stores
    turn(source, 1)
    import common.board_memory_migration as bridge
    original = bridge._read_plan
    def mutate_after_read(*args, **kwargs):
        plan = original(*args, **kwargs)
        with sqlite3.connect(source.path) as db:
            db.execute("UPDATE turns SET user='读取期间发生了变化' WHERE seq=1")
        return plan
    monkeypatch.setattr(bridge, "_read_plan", mutate_after_read)
    with pytest.raises(LegacyMigrationRejected, match="source_changed"):
        migrate(source, target)
    assert target.health()["active_bodies"] == 0


def test_unknown_exclusion_never_restores_a_turn_or_stale_current_fact(stores):
    source, target = stores
    seq = turn(source, 1, "应抑制的原话", "应抑制的回复")
    with sqlite3.connect(source.path) as db:
        db.execute("INSERT INTO recall_exclusions VALUES(?,'unknown_privacy_action')", (seq,))
    assert migrate(source, target)["bodies"] == 0
    assert target.history({"kind": "conversation", "id": CID}) == []


def test_current_fact_with_unknown_or_forgetting_exclusion_fails_closed(stores):
    source, target = stores
    command(source, 1, "记住：项目=不可恢复的值")
    with sqlite3.connect(source.path) as db:
        db.execute("UPDATE recall_exclusions SET reason='memory_forget'")
    with pytest.raises(LegacyMigrationRejected, match="current_fact_source_excluded"):
        migrate(source, target)
    assert target.health()["current_facts"] == 0


def test_orphan_historical_fact_versions_without_current_key_are_not_resurrected(stores):
    source, target = stores
    command(source, 1, "记住：项目=已遗忘旧值", at=1000.)
    command(source, 2, "忘记项目", at=1100.)
    with sqlite3.connect(source.path) as db:
        db.execute("INSERT INTO memory_fact_versions VALUES(?,?,?,?,?,NULL)", ("c:" + CID, "项目", "已遗忘旧值", 1, 1000.))
    report = migrate(source, target)
    assert report["ignored_orphan_fact_versions"] == 1
    assert target.context({"kind": "conversation", "id": CID})["facts"] == []
    assert "已遗忘旧值".encode() not in target_path_bytes(target)


def test_missing_source_coverage_is_unknown_even_with_dependency_edges(stores):
    source, target = stores
    first = turn(source, 1)
    turn(source, 2, at=1100., dependencies=[first])
    with sqlite3.connect(source.path) as db:
        db.execute("DROP TABLE memory_source_coverage")
    assert migrate(source, target)["assistant_recall_enabled"] == 0
    assert all(m["role"] == "user" for m in target.context({"kind": "conversation", "id": CID})["messages"])


def test_cross_scope_dependency_is_rejected_without_partial_import(stores):
    source, target = stores
    first = turn(source, 1)
    second = turn(source, 2, cid=OTHER, at=1100.)
    with sqlite3.connect(source.path) as db:
        db.execute("INSERT INTO memory_source_dependencies VALUES(?,?)", (second, first))
    with pytest.raises(LegacyMigrationRejected, match="invalid_or_cross_scope_dependency"):
        migrate(source, target)
    assert target.health()["active_bodies"] == 0


def test_imported_fact_can_be_corrected_and_forgotten_via_retained_source_links(stores):
    source, target = stores
    command(source, 1, "记住：项目=旧值", at=1000.)
    command(source, 2, "更正记忆：项目=当前值", at=1100.)
    migrate(source, target)
    scope = {"kind": "conversation", "id": CID}
    assert target.correct(scope, "项目", "板端新值", operation_id="board-correction")["revision"] == 3
    assert target.context(scope)["facts"][0]["value"] == "板端新值"
    target.forget(scope, fact_keys=["项目"], operation_id="board-forget")
    assert target.context(scope)["facts"] == []
    assert all(r["value"] is None for r in target.fact_history(scope, "项目"))


def test_tiny_transaction_budget_rolls_back_schema_rows_and_import_marker(stores):
    source, target = stores
    turn(source, 1)
    with pytest.raises(LegacyMigrationRejected, match="target_transaction_budget_exceeded"):
        migrate(source, target, transaction_budget_seconds=.000001)
    assert target.health()["active_bodies"] == 0
    with sqlite3.connect(target.path) as db:
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='bm_migrations'").fetchone()[0] == 0


def test_unknown_legacy_schema_version_is_not_guessed(stores):
    source, target = stores
    turn(source, 1)
    with sqlite3.connect(source.path) as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(LegacyMigrationRejected, match="unsupported_legacy_schema_version"):
        migrate(source, target)
    assert target.health()["active_bodies"] == 0


def test_ambiguous_schema_without_exclusion_primary_key_is_rejected(stores):
    source, target = stores
    turn(source, 1)
    with sqlite3.connect(source.path) as db:
        db.execute("DROP TABLE recall_exclusions")
        db.execute("CREATE TABLE recall_exclusions(seq INTEGER,reason TEXT)")
    with pytest.raises(LegacyMigrationRejected, match="unsupported_primary_key"):
        migrate(source, target)
    assert target.health()["active_bodies"] == 0
