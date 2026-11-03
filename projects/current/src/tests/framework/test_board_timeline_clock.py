"""Pure clock logic and tiny private JSON fixtures; no network/device/models."""
from datetime import datetime, timezone
from email.utils import format_datetime
from contextlib import contextmanager
import json
import os
import sqlite3
import stat
import threading
from unittest.mock import patch

import pytest

from common.board_timeline_clock import ClockUnavailable, HttpDateSample, StableTimelineClock
from common.board_memory import BoardMemoryStore, BoardMemoryWorker


UTC = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc).timestamp()
SOURCE = "configured-windows-model-health"


class Mono:
    def __init__(self, value=100.):
        self.value = value
    def __call__(self):
        return self.value
    def advance(self, seconds):
        self.value += seconds


def clock(mono, **options):
    return StableTimelineClock("synthetic-boot-a", SOURCE, lambda sample: sample.source_id == SOURCE,
        utc_bounds=(UTC - 86400, UTC + 86400), monotonic=mono, **options)


def sample(mono, *, date=UTC, rtt=.2, source=SOURCE, boot="synthetic-boot-a", age=0.):
    return HttpDateSample(source, format_datetime(datetime.fromtimestamp(date, timezone.utc), usegmt=True),
                          mono() - age - rtt, mono() - age, boot)


def anchored(**options):
    mono = Mono()
    result = clock(mono, **options)
    result.observe_http_date(sample(mono))
    return result, mono


def test_no_initial_anchor_refuses_events_and_cleanup_without_board_wall_fallback():
    mono = Mono(); value = clock(mono)
    with patch("time.time", return_value=1637383496.):
        for method in (value, value.event_time):
            with pytest.raises(ClockUnavailable, match="uninitialized"):
                method()
    assert not value.safe_for_compaction()


def test_explicit_date_anchor_has_a_bounded_interval_and_conservative_store_time():
    value, mono = anchored(server_error_seconds=1., drift_ppm=0.)
    reading = value.quality_snapshot()
    assert reading["utc_estimate"] == UTC + .1
    assert reading["uncertainty_seconds"] == pytest.approx(2.1)
    assert value() == UTC - 2
    assert reading["utc_lower_bound"] <= UTC <= reading["utc_upper_bound"]
    assert reading["error_budget"] == "caller_declared_not_ntp"


def test_board_wall_clock_jumps_cannot_advance_or_delay_the_timeline():
    value, mono = anchored(drift_ppm=0.)
    first = value()
    for wall in (1637383496., UTC + 10 * 86400, 0.):
        with patch("time.time", return_value=wall):
            mono.advance(1)
            assert value() == first + mono() - 100.


def test_retention_clock_never_runs_faster_than_monotonic_at_five_minute_boundary():
    value, mono = anchored(drift_ppm=500.)
    closed = value.event_time()
    mono.advance(299.999)
    assert value() - closed < 300
    mono.advance(.001)
    assert value() - closed < 300  # Drift uncertainty delays cleanup slightly.
    mono.advance(.151)
    assert value() - closed >= 300


def test_verification_expiry_keeps_event_recording_but_refuses_compaction():
    value, mono = anchored(verified_ttl_seconds=10.)
    before = value.event_time(); mono.advance(10.001)
    assert value.event_time() > before
    assert value.quality_snapshot()["quality"] == "estimated_degraded"
    assert not value.safe_for_compaction()
    with pytest.raises(ClockUnavailable, match="verification_expired"):
        value()


def test_later_matching_sample_refreshes_trust_without_moving_same_boot_origin():
    value, mono = anchored(verified_ttl_seconds=10., drift_ppm=0.)
    original = dict(value.anchor)
    mono.advance(11.)
    before = value.event_time()
    value.observe_http_date(sample(mono, date=UTC + 11))
    assert value() == before
    for key in ("anchor_monotonic", "utc_estimate_at_anchor", "base_uncertainty_seconds"):
        assert value.anchor[key] == original[key]
    assert value.safe_for_compaction()


