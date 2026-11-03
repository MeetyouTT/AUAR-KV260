"""Stable board UTC estimate from explicitly verified HTTP Date samples.

No networking, system time, NTP, service, business transcript or private key is
accessed here. The caller must obtain Date from its configured Windows model
health response and validate the actual endpoint, HTTP status and redirect/
ownership policy. A source label or Date header is not authentication by itself.

Use ``clock.event_time`` for Store timestamps, and gate idle work with
``safe_for_compaction``. Also wrap each destructive prepare/commit transaction
in ``compaction_guard``; an idle check alone has a check/use race. Never retain
the guard across a model/network call. ``clock()`` is the strict lower-bound UTC
clock. Uncertain but continuous same-boot event timing remains available after
verification expiry or a conflicting sample; cleanup does not.

The guard is a QUALITY READ LEASE, not a mutex held while waiting for SQLite.
Date/load/save writers wait a bounded/cancellable interval with the clock mutex
released. This preserves Store's SQLite -> clock lock order for ordinary input.
Quality is validated on guard entry and whenever Store reads its clock, not at
every nanosecond or after SQL COMMIT. A natural TTL boundary can therefore be
crossed by the final part of an already short transaction; no rollback is claimed
after COMMIT. Date changes serialize after the complete guarded transaction.

The event timestamp is a CONSERVATIVE UTC estimate, not the interval midpoint.
This keeps the same Store clock usable for recording and retention without
rounding uncertainty forward. Its slope is <= board monotonic time. The error
budget includes whole-second Date resolution, the complete observed RTT,
caller-declared server clock error and monotonic drift. These are assumptions,
not a measured NTP-grade accuracy guarantee. Fresh samples verify an existing
same-boot anchor; they never move it or narrow its error bound.
HTTP Date is an origination-time approximation (RFC 9110 section 6.6.1), not a
time synchronization protocol: https://www.rfc-editor.org/rfc/rfc9110.html#section-6.6.1
The caller must reject cached/intermediary/redirected responses it cannot bind
to the configured origin. One full second is allowed on BOTH sides of Date,
without assuming how that server rounds its integer-second header.

Persistent deployments should provide a board-private anchor_path and one
anchor writer, matching the memory store's single-writer ownership. Atomic JSON
and a short nonblocking OS file lock support restart handoff, not a new service.
Checksum detects damage; it is not a signature. POSIX files are mode 0600;
Windows directory ACLs, when used for tests, remain the caller's responsibility.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timezone
from email.utils import format_datetime, parsedate_to_datetime
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import threading
import time


SCHEMA_VERSION = 1
DATE_FORMAT = re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), [0-9]{2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
                         r"[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT")
ANCHOR_FIELDS = {"schema_version", "revision", "boot_id", "source_sha256", "policy_sha256", "anchor_monotonic",
                 "utc_estimate_at_anchor", "base_uncertainty_seconds", "verified_monotonic", "saved_monotonic",
                 "verification_status", "last_error"}
ERROR_CODES = {"", "uninitialized", "invalid_clock_number", "invalid_monotonic", "monotonic_rollback", "verification_expired",
               "utc_bounds_exhausted", "invalid_date_sample", "sample_boot_mismatch", "source_not_verified",
               "invalid_sample_monotonic_order", "sample_rtt_exceeded", "sample_too_old", "invalid_http_date",
               "http_date_out_of_bounds", "sample_older_than_verification", "http_date_conflicts_with_anchor",
               "anchor_symlink_rejected", "invalid_anchor_file", "anchor_not_private", "corrupt_anchor", "anchor_path_required",
               "anchor_boot_changed", "anchor_source_or_policy_mismatch", "anchor_read_failed", "anchor_busy_or_unwritable",
               "anchor_unavailable", "anchor_revision_conflict", "same_boot_anchor_replacement_rejected", "anchor_disappeared",
               "anchor_write_failed", "date_update_pending", "clock_update_busy", "clock_update_cancelled"}


class ClockUnavailable(RuntimeError):
    """A fixed diagnostic code; never includes endpoint/header/business data."""


@dataclass(frozen=True)
class HttpDateSample:
    source_id: str
    date_header: str
    sent_monotonic: float
    received_monotonic: float
    boot_id: str


def _number(value, *, minimum=0.):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ClockUnavailable("invalid_clock_number")
    return float(value)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class StableTimelineClock:
    def __init__(self, boot_id, source_id, source_validator, *, utc_bounds, anchor_path=None,
                 monotonic=time.monotonic, max_rtt_seconds=1., max_sample_age_seconds=2.,
                 verified_ttl_seconds=3600., server_error_seconds=1., drift_ppm=500.):
        if not isinstance(boot_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", boot_id):
            raise ValueError("Invalid board boot identifier")
        if not isinstance(source_id, str) or not 1 <= len(source_id) <= 256 or any(ord(c) < 32 for c in source_id):
            raise ValueError("Invalid configured Date source")
        if not callable(source_validator) or not callable(monotonic):
            raise ValueError("Explicit source verifier and monotonic clock required")
        if not isinstance(utc_bounds, (tuple, list)) or len(utc_bounds) != 2:
            raise ValueError("An explicit trusted UTC plausibility window is required")
        try:
            minimum, maximum = (_number(v) for v in utc_bounds)
            policy = {"utc_min": minimum, "utc_max": maximum, "max_rtt": _number(max_rtt_seconds),
                      "max_sample_age": _number(max_sample_age_seconds), "verified_ttl": _number(verified_ttl_seconds),
                      "server_error": _number(server_error_seconds), "drift_ppm": _number(drift_ppm), "date_quantization_seconds": 1.}
        except ClockUnavailable as exc:
            raise ValueError("Invalid clock policy") from exc
        if (minimum >= maximum or not 0 < policy["max_rtt"] <= 30 or not 0 < policy["max_sample_age"] <= 60
                or not 0 < policy["verified_ttl"] <= 7 * 86400 or policy["server_error"] > 60 or policy["drift_ppm"] > 10000):
            raise ValueError("Invalid clock policy bounds")
        self.boot_id = boot_id; self.source_id = source_id; self.source_validator = source_validator
        self.monotonic = monotonic; self.policy = policy
        self.source_sha256 = _sha(source_id); self.policy_sha256 = _sha(_json(policy))
        self.anchor_path = Path(anchor_path).absolute() if anchor_path is not None else None
        self.lock = threading.RLock(); self.local = threading.local()
        self.condition = threading.Condition(self.lock)
        self.active_compactions = 0; self.pending_writers = 0; self.deferred_rejection = ""
        self.anchor = None; self.last_seen = None; self.file_revision = 0
        self.status = "uninitialized"; self.last_error = "uninitialized"; self.fatal = False
        if self.anchor_path is not None and self.anchor_path.exists():
            self.load()

    def _mono(self):
        try:
            now = _number(self.monotonic())
        except (ClockUnavailable, ValueError, TypeError, OverflowError):
            self.fatal = True; self.status = "rejected"; self.last_error = "invalid_monotonic"
            raise ClockUnavailable(self.last_error) from None
        if self.last_seen is not None and now < self.last_seen:
            self.fatal = True; self.status = "rejected"; self.last_error = "monotonic_rollback"
            raise ClockUnavailable(self.last_error)
        self.last_seen = now
        return now

    def _reading(self, now, *, strict):
        if self.fatal:
            raise ClockUnavailable(self.last_error)
        if self.anchor is None:
            raise ClockUnavailable(self.last_error)
        anchor = self.anchor
        if now < max(anchor["anchor_monotonic"], anchor["verified_monotonic"]):
            self.fatal = True; self.status = "rejected"; self.last_error = "monotonic_rollback"
            raise ClockUnavailable(self.last_error)
        age = now - anchor["anchor_monotonic"]
        uncertainty = anchor["base_uncertainty_seconds"] + age * self.policy["drift_ppm"] / 1e6
        estimate = anchor["utc_estimate_at_anchor"] + age
        verified_age = now - anchor["verified_monotonic"]
        reason = self.last_error if self.status != "verified" else "verification_expired" if verified_age > self.policy["verified_ttl"] else ""
        if not getattr(self.local, "strict_depth", 0):
            if self.pending_writers:
                reason = "date_update_pending"
            elif self.deferred_rejection:
                reason = self.deferred_rejection
        if estimate - uncertainty < self.policy["utc_min"] or estimate + uncertainty > self.policy["utc_max"]:
            reason = "utc_bounds_exhausted"
        if strict and reason:
            raise ClockUnavailable(reason)
        return {"utc_estimate": estimate, "utc_lower_bound": estimate - uncertainty, "utc_upper_bound": estimate + uncertainty,
                "uncertainty_seconds": uncertainty, "verified_age_seconds": verified_age, "anchor_age_seconds": age,
                "safe_for_compaction": not bool(reason), "quality": "verified" if not reason else "estimated_degraded",
                "reason": reason}

    def __call__(self):
        with self.lock:
            return self._reading(self._mono(), strict=True)["utc_lower_bound"]

    def event_time(self):
        """Continuous conservative estimate; does not authorize cleanup."""
        with self.lock:
            strict = bool(getattr(self.local, "strict_depth", 0))
            return self._reading(self._mono(), strict=strict)["utc_lower_bound"]

    def quality_snapshot(self):
        with self.lock:
            try:
                reading = self._reading(self._mono(), strict=False)
                return dict(reading, anchored=True, event_time_available=True, error_budget="caller_declared_not_ntp",
                            persistent=bool(self.anchor_path), same_boot=True)
            except ClockUnavailable as exc:
                return {"anchored": self.anchor is not None, "event_time_available": False, "safe_for_compaction": False,
                        "quality": "unavailable", "reason": str(exc), "persistent": bool(self.anchor_path), "same_boot": False}

    snapshot = quality_snapshot

    def safe_for_compaction(self):
        return self.quality_snapshot()["safe_for_compaction"]

    @contextmanager
    def compaction_guard(self):
        """Quality lease for short prepare/commit; no mutex spans SQL or LLM."""
        with self.lock:
            self._reading(self._mono(), strict=True)
            depth = getattr(self.local, "strict_depth", 0)
            self.local.strict_depth = depth + 1
            self.active_compactions += 1
        try:
            yield self
        finally:
            with self.lock:
                self.local.strict_depth = depth
                self.active_compactions -= 1
                if self.active_compactions == 0:
                    if self.deferred_rejection:
                        self.status = "rejected"; self.last_error = self.deferred_rejection
                        self.deferred_rejection = ""
                    self.condition.notify_all()

    def _wait_for_compactions(self, wait_timeout=.25, cancelled=None):
        if getattr(self.local, "strict_depth", 0):
            raise RuntimeError("Clock update inside compaction guard is a programming error")
        if not isinstance(wait_timeout, (int, float)) or isinstance(wait_timeout, bool) or not 0 < wait_timeout <= 2:
            raise ValueError("Clock update wait must be bounded")
        deadline = time.perf_counter() + wait_timeout
        self.pending_writers += 1
        try:
            while self.active_compactions:
                if cancelled is not None and cancelled():
                    self.deferred_rejection = "clock_update_cancelled"
                    raise ClockUnavailable("clock_update_cancelled")
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    self.deferred_rejection = "clock_update_busy"
                    raise ClockUnavailable("clock_update_busy")
                self.condition.wait(min(.02, remaining))
        finally:
            self.pending_writers -= 1

    def observe_http_date(self, sample, *, wait_timeout=.25, cancelled=None):
        """Caller supplies the actual verified response and monotonic timings.

        A later same-boot Date never changes the origin or narrows uncertainty.
        A contradictory/rejected sample disables cleanup but keeps old-anchor
        event estimates available. Only a new trustworthy matching sample may
        restore verification. A monotonic rollback is permanent for the object.
        The source validator must be cheap and side-effect free: obtain and
        validate the actual HTTP response before this method, never fetch it
        under this clock's lock or a compaction guard.
        """
        with self.lock:
            self._wait_for_compactions(wait_timeout, cancelled)
            try:
                now = self._mono()
                if self.fatal:
                    raise ClockUnavailable(self.last_error)
                if not isinstance(sample, HttpDateSample):
                    raise ClockUnavailable("invalid_date_sample")
                if sample.boot_id != self.boot_id:
                    self.fatal = True
                    raise ClockUnavailable("sample_boot_mismatch")
                if sample.source_id != self.source_id:
                    raise ClockUnavailable("source_not_verified")
                try:
                    verified = self.source_validator(sample)
                except Exception:
                    verified = False
                if verified is not True:
                    raise ClockUnavailable("source_not_verified")
                sent = _number(sample.sent_monotonic); received = _number(sample.received_monotonic)
                if sent > received or received > now:
                    raise ClockUnavailable("invalid_sample_monotonic_order")
                rtt = received - sent
                if rtt > self.policy["max_rtt"]:
                    raise ClockUnavailable("sample_rtt_exceeded")
                if now - received > self.policy["max_sample_age"]:
                    raise ClockUnavailable("sample_too_old")
                if not isinstance(sample.date_header, str) or not DATE_FORMAT.fullmatch(sample.date_header):
                    raise ClockUnavailable("invalid_http_date")
                try:
                    parsed = parsedate_to_datetime(sample.date_header)
                    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed) or format_datetime(parsed, usegmt=True) != sample.date_header:
                        raise ValueError("Noncanonical Date")
                    date = _number(parsed.timestamp())
                except (ValueError, TypeError, OverflowError):
                    raise ClockUnavailable("invalid_http_date") from None
                center = date + rtt / 2
                uncertainty = self.policy["server_error"] + self.policy["date_quantization_seconds"] + rtt / 2
                if center - uncertainty < self.policy["utc_min"] or center + uncertainty > self.policy["utc_max"]:
                    raise ClockUnavailable("http_date_out_of_bounds")
                if self.anchor is None:
                    self.anchor = {"anchor_monotonic": received, "utc_estimate_at_anchor": center,
                                   "base_uncertainty_seconds": uncertainty, "verified_monotonic": received}
                else:
                    # Project both intervals to receipt time. Back-dated samples
                    # may not shrink/replace an already newer verified sample.
                    if received < self.anchor["verified_monotonic"]:
                        raise ClockUnavailable("sample_older_than_verification")
                    projected = self._reading(now, strict=False)
                    delta = now - received
                    low = center - uncertainty + delta * (1 - self.policy["drift_ppm"] / 1e6)
                    high = center + uncertainty + delta * (1 + self.policy["drift_ppm"] / 1e6)
                    if high < projected["utc_lower_bound"] or low > projected["utc_upper_bound"]:
                        raise ClockUnavailable("http_date_conflicts_with_anchor")
                    self.anchor["verified_monotonic"] = received
                self.status = "verified"; self.last_error = ""
                if self.anchor_path is not None:
                    self._save_locked()
                return self._reading(now, strict=True)
            except ClockUnavailable as exc:
                self.status = "rejected"; self.last_error = str(exc)
                if self.anchor is not None and self.anchor_path is not None and not self.fatal:
                    try:
                        self._save_locked()
                    except ClockUnavailable:
                        pass  # Local strict mode remains rejected regardless.
                raise

    @staticmethod
    def _private_path(path):
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ClockUnavailable("anchor_symlink_rejected")

    @staticmethod
    def _record(path):
        StableTimelineClock._private_path(path)
        if path.stat().st_size > 4096 or not stat.S_ISREG(path.stat().st_mode):
            raise ClockUnavailable("invalid_anchor_file")
        if os.name == "posix" and (stat.S_IMODE(path.stat().st_mode) & 0o077 or path.stat().st_uid != os.getuid()):
            raise ClockUnavailable("anchor_not_private")
        try:
            def unique(pairs):
                out = {}
                for key, value in pairs:
                    if key in out:
                        raise ValueError("Duplicate anchor key")
                    out[key] = value
                return out
            value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
            if not isinstance(value, dict) or set(value) != ANCHOR_FIELDS | {"checksum"}:
                raise ValueError("Invalid anchor fields")
            checksum = value.pop("checksum")
            if not isinstance(checksum, str) or not hmac.compare_digest(checksum, _sha(_json(value))):
                raise ValueError("Anchor checksum mismatch")
            if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
                raise ValueError("Unknown anchor schema")
            if type(value["revision"]) is not int or value["revision"] < 1:
                raise ValueError("Invalid anchor revision")
            if not isinstance(value["boot_id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", value["boot_id"]):
                raise ValueError("Invalid anchor boot")
            for field in ("source_sha256", "policy_sha256"):
                if not isinstance(value[field], str) or not re.fullmatch(r"[0-9a-f]{64}", value[field]):
                    raise ValueError("Invalid anchor fingerprint")
            for key in ("anchor_monotonic", "utc_estimate_at_anchor", "base_uncertainty_seconds", "verified_monotonic", "saved_monotonic"):
                _number(value[key])
            if (value["verification_status"] not in {"verified", "rejected"} or value["last_error"] not in ERROR_CODES
                    or (value["verification_status"] == "verified" and value["last_error"] != "")):
                raise ValueError("Invalid verification state")
            if value["verified_monotonic"] < value["anchor_monotonic"] or value["saved_monotonic"] < value["verified_monotonic"]:
                raise ValueError("Invalid anchor monotonic order")
            return value
        except (ValueError, TypeError, KeyError, ClockUnavailable):
            raise ClockUnavailable("corrupt_anchor") from None

    def load(self):
        with self.lock:
            self._wait_for_compactions()
            if self.anchor_path is None:
                raise ClockUnavailable("anchor_path_required")
            try:
                value = self._record(self.anchor_path)
                now = self._mono()
                self.file_revision = value["revision"]
                if value["boot_id"] != self.boot_id:
                    self.anchor = None; self.status = "uninitialized"; self.last_error = "anchor_boot_changed"
                    return False
                if value["source_sha256"] != self.source_sha256 or value["policy_sha256"] != self.policy_sha256:
                    raise ClockUnavailable("anchor_source_or_policy_mismatch")
                if now < value["saved_monotonic"]:
                    self.fatal = True
                    raise ClockUnavailable("monotonic_rollback")
                self.anchor = {key: value[key] for key in ("anchor_monotonic", "utc_estimate_at_anchor", "base_uncertainty_seconds", "verified_monotonic")}
                self.status = value["verification_status"]; self.last_error = value["last_error"]
                self._reading(now, strict=False)
                return True
            except (ClockUnavailable, OSError) as exc:
                self.anchor = None; self.status = "rejected"
                self.last_error = str(exc) if isinstance(exc, ClockUnavailable) else "anchor_read_failed"
                self.fatal = True
                return False

    @contextmanager
    def _file_lock(self):
        lock_path = self.anchor_path.with_name(self.anchor_path.name + ".lock")
        self._private_path(lock_path)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(str(lock_path), flags, 0o600)
        locked = False
        try:
            try:
                if os.name == "posix":
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    import msvcrt
                    if os.fstat(fd).st_size == 0:
                        os.write(fd, b"0")
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError:
                raise ClockUnavailable("anchor_busy_or_unwritable") from None
            locked = True
            yield
        finally:
            if locked:
                if os.name == "posix":
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
                else:
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET); msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            os.close(fd)

    def _save_locked(self):
        if self.anchor is None or self.anchor_path is None:
            raise ClockUnavailable("anchor_unavailable")
        now = self._mono()
        self._private_path(self.anchor_path)
        self.anchor_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self.anchor_path.with_name(self.anchor_path.name + "." + secrets.token_hex(8) + ".tmp")
        try:
            with self._file_lock():
                if self.anchor_path.exists():
                    previous = self._record(self.anchor_path)
                    if previous["revision"] != self.file_revision:
                        raise ClockUnavailable("anchor_revision_conflict")
                    if previous["boot_id"] == self.boot_id:
                        if previous["source_sha256"] != self.source_sha256 or previous["policy_sha256"] != self.policy_sha256:
                            raise ClockUnavailable("anchor_source_or_policy_mismatch")
                        for key in ("anchor_monotonic", "utc_estimate_at_anchor", "base_uncertainty_seconds"):
                            if previous[key] != self.anchor[key]:
                                raise ClockUnavailable("same_boot_anchor_replacement_rejected")
                elif self.file_revision:
                    raise ClockUnavailable("anchor_disappeared")
                value = dict(self.anchor, schema_version=SCHEMA_VERSION, revision=self.file_revision + 1,
                             boot_id=self.boot_id, source_sha256=self.source_sha256, policy_sha256=self.policy_sha256,
                             saved_monotonic=now, verification_status=self.status, last_error=self.last_error)
                encoded = _json(dict(value, checksum=_sha(_json(value)))).encode("utf-8")
                descriptor = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
                os.replace(str(temporary), str(self.anchor_path))
                self.file_revision = value["revision"]
        except ClockUnavailable:
            raise
        except OSError:
            raise ClockUnavailable("anchor_write_failed") from None
        finally:
            if temporary.exists():
                temporary.unlink()

    def save(self):
        with self.lock:
            self._wait_for_compactions()
            try:
                self._save_locked()
            except ClockUnavailable as exc:
                self.status = "rejected"; self.last_error = str(exc)
                raise
