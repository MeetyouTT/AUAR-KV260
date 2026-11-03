"""Read-only shutdown database check in the independent production WMI view.

This is NOT a backup or migration. It never selects business columns, exports
templates, hashes an active database file, checkpoints, vacuums, deletes or
changes business state. Each database gets its own bounded read transaction;
there is no claim of one atomic snapshot across five separate databases.

The parent must launch this through its authorized hidden independent WMI/CIM
context, not a sandbox file view. This module only checks, it never stops a
service or changes system power state. Results contain metadata only.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--max-seconds", type=float, default=25.)
    parser.add_argument("--check", choices=("quick_check", "integrity_check"), default="quick_check")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{32}", args.job_id) or not 1 <= args.max_seconds <= 30:
        raise SystemExit("Invalid shutdown metadata check arguments")
    output = HERE / ("shutdown_database_check_" + args.job_id + ".json")
    partial = output.with_suffix(".json.partial")
    if output.exists() or partial.exists():
        raise SystemExit("Do not overwrite an existing shutdown check")
    private = Path.home() / "AppData/Local/Aura/device-memory"
    sources = (
        ("conversation", PROJECT / "deliverables/2026-10-18_board_dialogue/model_host/conversations.sqlite3"),
        ("observation", private / "observations.sqlite3"),
        ("speaker", private / "speakers.sqlite3"),
        ("anonymous_voice", private / "anonymous-voices.sqlite3"),
        ("identity_links", private / "identity-links.sqlite3"),
    )
    started = time.perf_counter(); deadline = started + args.max_seconds
    report = {
        "schema_version": 1, "job_id": args.job_id, "pid": os.getpid(), "python_executable": sys.executable,
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "required_launch_context": "independent_hidden_WMI_production_file_view",
        "launch_context_must_be_verified_by_parent": True,
        "read_only": True, "business_rows_exported": False, "backup_performed": False,
        "active_database_file_hash_computed": False, "checkpoint_performed": False,
        "business_writes": False, "private_keys_read": False, "services_stopped": False,
        "cross_database_atomic_snapshot": False, "check": args.check, "max_seconds": args.max_seconds,
        "databases": {},
    }
    for kind, source in sources:
        begin = time.perf_counter()
        value = {"path": str(source), "exists": source.is_file(), "checked": False,
                 "read_mode": "mode=ro", "read_transaction": "BEGIN", "counts": {}}
        report["databases"][kind] = value
        if not value["exists"]:
            value["error_code"] = "required_source_missing"
            continue
        if begin >= deadline:
            value["error_code"] = "overall_budget_exhausted"
            continue
        db = None
        try:
            value["file_bytes_before"] = source.stat().st_size
            db = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=.3, isolation_level=None)
            db.execute("PRAGMA query_only=ON")
            db.set_progress_handler(lambda: int(time.perf_counter() >= deadline), 1000)
            db.execute("BEGIN")
            # Only an allowlisted pragma string is interpolated; diagnostics
            # are counted but never emitted with potentially private detail.
            rows = db.execute("PRAGMA " + args.check).fetchmany(11)
            value["check_result_rows"] = len(rows)
            value["integrity_ok"] = len(rows) == 1 and rows[0][0] == "ok"
            if not value["integrity_ok"]:
                value["error_code"] = "database_check_failed"
            else:
                tables = [row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
                if len(tables) > 256:
                    raise ValueError("Unexpected table-count bound")
                counts = {}
                for table in tables:
                    if time.perf_counter() >= deadline:
                        raise TimeoutError("Metadata budget expired")
                    quoted = '"' + table.replace('"', '""') + '"'
                    counts[table] = db.execute("SELECT count(*) FROM " + quoted).fetchone()[0]
                value["counts"] = counts
                value["checked"] = True
            db.rollback()  # End the read transaction; no business changes.
            value["file_bytes_after"] = source.stat().st_size
            value["file_bytes_are_not_a_snapshot_fingerprint"] = True
        except (sqlite3.Error, OSError, ValueError, TimeoutError) as exc:
            value["checked"] = False
            value["error_type"] = type(exc).__name__
            value["error_code"] = "metadata_budget_exhausted" if time.perf_counter() >= deadline else "readonly_metadata_check_failed"
            # Do not serialize exception messages, rows or SQL parameters.
        finally:
            if db is not None:
                db.close()
            value["elapsed_ms"] = round((time.perf_counter() - begin) * 1000, 3)
    report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    report["status"] = "PASS" if all(row["exists"] and row["checked"] and row.get("integrity_ok") for row in report["databases"].values()) else "FAIL"
    encoded = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    with partial.open("xb") as stream:
        stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
    os.replace(str(partial), str(output))
    print(json.dumps({"status": report["status"], "pid": report["pid"], "metadata_output": str(output),
                      "elapsed_seconds": report["elapsed_seconds"], "backup_performed": False}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