def test_conflicting_date_disables_cleanup_without_rewriting_or_losing_event_time():
    value, mono = anchored()
    mono.advance(2.); before = value.event_time(); origin = dict(value.anchor)
    with pytest.raises(ClockUnavailable, match="http_date_conflicts_with_anchor"):
        value.observe_http_date(sample(mono, date=UTC + 120))
    assert value.event_time() == before and value.anchor == origin
    assert not value.safe_for_compaction()
    with pytest.raises(ClockUnavailable):
        value()
    value.observe_http_date(sample(mono, date=UTC + 2))
    assert value.safe_for_compaction() and value.event_time() == before


@pytest.mark.parametrize("change,reason", [
    ({"rtt": 1.001}, "sample_rtt_exceeded"),
    ({"age": 2.001}, "sample_too_old"),
    ({"source": "unverified-redirect-endpoint"}, "source_not_verified"),
    ({"date": UTC + 2 * 86400}, "http_date_out_of_bounds"),
])
def test_rejected_samples_keep_old_event_estimate_but_latch_cleanup_closed(change, reason):
    value, mono = anchored(); mono.advance(3.); before = value.event_time()
    with pytest.raises(ClockUnavailable, match=reason):
        value.observe_http_date(sample(mono, **change))
    assert value.event_time() == before and not value.safe_for_compaction()


@pytest.mark.parametrize("header", ["Fri, 30 Oct 2026 12:00:00 +0000", "bad", "Sat, 30 Oct 2026 12:00:00 GMT",
                                    "Fri, 30 Oct 2026 12:00:00 GMT, Fri, 30 Oct 2026 12:00:00 GMT"])
def test_malformed_noncanonical_duplicate_or_wrong_weekday_date_is_rejected(header):
    mono = Mono(); value = clock(mono)
    s = HttpDateSample(SOURCE, header, 99.8, 100., "synthetic-boot-a")
    with pytest.raises(ClockUnavailable, match="invalid_http_date"):
        value.observe_http_date(s)
    assert not value.quality_snapshot()["event_time_available"]


def test_source_validator_is_required_and_its_rejection_is_not_replaced_by_source_label():
    mono = Mono()
    with pytest.raises(ValueError):
        StableTimelineClock("boot", SOURCE, None, utc_bounds=(UTC - 1, UTC + 1), monotonic=mono)
    value = StableTimelineClock("boot", SOURCE, lambda sample: False, utc_bounds=(UTC - 10, UTC + 10), monotonic=mono)
    with pytest.raises(ClockUnavailable, match="source_not_verified"):
        value.observe_http_date(sample(mono, boot="boot"))


def test_monotonic_rollback_permanently_refuses_both_events_and_cleanup():
    value, mono = anchored(); mono.advance(10.); value.event_time(); mono.advance(-1.)
    for method in (value.event_time, value):
        with pytest.raises(ClockUnavailable, match="monotonic_rollback"):
            method()
    mono.advance(100.)
    with pytest.raises(ClockUnavailable, match="monotonic_rollback"):
        value.observe_http_date(sample(mono, date=UTC + 109))


def test_boot_mismatched_sample_does_not_adopt_a_new_clock_inside_existing_process():
    value, mono = anchored()
    with pytest.raises(ClockUnavailable, match="sample_boot_mismatch"):
        value.observe_http_date(sample(mono, boot="different-boot"))
    with pytest.raises(ClockUnavailable):
        value.event_time()


def test_compaction_guard_enforces_strict_checks_on_store_event_time_and_expires_mid_transaction():
    value, mono = anchored(verified_ttl_seconds=1.)
    with value.compaction_guard():
        assert value.event_time() == value()
        mono.advance(1.01)
        with pytest.raises(ClockUnavailable, match="verification_expired"):
            value.event_time()
    assert isinstance(value.event_time(), float)
    with pytest.raises(ClockUnavailable, match="verification_expired"):
        with value.compaction_guard():
            pass


