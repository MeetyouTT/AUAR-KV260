#!/usr/bin/env python3
"""Read USB/UART and routing state; record no credentials and make no changes."""
import datetime
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = ROOT / "evidence" / ("host-connection-" + stamp + ".json")
    state = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "commands": []}
    for argv in (["lsusb"], ["ip", "-4", "-j", "address"], ["ip", "-4", "route"],
                 ["ip", "-4", "route", "get", "192.168.50.2"]):
        process = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        state["commands"].append({"argv": argv, "returncode": process.returncode, "output": process.stdout})
    ports = list(Path("/dev").glob("ttyUSB*"))
    byid = Path("/dev/serial/by-id")
    if byid.exists():
        ports += list(byid.iterdir())
    state["serial_ports"] = [{"path": str(p), "target": str(p.resolve())} for p in sorted(ports)]
    output.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"evidence": str(output), "serial_ports": state["serial_ports"],
        "route_to_board": state["commands"][-1]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
