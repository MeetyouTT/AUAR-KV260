"""Single-process-at-a-time skill C regression entry point, Python 3.8+."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
CHECKS = [
    (0, ["-m", "unittest", "discover", "-s", "tests", "-v"]),
    (0, ["scripts/verify_measured_run.py", "examples/measured"]),
    (0, ["scripts/analyze_benchmarks.py", "--input", "examples/benchmarks.json"]),
    (0, ["scripts/validate_delivery_trace.py", "--input", "examples/delivery_pass.json"]),
    (1, ["scripts/validate_delivery_trace.py", "--input", "examples/delivery_fail.json"]),
]


if __name__ == "__main__":
    import json
    for expected, args in CHECKS:
        run = subprocess.run([sys.executable, "-B"] + args, cwd=str(ROOT),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        ok = run.returncode == expected
        if args[0] != "-m" and ok:
            try:
                ok = json.loads(run.stdout)["status"] == ("FAIL" if expected else "PASS")
            except (ValueError, KeyError):
                ok = False
        print(("PASS " if ok else "FAIL ") + " ".join(args))
        if not ok:
            print(run.stdout)
            sys.exit(1)
