"""Run the public trace examples and unit tests sequentially. Requires Python 3.8+."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(args):
    return subprocess.run([sys.executable, "-B"] + args, cwd=str(ROOT),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding="utf-8", errors="replace")


def main():
    profile = json.loads((ROOT / "config/wide_contract.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256((ROOT / "references/rtl/visual_servo.sv").read_bytes()).hexdigest()
    rows = []
    for case, status, code in (("trace_pass", "PASS", 0), ("trace_fail", "FAIL", 1),
                               ("trace_unknown", "UNKNOWN", 2)):
        proc = run(["scripts/validate_trace.py", "--trace", "examples/" + case + ".json",
                    "--profile", "config/wide_contract.json"])
        result = json.loads(proc.stdout)
        rows.append({"input": case, "expected": status, "actual": result,
                     "returncode": proc.returncode,
                     "matched": result["status"] == status and proc.returncode == code})
    units = run(["-m", "unittest", "discover", "-s", "tests", "-v"])
    passed = digest == profile["source_sha256"] and all(row["matched"] for row in rows) and units.returncode == 0
    print(json.dumps({"python": platform.python_version(), "platform": platform.system(),
                      "scope": "normalized public trace unit tests and source identity",
                      "rtl_sha256": digest, "rtl_matches_profile": digest == profile["source_sha256"],
                      "examples": rows, "unit_returncode": units.returncode,
                      "unit_output": units.stderr.splitlines(), "passed": passed}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
