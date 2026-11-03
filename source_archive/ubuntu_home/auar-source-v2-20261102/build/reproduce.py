#!/usr/bin/env python3
"""Real Vivado source build runner; no board operations or model requests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sources():
    result = {}
    for folder in [ROOT / "src", ROOT / "third_party", ROOT / "build"]:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                if path.suffix.lower() in {".dcp", ".xpr", ".bit", ".xsa", ".xclbin", ".so", ".o"}:
                    raise ValueError("Generated binary found among source inputs: " + str(path))
                result[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--vivado", type=Path, required=True)
    parser.add_argument("--vitis-root", type=Path, required=True)
    parser.add_argument("--stage", choices=["prepare", "implement", "all"], default="all")
    args = parser.parse_args()
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        raise ValueError("Output must be outside the source directory")
    if args.stage != "implement" and out.exists():
        raise ValueError("Use a fresh output directory")
    vivado = args.vivado.resolve()
    vitis = args.vitis_root.resolve()
    if not vivado.is_file() or not (vitis / "data/ip").is_dir():
        raise ValueError("Vivado executable or Vitis IP directory missing")
    pins = sources()
    out.mkdir(parents=True, exist_ok=args.stage == "implement")
    previous = out / "prepare_receipt.json"
    if args.stage == "implement":
        prepared = json.loads(previous.read_text())
        if prepared.get("exit_code") != 0 or prepared.get("source_sha256") != pins:
            raise ValueError("Source differs from successful prepare; start a fresh build")
    command = [str(vivado), "-mode", "batch", "-source", str(ROOT / "build/build.tcl"),
               "-log", str(out / (args.stage + ".vivado.log")),
               "-journal", str(out / (args.stage + ".vivado.jou")),
               "-tclargs", "--out", str(out), "--stage", args.stage, "--vitis-root", str(vitis)]
    started = time.time()
    log = out / (args.stage + ".console.log")
    print("Running stage", args.stage, "log:", log, flush=True)
    with log.open("wb") as handle:
        process = subprocess.Popen(command, cwd=out, stdout=handle, stderr=subprocess.STDOUT,
                                   env=dict(os.environ, OMP_NUM_THREADS="1"))
        code = process.wait()
    required = []
    if args.stage in {"prepare", "all"}:
        required += ["AUAR_PREPARE_PASS"]
    if args.stage in {"implement", "all"}:
        required += ["AUAR_IMPLEMENT_PASS"]
    text = log.read_text(errors="replace")
    missing = [marker for marker in required if marker not in text]
    changed = pins != sources()
    receipt = {"stage": args.stage, "exit_code": code, "elapsed_seconds": round(time.time() - started, 3),
               "missing_markers": missing, "source_changed": changed, "source_sha256": pins,
               "command": command, "old_checkpoint_used": False, "board_accessed": False,
               "status": "PASS" if code == 0 and not missing and not changed else "FAIL"}
    (out / (args.stage + "_receipt.json")).write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key not in {"source_sha256", "command"}}, indent=2))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        sys.exit(2)