def test_same_boot_restart_reuses_private_json_and_exact_origin(tmp_path):
    path = tmp_path / "private" / "timeline-anchor.json"
    value, mono = anchored(anchor_path=path)
    before = value.event_time(); mono.advance(7.)
    restored = clock(mono, anchor_path=path)
    assert restored.event_time() == pytest.approx(before + 7 * .9995)
    assert restored.safe_for_compaction()
    data = json.loads(path.read_text())
    assert len(path.read_bytes()) < 2048 and SOURCE not in path.read_text()
    assert set(data) == {"schema_version", "revision", "boot_id", "source_sha256", "policy_sha256", "anchor_monotonic",
        "utc_estimate_at_anchor", "base_uncertainty_seconds", "verified_monotonic", "saved_monotonic", "verification_status", "last_error", "checksum"}
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_new_boot_requires_a_fresh_trusted_date_before_replacing_old_boot_anchor(tmp_path):
    path = tmp_path / "anchor.json"; value, mono = anchored(anchor_path=path)
    new_mono = Mono(1.)
    fresh = StableTimelineClock("synthetic-boot-b", SOURCE, lambda sample: True, utc_bounds=(UTC - 86400, UTC + 86400),
                               anchor_path=path, monotonic=new_mono)
    assert not fresh.safe_for_compaction()
    with pytest.raises(ClockUnavailable, match="anchor_boot_changed"):
        fresh.event_time()
    fresh.observe_http_date(sample(new_mono, boot="synthetic-boot-b", date=UTC + 60))
    assert fresh.safe_for_compaction() and json.loads(path.read_text())["boot_id"] == "synthetic-boot-b"


def test_persisted_rejection_survives_restart_without_forgetting_the_event_anchor(tmp_path):
    path = tmp_path / "anchor.json"; value, mono = anchored(anchor_path=path)
    mono.advance(2.)
    with pytest.raises(ClockUnavailable):
        value.observe_http_date(sample(mono, date=UTC + 120))
    restored = clock(mono, anchor_path=path)
    assert isinstance(restored.event_time(), float) and not restored.safe_for_compaction()
    restored.observe_http_date(sample(mono, date=UTC + 2))
    assert restored.safe_for_compaction()


def test_damaged_or_nonprivate_anchor_does_not_fall_back_to_unverified_wall_time(tmp_path):
    path = tmp_path / "anchor.json"; value, mono = anchored(anchor_path=path)
    body = json.loads(path.read_text()); body["utc_estimate_at_anchor"] += 1000
    path.write_text(json.dumps(body))
    broken = clock(mono, anchor_path=path)
    assert not broken.safe_for_compaction()
    with pytest.raises(ClockUnavailable, match="corrupt_anchor"):
        broken.event_time()


def test_cross_process_stale_writer_cannot_overwrite_newer_verification(tmp_path):
    path = tmp_path / "anchor.json"; first, mono = anchored(anchor_path=path)
    stale = clock(mono, anchor_path=path)
    mono.advance(3.)
    first.observe_http_date(sample(mono, date=UTC + 3))
    saved = path.read_bytes()
    with pytest.raises(ClockUnavailable, match="anchor_revision_conflict"):
        stale.observe_http_date(sample(mono, date=UTC + 3))
    assert path.read_bytes() == saved and not stale.safe_for_compaction()
    assert isinstance(stale.event_time(), float)


def test_anchor_atomic_write_failure_keeps_prior_file_and_disables_cleanup(tmp_path):
    path = tmp_path / "anchor.json"; value, mono = anchored(anchor_path=path)
    old = path.read_bytes(); mono.advance(2.)
    with patch("common.board_timeline_clock.os.replace", side_effect=OSError("synthetic failure")):
        with pytest.raises(ClockUnavailable, match="anchor_write_failed"):
            value.observe_http_date(sample(mono, date=UTC + 2))
    assert path.read_bytes() == old and not value.safe_for_compaction()
    assert not list(path.parent.glob("*.tmp"))


def test_same_boot_policy_change_requires_explicit_reconciliation_not_a_silent_new_anchor(tmp_path):
    path = tmp_path / "anchor.json"; value, mono = anchored(anchor_path=path)
    changed = clock(mono, anchor_path=path, server_error_seconds=.1)
    assert not changed.safe_for_compaction()
    with pytest.raises(ClockUnavailable, match="anchor_source_or_policy_mismatch"):
        changed.observe_http_date(sample(mono))


def test_saved_monotonic_ahead_of_new_process_is_a_fail_closed_rollback(tmp_path):
    path = tmp_path / "anchor.json"; value, mono = anchored(anchor_path=path)
    restored = clock(Mono(99.), anchor_path=path)
    assert not restored.safe_for_compaction()
    with pytest.raises(ClockUnavailable, match="monotonic_rollback"):
        restored.event_time()


