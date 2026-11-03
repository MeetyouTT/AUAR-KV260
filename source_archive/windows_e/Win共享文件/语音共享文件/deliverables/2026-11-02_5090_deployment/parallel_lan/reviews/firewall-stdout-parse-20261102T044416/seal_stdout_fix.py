"""Seal independent repair provenance without rewriting historical receipts."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
LAN = REVIEW.parents[1]
OUT = LAN.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


original_manifest = LAN / "prepared_source_manifest.json"
assert sha(original_manifest) == sha(REVIEW / "prepared_source_manifest.json.before")
assert sha(LAN / "PREPARED.json") == sha(REVIEW / "PREPARED.json.before")
historical_sources = read(REVIEW / "original_sources_manifest.json")
assert len(historical_sources) == 8
for item in historical_sources:
    assert sha(Path(item["backup_path"])) == item["sha256"]
    assert Path(item["backup_path"]).stat().st_size == item["bytes"]
transaction_files = read(REVIEW / "transaction_before_manifest.json")
assert len(transaction_files) == 5
for item in transaction_files:
    assert sha(Path(item["original_path"])) == sha(Path(item["backup_path"])) == item["sha256"]
assert sha(LAN / "firewall_result.json") == sha(REVIEW / "firewall_result.json.before")

paths = [Path(item["path"]) for item in read(original_manifest)]
paths += [LAN / "cli_stdout_fixture.py", LAN / "test_cli_stdout.ps1"]
current = [dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path)) for path in paths]
fixed_manifest = LAN / "source_manifest_cli_stdout_fix.json"
write(fixed_manifest, current)
changes = []
patches = []
for item in historical_sources:
    original = Path(item["original_path"])
    backup = Path(item["backup_path"])
    if sha(original) != item["sha256"]:
        changes.append(original.name)
        patches.extend(difflib.unified_diff(backup.read_text(encoding="utf-8").splitlines(keepends=True),
                                           original.read_text(encoding="utf-8").splitlines(keepends=True),
                                           fromfile=str(backup), tofile=str(original)))
assert sorted(changes) == ["lan_control.py", "test_lan_control.py"]
(REVIEW / "repair.diff").write_text("".join(patches), encoding="utf-8")
before = read(REVIEW / "full_cp936_guard_before.json")
after = read(REVIEW / "full_cp936_guard_after.json")
assert before["parse"] == "FAILED" and "Path 'adapter.alias', line 184, position 5" in before["error"]
assert after["parse"] == "PASS" and after["alias"] == "\u4ee5\u592a\u7f51"
cli_tests = [read(REVIEW / ("cli_stdout_" + version + "_final.json")) for version in ("ps51", "ps7")]
assert all(report["status"] == "PASS" and len(report["cases"]) == 3 for report in cli_tests)
assert b"Ran 25 tests" in (REVIEW / "python_25_final.log").read_bytes()
assert b"\nOK" in (REVIEW / "python_25_final.log").read_bytes()
assert read(REVIEW / "powershell_syntax_ps51_after.json")["status"] == "PASS"
assert read(REVIEW / "firewall_scope_after.json")["status"] == "PASS"
transaction = read(LAN / "transactions/2524d38f24674cdca495ed726f38b41d/transaction.json")
guard = read(REVIEW / "full_cp936_guard_stdout_after.txt")
assert guard["session_id"] == transaction["candidate_record"]["session_id"] == "2f3a707efa62401d81fc20ef22a379cb"
assert transaction["phase"] == "LAN_READY_FIREWALL_AND_BOARD_PROBE_PENDING"
report = dict(
    schema="aura-lan-cli-stdout-repair-1",
    status="CLI_STDOUT_FIX_VALIDATED_AWAITING_ROOT_FIREWALL_APPLY",
    utc=datetime.now(timezone.utc).isoformat(),
    historical_preparation_manifest=str(original_manifest),
    historical_preparation_manifest_sha256=sha(original_manifest),
    historical_prepared_json_unchanged=True,
    historical_original_source_count=8,
    historical_source_backup_manifest=str(REVIEW / "original_sources_manifest.json"),
    transaction_id=transaction["transaction_id"],
    transaction_phase_unchanged=transaction["phase"],
    session_id=guard["session_id"],
    actual_transaction_original_files_unchanged=5,
    actual_transaction_backup_manifest=str(REVIEW / "transaction_before_manifest.json"),
    first_apply_failure_original_bytes_unchanged=True,
    first_apply_failure_archive=str(REVIEW / "firewall_result.json.before"),
    diagnosis="CP936 native decoding of ensure_ascii=False UTF-8 consumes the closing alias quote; full guard reproduces the exact observed JSON error. CLI ASCII JSON restores the exact original Unicode alias under each tested code page.",
    changes=["Normal CLI JSON ensure_ascii=False -> True; errors already use ASCII escaping.",
             "Read-only firewall Check subprocess bounded timeout120 -> 600 seconds; exact scope, owner, other-rule fingerprints and freshness unchanged.",
             "Regression requires Check600 and proves Check timeout causes no SSH and no transaction mutation."],
    check_timeout_basis="Root observed first Apply take134 seconds before first guard JSON parse failed. Full Check includes two other-rule/filter fingerprints and two current owner guards;120 seconds is insufficient.",
    current_source_manifest=str(fixed_manifest),
    current_source_manifest_sha256=sha(fixed_manifest),
    current_source_count=len(current),
    changed_original_source_files=changes,
    lan_control_sha256=sha(LAN / "lan_control.py"),
    firewall_script_sha256=sha(OUT / "configure_model_firewall.ps1"),
    validation=dict(isolated_python_tests=25, powershell_cli_unicode_cases=6,
                    powershell_versions=[item["powershell_version"] for item in cli_tests],
                    codepages=[65001, 936, 437], exact_unicode_alias=True,
                    full_actual_guard_cp936_after="PASS", powershell51_parse_errors=0,
                    changed_firewall_scopes_rejected=13, changed_physical_adapters_rejected=5),
    model_control_performed=False, inference_sent=False, firewall_modified=False,
    board_contacted=False, historical_execution_relabelled=False,
    next_step="Root Apply exact existing script for current session, then inspect its fresh result and separately authorize public board probe using this independent repair provenance.",
)
if (REVIEW / "fingerprint_timing.json").exists():
    report["supplementary_readonly_fingerprint_timing"] = str(REVIEW / "fingerprint_timing.json")
write(LAN / "CLI_STDOUT_FIX.json", report)
print(json.dumps({key: report[key] for key in ("status", "session_id", "current_source_manifest_sha256", "lan_control_sha256", "firewall_script_sha256", "actual_transaction_original_files_unchanged")}, indent=2))
