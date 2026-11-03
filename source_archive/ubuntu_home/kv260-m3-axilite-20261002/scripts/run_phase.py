#!/usr/bin/env python3
"""Run a host build phase with a separate complete log and exit-status record."""
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib
import os
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
if len(sys.argv) != 2 or sys.argv[1] not in {"ip", "platform", "overlay", "review", "review-finalize"}:
    raise SystemExit("Usage: python3 scripts/run_phase.py ip|platform|overlay|review|review-finalize")
phase = sys.argv[1]
attempt = 1
while (root / "logs" / f"{phase}_{attempt:02d}").exists():
    attempt += 1
directory = root / "logs" / f"{phase}_{attempt:02d}"
directory.mkdir()
snapshot = directory / "run_m3_build.sh"
script_data = (root / "run_m3_build.sh").read_bytes()
snapshot.write_bytes(script_data)
command = ["bash", str(snapshot), phase]
record = {"phase": phase, "attempt": attempt, "command": command,
          "entry_script_snapshot": str(snapshot.relative_to(root)),
          "entry_script_sha256": hashlib.sha256(script_data).hexdigest(),
          "started_at_utc": datetime.now(timezone.utc).isoformat(), "state": "running"}
result_path = directory / "result.json"
result_path.write_text(json.dumps(record, indent=2) + "\n")
print(f"Phase {phase}, attempt {attempt}: {directory / 'console.log'}", flush=True)
with (directory / "console.log").open("x") as log:
    environment = os.environ.copy()
    environment["AURA_M3_PROJECT_ROOT"] = str(root)
    process = subprocess.Popen(command, cwd=root, env=environment,
                               stdout=log, stderr=subprocess.STDOUT)
    record["pid"] = process.pid
    result_path.write_text(json.dumps(record, indent=2) + "\n")
    returncode = process.wait()
record.update({"state": "finished", "returncode": returncode,
               "ended_at_utc": datetime.now(timezone.utc).isoformat()})
result_path.write_text(json.dumps(record, indent=2) + "\n")
print(f"Phase {phase} finished, returncode={returncode}", flush=True)
raise SystemExit(returncode)