def test_same_boot_refresh_does_not_narrow_uncertainty_or_advance_retention_time():
    value, mono = anchored(drift_ppm=500.)
    mono.advance(600.)
    before = value.quality_snapshot()
    value.observe_http_date(sample(mono, date=UTC + 600, rtt=.001))
    after = value.quality_snapshot()
    assert after["utc_lower_bound"] == before["utc_lower_bound"]
    assert after["uncertainty_seconds"] == before["uncertainty_seconds"]


def test_source_verifier_exception_never_exports_its_message_or_grants_trust():
    mono = Mono()
    def reject(_):
        raise RuntimeError("private upstream detail must not escape")
    value = StableTimelineClock("synthetic-boot-a", SOURCE, reject, utc_bounds=(UTC - 100, UTC + 100), monotonic=mono)
    with pytest.raises(ClockUnavailable) as error:
        value.observe_http_date(sample(mono))
    assert str(error.value) == "source_not_verified"


def test_future_received_time_and_nonfinite_monotonic_fail_closed():
    value, mono = anchored()
    incoming = HttpDateSample(SOURCE, sample(mono).date_header, 100., 100.1, "synthetic-boot-a")
    with pytest.raises(ClockUnavailable, match="invalid_sample_monotonic_order"):
        value.observe_http_date(incoming)
    assert isinstance(value.event_time(), float) and not value.safe_for_compaction()
    mono.value = float("nan")
    assert value.quality_snapshot()["event_time_available"] is False


