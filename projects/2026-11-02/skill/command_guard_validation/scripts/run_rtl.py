"""Explicit local RTL simulation only. Requires a new output directory; no board access."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vivado-bin", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if sys.platform == "win32":
        p.error("This wrapper is Linux-only. Windows RTL execution is not validated by this bundle.")
    args.output = args.output.resolve()
    tools = {name: args.vivado_bin.resolve() / name for name in ("xvlog", "xelab", "xsim")}
    for tool in tools.values():
        if not tool.is_file():
            p.error("missing simulator: " + str(tool))
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    rtl = root / "references/rtl/visual_servo.sv"
    profile = json.loads((root / "config/wide_contract.json").read_text(encoding="utf-8"))
    rtl_sha = hashlib.sha256(rtl.read_bytes()).hexdigest()
    if rtl_sha != profile["source_sha256"]:
        p.error("RTL SHA-256 differs from wide_contract.json")
    markers = {
        "tb_wide": "AURA_WIDE_TEST_PASS",
        "tb_servo": "AURA_SERVO_TEST_PASS",
        "tb_pulse_guard": "AURA_V2_PULSE_GUARD_OFFLINE_PASS_NOT_BOARD_RELEASE",
        "tb_nominal": "AURA_NOMINAL_TEST_PASS",
    }
    rows = []
    for name, marker in markers.items():
        work = args.output / name
        work.mkdir()
        original = root / ("references/tests/" + name + ".sv")
        # Same build-ID substitution used by the frozen project test runner.
        text = original.read_text(encoding="utf-8").replace("32'h778d2512", "32'h10282601")
        tb = work / (name + ".sv")
        tb.write_text(text, encoding="utf-8")
        row = {"test": name, "stages": [], "passed": False, "required_marker": marker,
               "source_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
               "effective_tb_sha256": hashlib.sha256(tb.read_bytes()).hexdigest()}
        commands = [
            [str(tools["xvlog"]), "-sv", str(rtl), str(tb)],
            [str(tools["xelab"]), name, "-s", name, "-debug", "typical"],
            [str(tools["xsim"]), name, "-runall"],
        ]
        last_text = ""
        for command in commands:
            stage = Path(command[0]).name
            try:
                result = subprocess.run(command, cwd=str(work), capture_output=True,
                                        text=True, errors="replace", timeout=240)
                last_text = result.stdout + result.stderr
                code = result.returncode
            except subprocess.TimeoutExpired:
                last_text, code = "SIMULATION_TIMEOUT\n", 124
            (work / (stage + ".log")).write_text(last_text, encoding="utf-8")
            row["stages"].append({"stage": stage, "returncode": code})
            if code or "Fatal:" in last_text or "ERROR:" in last_text:
                break
        else:
            row["passed"] = any(line.startswith(marker) for line in last_text.splitlines())
        rows.append(row)
    result = {"scope": "RTL_SIMULATION_ONLY", "device_accessed": False,
              "physical_motion_verified": False, "rtl_sha256": rtl_sha, "tests": rows,
              "passed": all(x["passed"] for x in rows)}
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
