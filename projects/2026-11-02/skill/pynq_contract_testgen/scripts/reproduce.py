#!/usr/bin/env python3
"""Generate and simulate both examples in a fresh directory; no hardware IO."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import random
import subprocess
import sys

from generate import ROOT, generate


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out = args.out.resolve()
    if args.out.exists():
        parser.error("--out must be a new directory")
    args.out.mkdir(parents=True)
    summary = {"status": "FAIL", "validation_level": "offline_generated_code_with_mock_ip",
               "python": platform.python_version(), "pynq_imported": False, "board_verified": False,
               "examples": [], "generator_sha256": hashlib.sha256((ROOT / "scripts/generate.py").read_bytes()).hexdigest()}
    try:
        for name in ("adder", "crc32"):
            example = ROOT / "examples" / name
            out = args.out / name
            generate(example / "contract.json", example / "metadata_fixture.hwh", example / "vectors.json", out, example / "mock_ip.py")
            golden = load_module(example / "golden.py", name + "_golden")
            vectors = json.loads((example / "vectors.json").read_text(encoding="utf-8"))
            for row in vectors:
                if golden.expected(row["inputs"]) != row["expected"]:
                    raise ValueError("fixed vector differs from golden reference: " + name + "/" + row["id"])
            generator_contract = json.loads((out / "contract.json").read_text())
            rng = random.Random(20261102)
            for i in range(32):
                inputs = {key: rng.getrandbits(32) for key in generator_contract["inputs"]}
                vectors.append({"id": "random_" + str(i), "inputs": inputs, "expected": golden.expected(inputs)})
            (out / "test_vectors.json").write_text(json.dumps(vectors, indent=2) + "\n", encoding="utf-8")
            report = out / "validation_report.json"
            process = subprocess.run([sys.executable, str(out / "test_ip.py"), "--mode", "mock", "--vectors", str(out / "test_vectors.json"), "--report", str(report)],
                                     cwd=str(out), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            (out / "runner.log").write_text(process.stdout, encoding="utf-8")
            result = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {"status": "FAIL", "cases": []}
            summary["examples"].append({"name": name, "status": result["status"], "returncode": process.returncode,
                                        "cases": len(result["cases"]), "report": name + "/validation_report.json"})
            if process.returncode or result["status"] != "PASS" or result["board_verified"]:
                raise ValueError("offline example failed or misreported hardware verification: " + name)
        summary["status"] = "PASS"
    except Exception as exc:
        summary["error"] = type(exc).__name__ + ": " + str(exc)
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
