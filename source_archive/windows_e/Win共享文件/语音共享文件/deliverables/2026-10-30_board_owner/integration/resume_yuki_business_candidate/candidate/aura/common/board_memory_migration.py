"""Read-only same-origin legacy snapshot -> empty board memory migration.

No automatic migration or writer switch runs here. The caller supplies a
fingerprinted, quiescent SQLite snapshot, never the live legacy store. Only the
known conversation/fact/control schema is read; identity, speaker attribution,
media and old extractive digest caches are not transferred. Minimal profile
id/name/created catalogue metadata stays in the private target. Reports expose
only counts/fingerprints, not names or IDs. Private scope IDs remain local without
grants. Raw user variants and transport/identity contexts are not duplicated.

All planning and validation precede the bounded target transaction. Source bytes
are hashed again immediately before writing. An import marker and seq mapping
commit atomically with the rows. A retry of the exact completed snapshot is a
read-only no-op even when newer board rows exist; another snapshot cannot replace
them. Returned reports and exceptions contain counts/codes/fingerprints only.

The bridge intentionally refuses profile-owned conversation-local facts: the
current board scope model cannot preserve that extra nested permission boundary.
Played replies without complete dependency coverage, dated ACK evidence, or
migrated source dependencies remain metadata-only and cannot enter recall.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

from .board_memory import (BoardMemoryStore, MemoryBusy, _hash,
                           _json, _text, _time)
from .memory_commands import key_name


BRIDGE_VERSION = 1
ARCHIVE_COMMANDS = {"memory_command", "personal_memory_command", "memory_controls_command"}
KNOWN_EXCLUSIONS = ARCHIVE_COMMANDS | {"memory_update", "personal_memory_update", "memory_clear",
    "personal_memory_clear", "visual_source_invalidated", "deleted_source_dependency"}
FACT_HISTORY_EXCLUSIONS = ARCHIVE_COMMANDS | {"memory_update", "personal_memory_update"}
BUSINESS_COLUMNS = {
    "conversations": ({"id", "created", "revision", "memory_revision"}, set()),
    "turns": ({"seq", "request_id", "conversation_id", "context", "user", "raw_user", "assistant", "samples", "digest",
               "status", "created", "memory_revision"}, {"profile_revision"}),
    "conversation_facts": ({"conversation_id", "key", "value", "source_seq"}, set()),
    "recall_exclusions": ({"seq", "reason"}, set()),
    "profiles": ({"id", "name", "created", "memory_revision"}, set()),
    "conversation_profiles": ({"conversation_id", "profile_id"}, set()),
    "profile_facts": ({"profile_id", "key", "value", "source_seq"}, set()),
    "profile_changes": ({"profile_id", "revision", "operation"}, set()),
    "timeline_played": ({"seq", "received"}, set()),
    "timeline_visual_dependency": ({"seq", "revision"}, set()),
    "memory_source_dependencies": ({"seq", "source_seq"}, set()),
    "memory_source_coverage": ({"seq", "version"}, set()),
    "memory_fact_versions": ({"owner", "key", "value", "source_seq", "recorded", "superseded"}, set()),
}
BUSINESS_PRIMARY_KEYS = {
    "conversations": ["id"], "turns": ["seq"], "conversation_facts": ["conversation_id", "key"],
    "recall_exclusions": ["seq"], "profiles": ["id"], "conversation_profiles": ["conversation_id"],
    "profile_facts": ["profile_id", "key"], "profile_changes": ["profile_id", "revision"],
    "timeline_played": ["seq"], "timeline_visual_dependency": ["seq"],
    "memory_source_dependencies": ["seq", "source_seq"], "memory_source_coverage": ["seq"],
    "memory_fact_versions": ["owner", "key", "source_seq"],
}


class LegacyMigrationRejected(ValueError):
    """A code-only migration rejection; it never includes source content."""


def _reject(code):
    raise LegacyMigrationRejected(code)


def _fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quiescent(path):
    # immutable=1 intentionally ignores sidecars. Therefore none may exist,
    # including empty WALs whose main file may not contain the committed state.
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        _reject("source_not_quiescent_snapshot")


def _integer(value, code, *, minimum=0):
    if type(value) is not int or value < minimum:
        _reject(code)
    return value


def _cid(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        _reject("invalid_legacy_scope_identifier")
    return value


def _stamp(value):
    try:
        return _time(value)
    except ValueError:
        _reject("invalid_legacy_timestamp")


def _string(value, code, limit=32768):
    try:
        return _text(value, limit=limit)
    except ValueError:
        _reject(code)


def _rows(db, table, columns, maximum):
    result = [dict(r) for r in db.execute("SELECT " + ",".join(columns) + " FROM " + table + " LIMIT ?", (maximum + 1,))]
    if len(result) > maximum:
        _reject("source_row_bound_exceeded")
    return result


def _read_plan(path, source_hash, *, imported_at, max_turns):
    uri = path.as_uri() + "?mode=ro&immutable=1"
    db = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=.15)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            _reject("source_integrity_check_failed")
        schema = [tuple(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]
        tables = {r[1] for r in schema if r[0] == "table"}
        if not {"conversations", "turns", "conversation_facts", "recall_exclusions"} <= tables:
            _reject("unsupported_legacy_schema")
        for table, (required, optional) in BUSINESS_COLUMNS.items():
            if table in tables:
                information = list(db.execute("PRAGMA table_info(" + table + ")"))
                columns = {r["name"] for r in information}
                if not required <= columns or columns - required - optional:
                    _reject("unsupported_columns")
                keys = [r["name"] for r in sorted(information, key=lambda r: r["pk"]) if r["pk"]]
                if keys != BUSINESS_PRIMARY_KEYS[table]:
                    _reject("unsupported_primary_key")
        profile_tables = {"profiles", "conversation_profiles", "profile_facts", "profile_changes"}
        if profile_tables & tables and not profile_tables <= tables:
            _reject("partial_profile_schema")
        if profile_tables <= tables and "profile_revision" not in {r["name"] for r in db.execute("PRAGMA table_info(turns)")}:
            _reject("profile_revision_missing")
        user_version = db.execute("PRAGMA user_version").fetchone()[0]
        if user_version != 0 or db.execute("PRAGMA application_id").fetchone()[0] != 0:
            _reject("unsupported_legacy_schema_version")
        conversations = _rows(db, "conversations", ["id", "created", "revision", "memory_revision"], max_turns)
        turn_cols = ["seq", "request_id", "conversation_id", "context", "user", "assistant", "samples", "digest", "status", "created", "memory_revision"]
        if profile_tables <= tables:
            turn_cols.append("profile_revision")
        turns = _rows(db, "turns", turn_cols, max_turns)
        exclusions = _rows(db, "recall_exclusions", ["seq", "reason"], max_turns)
        conversation_facts = _rows(db, "conversation_facts", ["conversation_id", "key", "value", "source_seq"], max_turns * 12)
        profiles = _rows(db, "profiles", ["id", "name", "created", "memory_revision"], max_turns) if "profiles" in tables else []
        profile_links = _rows(db, "conversation_profiles", ["conversation_id", "profile_id"], max_turns) if "conversation_profiles" in tables else []
        profile_facts = _rows(db, "profile_facts", ["profile_id", "key", "value", "source_seq"], max_turns * 12) if "profile_facts" in tables else []
        changes = _rows(db, "profile_changes", ["profile_id", "revision", "operation"], max_turns * 12) if "profile_changes" in tables else []
        played = _rows(db, "timeline_played", ["seq", "received"], max_turns) if "timeline_played" in tables else []
        visual = _rows(db, "timeline_visual_dependency", ["seq", "revision"], max_turns) if "timeline_visual_dependency" in tables else []
        dependencies = _rows(db, "memory_source_dependencies", ["seq", "source_seq"], max_turns * 128) if "memory_source_dependencies" in tables else []
        coverage = _rows(db, "memory_source_coverage", ["seq", "version"], max_turns) if "memory_source_coverage" in tables else []
        versions = _rows(db, "memory_fact_versions", ["owner", "key", "value", "source_seq", "recorded", "superseded"], max_turns * 32) if "memory_fact_versions" in tables else None
        db.rollback()
    except sqlite3.Error as exc:
        raise LegacyMigrationRejected("source_sqlite_read_failed") from None
    finally:
        db.close()
    source_schema = _hash(_json([user_version, schema]))
    import_id = "legacy:" + _hash(_json([BRIDGE_VERSION, source_hash, source_schema]))[:32]
    by_conversation = {}
    for row in conversations:
        cid = _cid(row["id"])
        row["created"] = _stamp(row["created"])
        _integer(row["revision"], "invalid_legacy_revision"); _integer(row["memory_revision"], "invalid_legacy_revision")
        by_conversation[cid] = row
    by_profile = {}
    for row in profiles:
        pid = _cid(row["id"]); row["created"] = _stamp(row["created"])
        if (not isinstance(row["name"], str) or not 1 <= len(row["name"].strip()) <= 40
                or row["name"] != row["name"].strip() or any(ord(c) < 32 for c in row["name"])):
            _reject("invalid_profile_display_name")
        _integer(row["memory_revision"], "invalid_profile_revision")
        by_profile[pid] = row
    links = {}
    for row in profile_links:
        if row["conversation_id"] not in by_conversation or row["profile_id"] not in by_profile:
            _reject("invalid_profile_scope_link")
        links[row["conversation_id"]] = row["profile_id"]
    def owner_for(cid):
        if cid not in by_conversation:
            _reject("unknown_conversation_scope")
        return ("profile", links[cid]) if cid in links else ("conversation", cid)
    by_seq = {}; request_ids = set()
    for row in turns:
        seq = _integer(row["seq"], "invalid_source_seq", minimum=1)
        if seq in by_seq or row["request_id"] in request_ids:
            _reject("duplicate_legacy_turn")
        request_ids.add(row["request_id"])
        row["owner"] = owner_for(row["conversation_id"])
        row["created"] = _stamp(row["created"])
        _string(row["request_id"], "invalid_legacy_request", 256)
        _string(row["user"], "invalid_legacy_user_text")
        if row["assistant"] is not None and not isinstance(row["assistant"], str):
            _reject("invalid_legacy_assistant_text")
        if row["assistant"] is not None and len(row["assistant"].encode("utf-8")) > 32768:
            _reject("legacy_assistant_too_large")
        if row["status"] not in {"submitted", "generated", "played", "interrupted"}:
            _reject("unknown_legacy_turn_status")
        _integer(row["memory_revision"], "invalid_legacy_revision")
        _integer(row.get("profile_revision", 0), "invalid_profile_revision")
        if row["memory_revision"] > by_conversation[row["conversation_id"]]["memory_revision"]:
            _reject("source_revision_ahead_of_owner")
        if row["owner"][0] == "profile":
            if row.get("profile_revision", 0) > by_profile[row["owner"][1]]["memory_revision"]:
                _reject("source_revision_ahead_of_owner")
        elif row.get("profile_revision", 0) != 0:
            _reject("anonymous_turn_has_profile_revision")
        try:
            context = json.loads(row["context"])
            generation = context.get("generation") if isinstance(context, dict) else None
            row["context_valid"] = (isinstance(context, dict) and context.get("request_id") == row["request_id"]
                                     and type(generation) is int and generation >= 0)
            row["generation"] = generation if row["context_valid"] else 0
        except (ValueError, TypeError):
            row["context_valid"] = False; row["generation"] = 0
        row["turn_id"] = "legacy_turn:" + _hash(import_id + ":" + str(seq))[:32]
        row["user_id"] = "user_said:" + _hash(row["turn_id"])[:32]
        row["assistant_id"] = "assistant_reply:" + _hash(row["turn_id"])[:32] if row["assistant"] else None
        by_seq[seq] = row
    exclusion_by_seq = {}
    for row in exclusions:
        if row["seq"] not in by_seq or not isinstance(row["reason"], str) or not row["reason"]:
            _reject("invalid_recall_exclusion")
        exclusion_by_seq[row["seq"]] = row["reason"] if row["reason"] in KNOWN_EXCLUSIONS else "unknown_exclusion"
    played_by_seq = {}
    for row in played:
        if row["seq"] not in by_seq:
            _reject("orphan_playback_receipt")
        stamp = _stamp(row["received"])
        if stamp < by_seq[row["seq"]]["created"]:
            _reject("invalid_playback_time_order")
        played_by_seq[row["seq"]] = stamp
    visual_seqs = set()
    for row in visual:
        if row["seq"] not in by_seq:
            _reject("orphan_visual_dependency")
        _integer(row["revision"], "invalid_visual_revision")
        visual_seqs.add(row["seq"])
    deps = {seq: set() for seq in by_seq}
    for row in dependencies:
        seq, source_seq = row["seq"], row["source_seq"]
        if seq not in by_seq or source_seq not in by_seq or source_seq >= seq or by_seq[seq]["owner"] != by_seq[source_seq]["owner"]:
            _reject("invalid_or_cross_scope_dependency")
        deps[seq].add(source_seq)
    coverage_by_seq = {}
    for row in coverage:
        if row["seq"] not in by_seq:
            _reject("orphan_source_coverage")
        coverage_by_seq[row["seq"]] = row["version"]
    current_facts = {}
    for personal, rows in ((False, conversation_facts), (True, profile_facts)):
        for fact in rows:
            key = key_name(_string(fact["key"], "invalid_fact_key", 128))
            value = _string(fact["value"], "invalid_fact_value", 1024)
            if personal:
                if fact["profile_id"] not in by_profile:
                    _reject("invalid_fact_owner")
                owner = "profile", fact["profile_id"]
            else:
                cid = fact["conversation_id"]
                if cid in links:
                    _reject("profile_conversation_local_facts_unsupported")
                owner = owner_for(cid)
            source_seq = fact["source_seq"]
            if source_seq not in by_seq or by_seq[source_seq]["owner"] != owner:
                _reject("invalid_fact_source")
            if source_seq in exclusion_by_seq and exclusion_by_seq[source_seq] not in ARCHIVE_COMMANDS:
                _reject("current_fact_source_excluded")
            identity = owner + (key,)
            if identity in current_facts:
                _reject("canonical_fact_key_collision")
            current_facts[identity] = {"owner": owner, "key": key, "value": value, "source_seq": source_seq}
    current_source_seqs = {f["source_seq"] for f in current_facts.values()}
    eligible = {}
    for seq, row in sorted(by_seq.items()):
        valid_receipt = (type(row["samples"]) is int and row["samples"] > 0 and isinstance(row["digest"], str)
                         and re.fullmatch(r"[0-9a-f]{64}", row["digest"]) is not None and seq in played_by_seq)
        trusted = bool(row["status"] == "played" and row["assistant"] and row["context_valid"] and valid_receipt
                       and seq not in exclusion_by_seq and seq not in visual_seqs and coverage_by_seq.get(seq) == 1)
        for source_seq in deps[seq]:
            fact_archive = source_seq in current_source_seqs and exclusion_by_seq.get(source_seq) in ARCHIVE_COMMANDS
            if source_seq in exclusion_by_seq and not fact_archive:
                trusted = False
            if by_seq[source_seq]["assistant"] and not eligible.get(source_seq, False) and not fact_archive:
                trusted = False
        eligible[seq] = trusted
    fact_versions = []; ignored_versions = 0
    grouped_versions = {}
    if versions is not None:
        for version in versions:
            legacy_owner = version["owner"]
            if not isinstance(legacy_owner, str) or not legacy_owner.startswith(("c:", "p:")):
                _reject("invalid_fact_version_owner")
            owner = ("profile" if legacy_owner.startswith("p:") else "conversation", legacy_owner[2:])
            key = key_name(_string(version["key"], "invalid_fact_key", 128))
            identity = owner + (key,)
            if identity not in current_facts:
                ignored_versions += 1
                continue  # Never resurrect a value absent from the current view.
            grouped_versions.setdefault(identity, []).append(version)
    for identity, current in sorted(current_facts.items()):
        history = grouped_versions.get(identity, []) if versions is not None else [{"source_seq": current["source_seq"],
            "value": current["value"], "recorded": by_seq[current["source_seq"]]["created"], "superseded": None}]
        history.sort(key=lambda r: r["source_seq"])
        if (not history or history[-1]["source_seq"] != current["source_seq"] or history[-1]["value"] != current["value"]
                or history[-1]["superseded"] is not None):
            _reject("fact_version_current_missing_or_inconsistent")
        seen = set()
        for revision, version in enumerate(history, 1):
            seq = version["source_seq"]
            if seq not in by_seq or by_seq[seq]["owner"] != current["owner"] or seq in seen:
                _reject("invalid_fact_version_source")
            seen.add(seq)
            recorded = _stamp(version["recorded"])
            superseded = None if version["superseded"] is None else _stamp(version["superseded"])
            if superseded is not None and superseded < recorded:
                _reject("invalid_fact_revision_time")
            state = "current" if seq == current["source_seq"] else "superseded"
            value = _string(version["value"], "invalid_fact_value", 1024)
            if seq in exclusion_by_seq and exclusion_by_seq[seq] not in FACT_HISTORY_EXCLUSIONS:
                value = None; state = "forgotten"
            fact_versions.append({"owner": current["owner"], "key": current["key"], "revision": revision,
                                  "value": value, "state": state, "recorded": recorded, "superseded": superseded, "source_seq": seq})
    for change in changes:
        if change["profile_id"] not in by_profile or change["operation"] not in {"set", "forget", "clear", "conversation_delete"}:
            _reject("unknown_profile_control_history")
        _integer(change["revision"], "invalid_profile_revision", minimum=1)
        if change["revision"] > by_profile[change["profile_id"]]["memory_revision"]:
            _reject("profile_change_ahead_of_owner")
    scopes = []
    for cid, row in by_conversation.items():
        if cid not in links:
            scopes.append(("conversation", cid, row["revision"]))
    scopes.extend(("profile", pid, p["memory_revision"]) for pid, p in by_profile.items())
    events = []; target_turns = []; bodies = []; mapping = []; target_dependencies = []
    event_fact_keys = set()
    fact_keys_by_seq = {}
    for fact in fact_versions:
        if fact["state"] == "current":
            fact_keys_by_seq.setdefault(fact["source_seq"], []).append(fact["key"])
    for seq, row in sorted(by_seq.items()):
        owner = row["owner"]; exclusion = exclusion_by_seq.get(seq)
        user_valid = exclusion is None or (seq in current_source_seqs and exclusion in ARCHIVE_COMMANDS)
        closed = played_by_seq.get(seq, max(imported_at, row["created"]))
        topic = "legacy-conversation:" + _hash(row["conversation_id"])[:12] if owner[0] == "profile" else ""
        metadata = {"time_basis": "host_received"}
        if seq in fact_keys_by_seq:
            metadata["fact_keys"] = fact_keys_by_seq[seq]
        events.append((row["user_id"], owner[0], owner[1], row["turn_id"], "user_said", topic, row["created"], None, closed,
                       1, "valid" if user_valid else "legacy_excluded", "none", _json(metadata),
                       _hash(_json([source_hash, seq, "user"])), _hash(row["user"]), None, None, 1))
        if exclusion is None:
            bodies.append((row["user_id"], row["user"]))
        if row["assistant_id"]:
            at = played_by_seq.get(seq, row["created"])
            evidence = "host_playback_ack" if seq in played_by_seq else "legacy_assistant_generation_time_unknown"
            events.append((row["assistant_id"], owner[0], owner[1], row["turn_id"], "assistant_played" if eligible[seq] else "assistant_reply", topic,
                           at, None, closed, 1, "valid" if eligible[seq] else "legacy_excluded",
                           "complete" if row["status"] == "played" and seq in played_by_seq else "incomplete", _json({"time_basis": evidence}),
                           _hash(_json([source_hash, seq, "assistant"])), _hash(row["assistant"]), None, None, int(eligible[seq])))
            if eligible[seq]:
                bodies.append((row["assistant_id"], row["assistant"]))
                target_dependencies.append((row["assistant_id"], row["user_id"]))
                for source_seq in sorted(deps[seq]):
                    target_dependencies.append((row["assistant_id"], by_seq[source_seq]["user_id"]))
                    if eligible[source_seq] and by_seq[source_seq]["assistant_id"]:
                        target_dependencies.append((row["assistant_id"], by_seq[source_seq]["assistant_id"]))
        token = "migrated-audio:" + _hash(import_id + str(seq))[:32] if eligible[seq] else None
        target_turns.append((row["turn_id"], owner[0], owner[1], row["generation"], topic,
                             "played" if eligible[seq] else "interrupted", row["user_id"], row["assistant_id"], row["created"], closed,
                             _hash(_json([source_hash, seq])), token, row["digest"] if eligible[seq] else None,
                             row["samples"] if eligible[seq] else None))
        mapping.append((import_id, seq, row["conversation_id"], owner[0], owner[1], row["turn_id"], row["user_id"], row["assistant_id"],
                        _hash(row["request_id"]), row["status"], played_by_seq.get(seq), int(eligible[seq]),
                        row["memory_revision"], row.get("profile_revision", 0)))
    for fact in fact_versions:
        event_fact_keys.add((by_seq[fact["source_seq"]]["user_id"], fact["key"]))
    return {"source_sha256": source_hash, "source_schema_sha256": source_schema, "source_user_version": user_version,
            "import_id": import_id, "scopes": scopes, "events": events, "turns": target_turns, "bodies": bodies,
            "mapping": mapping, "dependencies": target_dependencies, "event_fact_keys": sorted(event_fact_keys),
            "facts": fact_versions, "by_seq_ids": {seq: row["user_id"] for seq, row in by_seq.items()},
            "profile_links": [(import_id, cid, pid) for cid, pid in sorted(links.items())],
            "exclusions": [(import_id, seq, reason) for seq, reason in sorted(exclusion_by_seq.items())],
            "scope_meta": [(import_id, "conversation", r["id"], r["created"], r["revision"], r["memory_revision"]) for r in conversations] +
                          [(import_id, "profile", r["id"], r["created"], 0, r["memory_revision"]) for r in profiles],
            "profile_changes": [(import_id, r["profile_id"], r["revision"], r["operation"]) for r in changes],
            "profiles": [(r["id"], r["name"], r["created"], 1) for r in profiles],
            "counts": {"turns": len(turns), "events": len(events), "bodies": len(bodies), "profiles": len(profiles),
                       "current_facts": len(current_facts), "fact_revisions": len(fact_versions),
                       "excluded_turns": len(exclusions), "ignored_orphan_fact_versions": ignored_versions,
                       "assistant_recall_enabled": sum(eligible.values()),
                       "assistant_recall_suppressed": sum(bool(r["assistant"]) and not eligible[s] for s, r in by_seq.items())}}


MIGRATION_DDL = [
    "CREATE TABLE bm_migrations(import_id TEXT PRIMARY KEY,source_sha256 TEXT NOT NULL,source_schema_sha256 TEXT NOT NULL,"
    "bridge_version INTEGER NOT NULL,source_user_version INTEGER NOT NULL,state TEXT NOT NULL,report TEXT NOT NULL,completed_utc REAL NOT NULL)",
    "CREATE TABLE bm_migration_turn_map(import_id TEXT NOT NULL,source_seq INTEGER NOT NULL,source_conversation_id TEXT NOT NULL,"
    "scope_kind TEXT NOT NULL,scope_id TEXT NOT NULL,target_turn_id TEXT NOT NULL,user_event_id TEXT NOT NULL,assistant_event_id TEXT,"
    "source_request_sha256 TEXT NOT NULL,source_status TEXT NOT NULL,source_played_utc REAL,assistant_recall_eligible INTEGER NOT NULL,"
    "source_memory_revision INTEGER NOT NULL,source_profile_revision INTEGER NOT NULL,PRIMARY KEY(import_id,source_seq))",
    "CREATE TABLE bm_migration_conversation_profiles(import_id TEXT NOT NULL,conversation_id TEXT NOT NULL,profile_id TEXT NOT NULL,PRIMARY KEY(import_id,conversation_id))",
    "CREATE TABLE bm_migration_exclusions(import_id TEXT NOT NULL,source_seq INTEGER NOT NULL,reason_code TEXT NOT NULL,PRIMARY KEY(import_id,source_seq))",
    "CREATE TABLE bm_migration_fact_versions(import_id TEXT NOT NULL,scope_kind TEXT NOT NULL,scope_id TEXT NOT NULL,fact_key TEXT NOT NULL,"
    "target_revision INTEGER NOT NULL,source_seq INTEGER NOT NULL,superseded_utc REAL,PRIMARY KEY(import_id,scope_kind,scope_id,fact_key,target_revision))",
    "CREATE TABLE bm_migration_scope_meta(import_id TEXT NOT NULL,scope_kind TEXT NOT NULL,scope_id TEXT NOT NULL,created_utc REAL NOT NULL,"
    "source_revision INTEGER NOT NULL,source_memory_revision INTEGER NOT NULL,PRIMARY KEY(import_id,scope_kind,scope_id))",
    "CREATE TABLE bm_migration_profile_changes(import_id TEXT NOT NULL,profile_id TEXT NOT NULL,revision INTEGER NOT NULL,operation TEXT NOT NULL,"
    "PRIMARY KEY(import_id,profile_id,revision))",
]


def migrate_legacy_snapshot(source_path, target, *, expected_sha256, source_data_origin="synthetic", max_turns=4096,
                            transaction_budget_seconds=1.):
    """Import one explicit same-origin snapshot into an empty board store.

    Board origin requires the caller's separate private-path/single-writer
    deployment guard. This function never snapshots a live writer, opens a
    network connection, issues grants, starts cleanup or switches a writer.
    Fingerprint/schema/provenance and bounded empty-target gates are identical.
    """
    if source_data_origin not in ("synthetic", "board") or not isinstance(target, BoardMemoryStore):
        _reject("invalid_data_origin")
    if target.data_origin != source_data_origin:
        _reject("source_target_origin_mismatch")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        _reject("invalid_expected_source_fingerprint")
    if type(max_turns) is not int or not 1 <= max_turns <= 8192 or not 0 < transaction_budget_seconds <= 2:
        _reject("invalid_import_bounds")
    path = Path(source_path).resolve()
    if os.path.normcase(str(path)) == os.path.normcase(target.path):
        _reject("source_target_same_file")
    if not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        _reject("source_missing_or_too_large")
    _quiescent(path)
    if _fingerprint(path) != expected_sha256:
        _reject("source_fingerprint_mismatch")
    imported_at = target._now()
    plan = _read_plan(path, expected_sha256, imported_at=imported_at, max_turns=max_turns)
    _quiescent(path)
    if _fingerprint(path) != expected_sha256:
        _reject("source_changed")
    report = dict(plan["counts"], bridge_version=BRIDGE_VERSION, import_id=plan["import_id"],
                  source_sha256=expected_sha256, source_schema_sha256=plan["source_schema_sha256"],
                  source_user_version=plan["source_user_version"], plan_sha256=_hash(_json(plan)), idempotent=False,
                  source_data_origin=source_data_origin, target_data_origin=target.data_origin,
                  synthetic_only=source_data_origin == "synthetic", production_enabled=source_data_origin == "board",
                  imported_legacy_summaries=0, issued_profile_grants=0)
    deadline = None
    try:
        with target._db(True) as db:
            if db.execute("SELECT value FROM bm_meta WHERE key='data_origin'").fetchone()[0] != source_data_origin:
                _reject("source_target_origin_mismatch")
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "bm_migrations" in tables:
                previous = db.execute("SELECT * FROM bm_migrations WHERE import_id=?", (plan["import_id"],)).fetchone()
                if previous and previous["state"] == "complete" and previous["source_sha256"] == expected_sha256 and previous["bridge_version"] == BRIDGE_VERSION:
                    return dict(json.loads(previous["report"]), idempotent=True)
                _reject("target_not_empty")
            for table in ("bm_scopes", "bm_events", "bm_turns", "bm_bodies", "bm_summaries", "bm_facts", "bm_tasks", "bm_operations"):
                if db.execute("SELECT 1 FROM " + table + " LIMIT 1").fetchone():
                    _reject("target_not_empty")
            if "bm_profiles" in tables and db.execute("SELECT 1 FROM bm_profiles LIMIT 1").fetchone():
                _reject("target_not_empty")
            deadline = time.perf_counter() + transaction_budget_seconds
            db.set_progress_handler(lambda: int(time.perf_counter() > deadline), 1000)
            def budget():
                if time.perf_counter() > deadline:
                    _reject("target_transaction_budget_exceeded")
            def batch(sql, rows):
                for row in rows:
                    budget()
                    db.execute(sql, row)
            for statement in MIGRATION_DDL:
                budget()
                db.execute(statement)
            target._profile_catalog(db, create=True)
            batch("INSERT INTO bm_profiles VALUES(?,?,?,?)", plan["profiles"])
            batch("INSERT INTO bm_scopes VALUES(?,?,?)", plan["scopes"])
            batch("INSERT INTO bm_turns VALUES(" + ",".join("?" for _ in range(14)) + ")", plan["turns"])
            batch("INSERT INTO bm_events VALUES(" + ",".join("?" for _ in range(18)) + ")", plan["events"])
            batch("INSERT INTO bm_bodies VALUES(?,?)", plan["bodies"])
            batch("INSERT INTO bm_event_dependencies VALUES(?,?)", plan["dependencies"])
            batch("INSERT INTO bm_event_fact_keys VALUES(?,?)", plan["event_fact_keys"])
            for fact in plan["facts"]:
                budget()
                owner = fact["owner"]
                db.execute("INSERT INTO bm_facts VALUES(?,?,?,?,?,?,?)", owner + (fact["key"], fact["revision"], fact["value"], fact["state"], fact["recorded"]))
                db.execute("INSERT INTO bm_fact_sources VALUES(?,?,?,?,?)", owner + (fact["key"], fact["revision"], plan["by_seq_ids"][fact["source_seq"]]))
                db.execute("INSERT INTO bm_migration_fact_versions VALUES(?,?,?,?,?,?,?)", (plan["import_id"],) + owner +
                           (fact["key"], fact["revision"], fact["source_seq"], fact["superseded"]))
            batch("INSERT INTO bm_migration_turn_map VALUES(" + ",".join("?" for _ in range(14)) + ")", plan["mapping"])
            batch("INSERT INTO bm_migration_conversation_profiles VALUES(?,?,?)", plan["profile_links"])
            batch("INSERT INTO bm_migration_exclusions VALUES(?,?,?)", plan["exclusions"])
            batch("INSERT INTO bm_migration_scope_meta VALUES(?,?,?,?,?,?)", plan["scope_meta"])
            batch("INSERT INTO bm_migration_profile_changes VALUES(?,?,?,?)", plan["profile_changes"])
            if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
                _reject("target_foreign_key_check_failed")
            if db.execute("SELECT count(*) FROM bm_bodies").fetchone()[0] != report["bodies"]:
                _reject("target_readback_failed")
            db.execute("INSERT INTO bm_migrations VALUES(?,?,?,?,?,'complete',?,?)", (plan["import_id"], expected_sha256,
                       plan["source_schema_sha256"], BRIDGE_VERSION, plan["source_user_version"], _json(report), imported_at))
            budget()
            db.set_progress_handler(None, 0)
    except LegacyMigrationRejected:
        raise
    except MemoryBusy as exc:
        raise LegacyMigrationRejected("target_database_busy") from None
    except sqlite3.Error as exc:
        if deadline is not None and time.perf_counter() > deadline:
            raise LegacyMigrationRejected("target_transaction_budget_exceeded") from None
        raise LegacyMigrationRejected("target_transaction_failed") from None
    return report