def test_posix_nonprivate_anchor_is_refused(tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX mode ownership check; Windows uses caller ACL")
    path = tmp_path / "anchor.json"; value, mono = anchored(anchor_path=path)
    os.chmod(str(path), 0o644)
    restored = clock(mono, anchor_path=path)
    assert not restored.safe_for_compaction()
    with pytest.raises(ClockUnavailable, match="anchor_not_private"):
        restored.event_time()


def memory_fixture(tmp_path, **options):
    value, mono = anchored(**options)
    store = BoardMemoryStore(tmp_path / "synthetic-clock-memory.sqlite3", clock=value.event_time)
    store.append_event({"kind": "conversation", "id": "synthetic"}, "synthetic-source", "user_said", "合成内容")
    mono.advance(301.)
    return value, mono, store


def summary(prepared):
    return {"schema_version": 1, "scope": prepared["scope"], "topic": prepared["topic"],
            "start_utc": prepared["start_utc"], "end_utc": prepared["end_utc"],
            "source_refs": [{"event_id": s["event_id"], "revision": s["revision"]}
                            for s in prepared["sources"] if s["include_in_summary"]],
            "summary": "用户陈述合成内容", "keywords": ["合成"], "claims": prepared["required_claims"]}


def test_worker_idle_check_then_clock_expiry_retains_bodies_and_later_recovers(tmp_path):
    value, mono, store = memory_fixture(tmp_path, verified_ttl_seconds=302.)
    calls = []; first = [True]
    def idle():
        if first[0]:
            first[0] = False
            mono.advance(2.)  # State changed just after the caller's idle check.
        return True
    def model(p, cancelled):
        calls.append(p["task_id"])
        return summary(p)
    worker = BoardMemoryWorker(store, model, idle=idle, compaction_guard_factory=value.compaction_guard)
    assert not worker.step() and worker.error == "clock_unverified" and calls == []
    assert store.health()["active_bodies"] == 1 and store.health()["active_leases"] == 0
    value.observe_http_date(sample(mono, date=UTC + 303))
    assert worker.step() and worker.completed == 1 and store.health()["active_bodies"] == 0


def test_worker_clock_conflict_during_llm_discards_candidate_then_verification_restores_progress(tmp_path):
    value, mono, store = memory_fixture(tmp_path)
    first = [True]
    def model(p, cancelled):
        assert value.active_compactions == 0
        if first[0]:
            first[0] = False
            with pytest.raises(ClockUnavailable, match="http_date_conflicts_with_anchor"):
                value.observe_http_date(sample(mono, date=UTC + 3600))
        return summary(p)
    worker = BoardMemoryWorker(store, model, idle=lambda: value.safe_for_compaction(),
                               compaction_guard_factory=value.compaction_guard)
    assert not worker.step() and worker.error == "clock_unverified"
    assert store.health()["active_bodies"] == 1 and store.health()["valid_summaries"] == 0
    assert store.health()["active_leases"] == 0
    value.observe_http_date(sample(mono, date=UTC + 301))
    assert worker.step() and store.health()["valid_summaries"] == 1


def test_worker_ttl_expiring_inside_llm_is_rechecked_at_commit(tmp_path):
    value, mono, store = memory_fixture(tmp_path, verified_ttl_seconds=302.)
    def model(p, cancelled):
        mono.advance(2.)
        return summary(p)
    worker = BoardMemoryWorker(store, model, idle=lambda: True, compaction_guard_factory=value.compaction_guard)
    assert not worker.step() and worker.error == "clock_unverified"
    assert store.health()["active_bodies"] == 1 and store.health()["active_leases"] == 0


def test_no_clock_lease_or_sqlite_write_lock_spans_the_external_model_call(tmp_path):
    value, mono, store = memory_fixture(tmp_path)
    entered = threading.Event(); release = threading.Event(); outcome = []
    def model(p, cancelled):
        assert value.active_compactions == 0
        # A separate writer and Date sample are both possible while the model
        # is pending. No process/model is actually launched in this test.
        with sqlite3.connect(store.path, isolation_level=None) as db:
            db.execute("BEGIN IMMEDIATE"); db.rollback()
        entered.set()
        assert release.wait(.5)
        return summary(p)
    worker = BoardMemoryWorker(store, model, idle=lambda: True, compaction_guard_factory=value.compaction_guard)
    thread = threading.Thread(target=lambda: outcome.append(worker.step()))
    thread.start(); assert entered.wait(.5)
    value.observe_http_date(sample(mono, date=UTC + 301))
    release.set(); thread.join(.5)
    assert not thread.is_alive() and outcome == [True]


def test_quality_lease_has_no_clock_mutex_while_another_store_writer_reads_time(tmp_path, monkeypatch):
    value, mono, store = memory_fixture(tmp_path)
    commit_entered = threading.Event(); input_clock_read = threading.Event(); outcomes = []; errors = []
    original = store.commit_compaction
    def commit(*args):
        commit_entered.set()
        assert input_clock_read.wait(.5)
        return original(*args)
    monkeypatch.setattr(store, "commit_compaction", commit)
    worker = BoardMemoryWorker(store, lambda p, cancelled: summary(p), idle=lambda: True,
                               compaction_guard_factory=value.compaction_guard)
    def work():
        try:
            outcomes.append(worker.step())
        except Exception as exc:
            errors.append(exc)
    def ordinary_input():
        try:
            with store._db(True):
                assert isinstance(value.event_time(), float)
                input_clock_read.set()
        except Exception as exc:
            errors.append(exc)
    thread = threading.Thread(target=work); thread.start()
    assert commit_entered.wait(.5)
    dialogue = threading.Thread(target=ordinary_input); dialogue.start()
    dialogue.join(.5); thread.join(.5)
    assert not dialogue.is_alive() and not thread.is_alive() and errors == [] and outcomes == [True]


def test_date_writer_waits_for_quality_lease_while_event_time_keeps_working():
    value, mono = anchored()
    read_done = threading.Event(); write_done = threading.Event(); errors = []
    def write():
        try:
            value.observe_http_date(sample(mono), wait_timeout=.5)
            write_done.set()
        except Exception as exc:
            errors.append(exc)
    def record():
        value.event_time(); read_done.set()
    with value.compaction_guard():
        writer = threading.Thread(target=write); reader = threading.Thread(target=record)
        writer.start(); reader.start()
        assert read_done.wait(.2) and not write_done.is_set()
    writer.join(.5); reader.join(.5)
    assert write_done.is_set() and errors == []


@pytest.mark.parametrize("cancelled,reason", [(None, "clock_update_busy"), (lambda: True, "clock_update_cancelled")])
def test_date_writer_wait_is_bounded_or_cancellable_without_a_reentrant_deadlock(cancelled, reason):
    value, mono = anchored(); errors = []
    def write():
        try:
            value.observe_http_date(sample(mono), wait_timeout=.005, cancelled=cancelled)
        except ClockUnavailable as exc:
            errors.append(str(exc))
    with value.compaction_guard():
        thread = threading.Thread(target=write); thread.start(); thread.join(.2)
        assert not thread.is_alive() and errors == [reason]
        assert isinstance(value.event_time(), float)
        with pytest.raises(RuntimeError, match="programming error"):
            value.observe_http_date(sample(mono))
    assert not value.safe_for_compaction() and isinstance(value.event_time(), float)


def test_clock_rejection_does_not_stop_the_worker_thread(tmp_path):
    value, mono, store = memory_fixture(tmp_path, verified_ttl_seconds=302.)
    mono.advance(2.)
    repeated = threading.Event(); calls = [0]
    def idle():
        calls[0] += 1
        if calls[0] >= 2:
            repeated.set()
        return True
    worker = BoardMemoryWorker(store, lambda p, cancelled: summary(p), idle=idle, interval=.01,
                               compaction_guard_factory=value.compaction_guard)
    worker.start()
    try:
        assert repeated.wait(.5) and worker.thread.is_alive() and worker.error == "clock_unverified"
        assert store.health()["active_bodies"] == 1
    finally:
        worker.close()


def test_guard_factory_and_commit_programming_errors_are_not_reported_as_clock_failures(tmp_path, monkeypatch):
    value, mono, store = memory_fixture(tmp_path)
    @contextmanager
    def broken_guard():
        raise RuntimeError("synthetic factory bug")
        yield
    worker = BoardMemoryWorker(store, lambda p, cancelled: summary(p), idle=lambda: True,
                               compaction_guard_factory=broken_guard)
    with pytest.raises(RuntimeError, match="factory bug"):
        worker.step()
    def broken_commit(*args):
        raise KeyError("synthetic commit bug")
    monkeypatch.setattr(store, "commit_compaction", broken_commit)
    worker = BoardMemoryWorker(store, lambda p, cancelled: summary(p), idle=lambda: True,
                               compaction_guard_factory=value.compaction_guard)
    with pytest.raises(KeyError, match="commit bug"):
        worker.step()
    assert value.active_compactions == 0 and store.health()["active_bodies"] == 1


@pytest.mark.parametrize("fatal", ["rollback", "boot-mismatch"])
def test_fatal_clock_in_cleanup_keeps_real_store_body_and_lease_and_worker_alive(tmp_path, fatal):
    value, mono = anchored()
    cleanup_attempted = threading.Event(); retried = threading.Event(); idle_calls = [0]
    class ClockCheckedStore(BoardMemoryStore):
        # A strict adapter may gate even task-release bookkeeping. Exercise the
        # real SQLite store with that clock failure; no fake transcript store.
        def fail_compaction(self, *args, **kwargs):
            cleanup_attempted.set()
            value.event_time()
            return super().fail_compaction(*args, **kwargs)
    store = ClockCheckedStore(tmp_path / "fatal-clock.sqlite3", clock=value.event_time)
    store.append_event({"kind": "conversation", "id": "synthetic"}, "source", "user_said", "合成内容")
    mono.advance(301.)
    def idle():
        idle_calls[0] += 1
        if cleanup_attempted.is_set():
            retried.set()
        return True
    def model(prepared, cancelled):
        if fatal == "rollback":
            value.event_time(); mono.advance(-1.)
            with pytest.raises(ClockUnavailable, match="monotonic_rollback"):
                value.event_time()
        else:
            with pytest.raises(ClockUnavailable, match="sample_boot_mismatch"):
                value.observe_http_date(sample(mono, boot="different-boot"))
        return summary(prepared)
    worker = BoardMemoryWorker(store, model, idle=idle, interval=.01,
                               compaction_guard_factory=value.compaction_guard)
    worker.start()
    try:
        assert cleanup_attempted.wait(.5) and retried.wait(.5)
        assert worker.thread.is_alive() and worker.error == "clock_unverified"
        with sqlite3.connect(store.path) as db:
            assert db.execute("SELECT count(*) FROM bm_bodies").fetchone()[0] == 1
            assert db.execute("SELECT count(*) FROM bm_summaries").fetchone()[0] == 0
            assert db.execute("SELECT status FROM bm_tasks").fetchone()[0] == "leased"
            assert db.execute("SELECT reserved_task FROM bm_events").fetchone()[0]
    finally:
        worker.close()
