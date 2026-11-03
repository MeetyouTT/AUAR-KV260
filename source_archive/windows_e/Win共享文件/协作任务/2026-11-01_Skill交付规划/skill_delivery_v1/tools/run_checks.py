"""Run only public offline unit tests. Does not run RTL, XIR, CUDA or model services."""
import json
import os
from pathlib import Path
import subprocess
import sys

def main():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    results = []
    for name in ("command-guard-validation", "dpu-model-validation-and-scheduling",
                 "llm-voice-runtime-optimization"):
        command = [sys.executable, "-B", "-m", "unittest", "discover", "-s",
                   str(root / "skill" / name / "tests"), "-p", "test_*.py", "-v"]
        completed = subprocess.run(command, cwd=str(root), env=env, capture_output=True,
                                   text=True, errors="replace", timeout=120)
        print(completed.stdout, end="")
        print(completed.stderr, end="")
        results.append({"package": name, "returncode": completed.returncode})
    report = {"status": "PASS" if all(x["returncode"] == 0 for x in results) else "FAIL",
              "scope": "PUBLIC_OFFLINE_TESTS_ONLY", "results": results,
              "model_inference_run": False, "cuda_probe_run": False, "device_accessed": False}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
