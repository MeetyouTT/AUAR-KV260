#!/usr/bin/env python3
"""Run prebuilt NekoMote CPU tools; no builds, conversions, windows or services.

The source JSON/resx/textures are read-only. Reports/logs are written to --output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

COMMIT = "4fbf55aa6009df76ac40dc5f18e3781914bc464f"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--importer", required=True, type=Path)
    p.add_argument("--runtime-auditor", required=True, type=Path)
    p.add_argument("--model-json", required=True, type=Path)
    p.add_argument("--resx-json", required=True, type=Path)
    p.add_argument("--resource-root", type=Path)
    p.add_argument("--texture", action="append", default=[], metavar="NAME=RELATIVE_PATH")
    p.add_argument("--steps", type=int, default=120)
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--output", type=Path, default=Path(__file__).parent / "cpu-run")
    a = p.parse_args()
    if not 1 <= a.steps <= 36000:
        p.error("--steps must be in 1..36000")
    for path in (a.importer, a.runtime_auditor, a.model_json, a.resx_json):
        if not path.is_file():
            p.error(f"required file does not exist: {path}")
    a.output.mkdir(parents=True, exist_ok=True)
    root = a.resource_root or a.model_json.parent
    shared = [str(a.model_json.resolve()), str(a.resx_json.resolve()),
              "--resource-root", str(root.resolve())]
    for mapping in a.texture:
        shared += ["--texture", mapping]
    record = {"nekomote_expected_commit": COMMIT,
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "visual_certified": False, "playback_certified": False,
              "binary_sha256": {
                  str(binary.resolve()): hashlib.sha256(binary.read_bytes()).hexdigest()
                  for binary in (a.importer, a.runtime_auditor)},
              "runs": []}
    jobs = [
        ("import", a.importer, ["--audit-report", str((a.output / "import-report.json").resolve())]),
        ("runtime", a.runtime_auditor, ["--output", str((a.output / "runtime-report.json").resolve()),
                                      "--steps", str(a.steps)]),
    ]
    try:
        for label, binary, extra in jobs:
            command = [str(binary.resolve())] + shared + extra
            completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       encoding="utf-8", errors="replace", timeout=a.timeout,
                                       check=False)
            (a.output / f"{label}.stdout.log").write_text(completed.stdout, encoding="utf-8")
            (a.output / f"{label}.stderr.log").write_text(completed.stderr, encoding="utf-8")
            record["runs"].append({"kind": label, "argv": command,
                                   "returncode": completed.returncode})
            print(f"{label}: exit={completed.returncode}")
            if completed.returncode != 0:
                break
    except subprocess.TimeoutExpired as e:
        record["error"] = f"tool timed out after {e.timeout} seconds"
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (a.output / "execution.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    success = len(record["runs"]) == 2 and all(r["returncode"] == 0 for r in record["runs"])
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
