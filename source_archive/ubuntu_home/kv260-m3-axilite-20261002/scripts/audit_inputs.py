#!/usr/bin/env python3
"""Record source identity and preservation checks for the host hardware review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parent.parent
identity = json.loads((root / "evidence/build_identity.json").read_text())
source_checks = []
for item in identity["inputs"]:
    digest = hashlib.sha256((root / item["path"]).read_bytes()).hexdigest()
    source_checks.append({"path": item["path"], "recorded_sha256": item["sha256"],
                          "actual_sha256": digest, "matches": digest == item["sha256"]})
commit = subprocess.check_output(
    ["git", "-C", str(root / "src"), "rev-parse", "HEAD"], text=True).strip()
parent = root.parent / "kv260-dpu41-control-20261001"
preservation_checks = []
for name in ["ARTIFACTS.sha256", "candidate_board_20261002.sha256"]:
    index = parent / "evidence" / name
    command = ["sha256sum", "--check", "--quiet", str(index)]
    result = subprocess.run(command, cwd=parent, text=True, capture_output=True)
    preservation_checks.append({"index": str(index), "command": command,
                                "entries": len(index.read_text().splitlines()),
                                "returncode": result.returncode,
                                "diagnostics": result.stdout + result.stderr})
passed = (commit == identity["reference_commit"]
          and all(item["matches"] for item in source_checks)
          and all(item["returncode"] == 0 for item in preservation_checks))
record = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
          "actual_reference_commit": commit,
          "reference_commit_matches": commit == identity["reference_commit"],
          "source_checks": source_checks,
          "validated_parent_preservation": preservation_checks, "pass": passed}
(root / "evidence/input_integrity_audit.json").write_text(
    json.dumps(record, ensure_ascii=False, indent=2) + "\n")
print("Fixed commit and source/configuration identity:", passed)
for item in preservation_checks:
    print("Preserved parent index:", Path(item["index"]).name,
          "entries=", item["entries"], "returncode=", item["returncode"])
if not passed:
    raise SystemExit(3)
